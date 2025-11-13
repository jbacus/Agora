#!/bin/bash
# ============================================
# Google Cloud Infrastructure Setup Script
# Virtual Debate Panel (Agora)
# ============================================
# This script sets up all required Google Cloud resources for the project
#
# Prerequisites:
#   1. gcloud CLI installed (https://cloud.google.com/sdk/docs/install)
#   2. Authenticated: gcloud auth login
#   3. Billing account linked to your GCP project
#
# Usage:
#   chmod +x scripts/setup_gcloud_infrastructure.sh
#   ./scripts/setup_gcloud_infrastructure.sh

set -e  # Exit on error

# ============================================
# Configuration Variables
# ============================================
echo "🚀 Virtual Debate Panel - Google Cloud Infrastructure Setup"
echo "============================================"
echo ""

# Prompt for project ID
read -p "Enter your Google Cloud Project ID (or press Enter to create new): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    read -p "Enter a new Project ID (lowercase, numbers, hyphens): " PROJECT_ID
    read -p "Enter Project Name (human-readable): " PROJECT_NAME

    echo "📦 Creating new Google Cloud project..."
    gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"

    echo "⚠️  IMPORTANT: Link a billing account to this project in the Cloud Console:"
    echo "   https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    read -p "Press Enter after linking billing account..."
fi

# Set default project
gcloud config set project "$PROJECT_ID"
echo "✅ Using project: $PROJECT_ID"
echo ""

# Configuration
REGION="us-central1"
SERVICE_NAME="agora-backend"
ARTIFACT_REGISTRY_REPO="agora-images"
FRONTEND_BUCKET="${PROJECT_ID}-agora-frontend"

echo "Configuration:"
echo "  Region: $REGION"
echo "  Backend Service: $SERVICE_NAME"
echo "  Artifact Registry: $ARTIFACT_REGISTRY_REPO"
echo "  Frontend Bucket: $FRONTEND_BUCKET"
echo ""

# ============================================
# Enable Required APIs
# ============================================
echo "🔧 Enabling required Google Cloud APIs..."
echo "This may take a few minutes..."

# Enable IAM/Service Account API first (required for service accounts)
echo "📋 Enabling IAM and Service Account APIs..."
gcloud services enable iam.googleapis.com serviceusage.googleapis.com

# Enable other required APIs
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    cloudresourcemanager.googleapis.com

echo "✅ All APIs enabled"
echo ""

# Wait for API propagation
echo "⏳ Waiting for APIs to propagate (30 seconds)..."
sleep 30
echo "✅ APIs ready"
echo ""

# ============================================
# Create Artifact Registry Repository
# ============================================
echo "📦 Creating Artifact Registry repository for Docker images..."

# Check if repository exists
if gcloud artifacts repositories describe "$ARTIFACT_REGISTRY_REPO" \
    --location="$REGION" &>/dev/null; then
    echo "✅ Artifact Registry repository already exists"
else
    gcloud artifacts repositories create "$ARTIFACT_REGISTRY_REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker images for Virtual Debate Panel"
    echo "✅ Artifact Registry repository created"
fi
echo ""

# ============================================
# Create Cloud Storage Bucket for Frontend
# ============================================
echo "🗄️  Creating Cloud Storage bucket for frontend..."

# Check if bucket exists
if gsutil ls -b "gs://$FRONTEND_BUCKET" &>/dev/null; then
    echo "✅ Bucket already exists"
else
    gsutil mb -l "$REGION" -c STANDARD "gs://$FRONTEND_BUCKET"
    echo "✅ Bucket created"
fi

# Configure for static website hosting
echo "🌐 Configuring bucket for static website hosting..."
gsutil web set -m index.html -e 404.html "gs://$FRONTEND_BUCKET"

# Make bucket publicly readable
echo "🔓 Making bucket publicly accessible..."
gsutil iam ch allUsers:objectViewer "gs://$FRONTEND_BUCKET"

echo "✅ Frontend bucket configured"
echo ""

# ============================================
# Create Secret for API Key
# ============================================
echo "🔐 Setting up Secret Manager for API keys..."

read -p "Enter your Gemini API Key (or press Enter to skip): " GEMINI_API_KEY

if [ -n "$GEMINI_API_KEY" ]; then
    # Check if secret exists
    if gcloud secrets describe GEMINI_API_KEY &>/dev/null; then
        echo "Updating existing secret..."
        echo -n "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-
    else
        echo "Creating new secret..."
        echo -n "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
            --data-file=- \
            --replication-policy="automatic"
    fi
    echo "✅ API key stored in Secret Manager"
else
    echo "⚠️  Skipped - you'll need to create this manually later"
    echo "   gcloud secrets create GEMINI_API_KEY --data-file=-"
fi
echo ""

# ============================================
# Configure IAM Permissions
# ============================================
echo "🔑 Configuring IAM permissions for Cloud Build..."

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "Cloud Build Service Account: $CLOUD_BUILD_SA"

# Grant Cloud Build permissions to deploy to Cloud Run
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/run.admin" \
    --condition=None

# Grant Cloud Build permissions to act as Cloud Run runtime service account
gcloud iam service-accounts add-iam-policy-binding \
    "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/iam.serviceAccountUser"

# Grant Cloud Build access to Secret Manager
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

# Grant Cloud Build permissions to push to Artifact Registry
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/artifactregistry.writer" \
    --condition=None

echo "✅ IAM permissions configured"
echo ""

# ============================================
# Create Cloud Build Triggers (Manual Step)
# ============================================
echo "⚙️  Cloud Build Triggers Setup"
echo "============================================"
echo "Cloud Build triggers must be created manually via the Console or gcloud CLI."
echo ""
echo "Option 1: Using Cloud Console (Recommended)"
echo "  1. Go to: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo "  2. Click 'Connect Repository' and link your GitHub repo"
echo "  3. Create a trigger with these settings:"
echo "     - Name: agora-backend-deploy"
echo "     - Event: Push to branch 'main'"
echo "     - Configuration: Cloud Build configuration file (cloudbuild.yaml)"
echo "     - Location: Repository (cloudbuild.yaml)"
echo ""
echo "Option 2: Using gcloud CLI (if repo already connected)"
echo "  gcloud beta builds triggers create github \\"
echo "    --repo-name=Agora \\"
echo "    --repo-owner=YOUR_GITHUB_USERNAME \\"
echo "    --branch-pattern='^main$' \\"
echo "    --build-config=cloudbuild.yaml \\"
echo "    --description='Deploy Agora backend to Cloud Run' \\"
echo "    --region=$REGION"
echo ""

# ============================================
# Summary and Next Steps
# ============================================
echo "============================================"
echo "✅ Infrastructure Setup Complete!"
echo "============================================"
echo ""
echo "📋 Resources Created:"
echo "  ✓ Artifact Registry: $REGION-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REGISTRY_REPO"
echo "  ✓ Frontend Bucket: gs://$FRONTEND_BUCKET"
echo "  ✓ Frontend URL: http://$FRONTEND_BUCKET.storage.googleapis.com"
if [ -n "$GEMINI_API_KEY" ]; then
    echo "  ✓ Secret: GEMINI_API_KEY"
fi
echo "  ✓ IAM Permissions: Configured for Cloud Build"
echo ""
echo "📝 Next Steps:"
echo "  1. Create Cloud Build trigger (see instructions above)"
echo "  2. Copy .env.example to .env and fill in values"
echo "  3. Test locally: docker-compose up"
echo "  4. Push to GitHub main branch to trigger deployment"
echo "  5. Monitor deployment: https://console.cloud.google.com/cloud-build/builds?project=$PROJECT_ID"
echo ""
echo "📚 Documentation:"
echo "  - See docs/DEPLOYMENT.md for detailed deployment guide"
echo "  - See docs/ARCHITECTURE.md for system architecture"
echo ""
echo "🎉 Happy deploying!"
