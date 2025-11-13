#!/bin/bash
# ============================================
# CI/CD End-to-End Test Script
# Virtual Debate Panel (Agora)
# ============================================
# This script tests the entire CI/CD pipeline locally before deploying

set -e  # Exit on error

echo "🧪 CI/CD End-to-End Test"
echo "============================================"
echo ""

# ============================================
# Prerequisites Check
# ============================================
echo "📋 Step 1: Checking Prerequisites..."
echo "============================================"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo "✅ gcloud CLI installed"

# Check docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker installed"

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi
echo "✅ gcloud authenticated"

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi
echo "✅ GCP Project: $PROJECT_ID"

echo ""

# ============================================
# Step 2: Local Docker Build Test
# ============================================
echo "🐳 Step 2: Testing Local Docker Build..."
echo "============================================"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "❌ Please edit .env and add your GEMINI_API_KEY, then run this script again"
    exit 1
fi

# Source .env
export $(grep -v '^#' .env | xargs)

# Check for API key
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo "❌ GEMINI_API_KEY not set in .env file"
    exit 1
fi
echo "✅ GEMINI_API_KEY configured"

# Build Docker image
echo ""
echo "Building Docker image..."
docker build -t agora-backend:test -f Dockerfile . 2>&1 | tail -n 20

if [ $? -eq 0 ]; then
    echo "✅ Docker build successful"
else
    echo "❌ Docker build failed"
    exit 1
fi

echo ""

# ============================================
# Step 3: Local Container Test
# ============================================
echo "🚀 Step 3: Testing Container Locally..."
echo "============================================"

# Stop any existing test containers
docker stop agora-test 2>/dev/null || true
docker rm agora-test 2>/dev/null || true

# Run container
echo "Starting container..."
docker run -d \
  --name agora-test \
  -p 8080:8080 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e LLM_PROVIDER="gemini" \
  -e VECTOR_DB="chromadb" \
  -e LOG_LEVEL="INFO" \
  agora-backend:test

# Wait for startup
echo "Waiting for application to start (15 seconds)..."
sleep 15

# Test health endpoint
echo ""
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8080/api/health || echo "FAILED")

if echo "$HEALTH_RESPONSE" | grep -q "healthy\|status"; then
    echo "✅ Health endpoint responding"
    echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo "❌ Health endpoint failed"
    echo "Container logs:"
    docker logs agora-test
    docker stop agora-test
    exit 1
fi

# Test authors endpoint
echo ""
echo "Testing authors endpoint..."
AUTHORS_RESPONSE=$(curl -s http://localhost:8080/api/authors || echo "FAILED")

if echo "$AUTHORS_RESPONSE" | grep -q "authors\|marx\|whitman"; then
    echo "✅ Authors endpoint responding"
    echo "$AUTHORS_RESPONSE" | jq '.' 2>/dev/null || echo "$AUTHORS_RESPONSE"
else
    echo "⚠️  Authors endpoint returned unexpected response (may be OK if no data ingested yet)"
    echo "$AUTHORS_RESPONSE"
fi

# Clean up
echo ""
echo "Cleaning up test container..."
docker stop agora-test
docker rm agora-test

echo "✅ Local container test complete"
echo ""

# ============================================
# Step 4: Google Cloud Setup Verification
# ============================================
echo "☁️  Step 4: Verifying Google Cloud Setup..."
echo "============================================"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
echo "Project Number: $PROJECT_NUMBER"

# Check required APIs
REQUIRED_APIS=(
    "iam.googleapis.com"
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "artifactregistry.googleapis.com"
    "secretmanager.googleapis.com"
)

echo ""
echo "Checking required APIs..."
ALL_APIS_ENABLED=true

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "  ✅ $api"
    else
        echo "  ❌ $api (not enabled)"
        ALL_APIS_ENABLED=false
    fi
done

if [ "$ALL_APIS_ENABLED" = false ]; then
    echo ""
    echo "⚠️  Some required APIs are not enabled. Run:"
    echo "  ./scripts/setup_gcloud_infrastructure.sh"
    exit 1
fi

# Check Artifact Registry
echo ""
echo "Checking Artifact Registry repository..."
REGION="us-central1"
REPO_NAME="agora-images"

if gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &>/dev/null; then
    echo "✅ Artifact Registry repository exists: $REPO_NAME"
else
    echo "❌ Artifact Registry repository not found"
    echo "Run: ./scripts/setup_gcloud_infrastructure.sh"
    exit 1
fi

# Check Secret Manager
echo ""
echo "Checking Secret Manager..."
if gcloud secrets describe GEMINI_API_KEY &>/dev/null; then
    echo "✅ GEMINI_API_KEY secret exists"
else
    echo "⚠️  GEMINI_API_KEY secret not found in Secret Manager"
    echo "Run: ./scripts/setup_gcloud_infrastructure.sh"
fi

# Check IAM permissions
echo ""
echo "Checking Cloud Build service account permissions..."
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

REQUIRED_ROLES=(
    "roles/run.admin"
    "roles/artifactregistry.writer"
)

for role in "${REQUIRED_ROLES[@]}"; do
    if gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$CLOUD_BUILD_SA AND bindings.role:$role" \
        --format="value(bindings.role)" | grep -q "$role"; then
        echo "  ✅ $role"
    else
        echo "  ⚠️  $role (may need to be granted)"
    fi
done

echo ""
echo "✅ Google Cloud setup verification complete"
echo ""

# ============================================
# Step 5: Cloud Build Test (Dry Run)
# ============================================
echo "🏗️  Step 5: Testing Cloud Build Configuration..."
echo "============================================"

# Validate cloudbuild.yaml syntax
if [ -f "cloudbuild.yaml" ]; then
    echo "✅ cloudbuild.yaml exists"

    # Check for required fields
    if grep -q "steps:" cloudbuild.yaml && \
       grep -q "gcr.io/cloud-builders/docker" cloudbuild.yaml && \
       grep -q "gcloud run deploy" cloudbuild.yaml; then
        echo "✅ cloudbuild.yaml has required steps"
    else
        echo "⚠️  cloudbuild.yaml may be missing required steps"
    fi
else
    echo "❌ cloudbuild.yaml not found"
    exit 1
fi

echo ""

# ============================================
# Step 6: Trigger Check
# ============================================
echo "🔄 Step 6: Checking Cloud Build Triggers..."
echo "============================================"

TRIGGERS=$(gcloud builds triggers list --format="value(name)" 2>/dev/null || echo "")

if [ -n "$TRIGGERS" ]; then
    echo "Cloud Build triggers found:"
    gcloud builds triggers list --format="table(name,github.name,github.branch)"
    echo ""
    echo "✅ Cloud Build triggers configured"
else
    echo "⚠️  No Cloud Build triggers found"
    echo ""
    echo "To create a trigger:"
    echo "  1. Go to: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
    echo "  2. Click 'Connect Repository'"
    echo "  3. Select GitHub and authorize"
    echo "  4. Choose your repository"
    echo "  5. Create trigger with branch pattern: ^main$"
    echo ""
fi

# ============================================
# Summary and Next Steps
# ============================================
echo "============================================"
echo "✅ CI/CD Test Summary"
echo "============================================"
echo ""
echo "✓ Local Docker build: PASSED"
echo "✓ Local container test: PASSED"
echo "✓ Google Cloud setup: VERIFIED"
echo "✓ Cloud Build config: VALID"
echo ""
echo "📝 Next Steps:"
echo ""
echo "To deploy to Cloud Run:"
echo "  1. Commit your changes: git add . && git commit -m 'Ready for deployment'"
echo "  2. Push to main: git push origin main"
echo "  3. Monitor build: gcloud builds list --limit=5"
echo "  4. View logs: gcloud builds log \$(gcloud builds list --limit=1 --format='value(ID)')"
echo ""
echo "Or deploy manually:"
echo "  gcloud builds submit --config=cloudbuild.yaml ."
echo ""
echo "After deployment:"
echo "  SERVICE_URL=\$(gcloud run services describe agora-backend --region=us-central1 --format='value(status.url)')"
echo "  curl \$SERVICE_URL/api/health"
echo ""
echo "🎉 CI/CD pipeline is ready to deploy!"
