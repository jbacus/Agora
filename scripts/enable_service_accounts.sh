#!/bin/bash
# ============================================
# Enable and Configure Service Accounts
# Virtual Debate Panel (Agora)
# ============================================
# This script enables the Service Account API and configures
# the necessary service accounts for Cloud Build and Cloud Run

set -e  # Exit on error

echo "🔧 Enabling Service Accounts for Agora Deployment"
echo "============================================"
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ No project set. Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📦 Project: $PROJECT_ID"
echo ""

# ============================================
# Step 1: Enable Service Account API
# ============================================
echo "🔧 Step 1: Enabling Service Account API..."

gcloud services enable iam.googleapis.com --project="$PROJECT_ID"

echo "✅ Service Account API enabled"
echo ""

# ============================================
# Step 2: Enable Service Usage API (required)
# ============================================
echo "🔧 Step 2: Enabling Service Usage API..."

gcloud services enable serviceusage.googleapis.com --project="$PROJECT_ID"

echo "✅ Service Usage API enabled"
echo ""

# ============================================
# Step 3: Wait for APIs to propagate
# ============================================
echo "⏳ Waiting for APIs to propagate (30 seconds)..."
sleep 30
echo "✅ APIs should be ready"
echo ""

# ============================================
# Step 4: Get Project Number
# ============================================
echo "🔍 Step 4: Getting project number..."

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

echo "✅ Project Number: $PROJECT_NUMBER"
echo ""

# ============================================
# Step 5: Verify Service Accounts
# ============================================
echo "🔍 Step 5: Verifying service accounts..."

# Cloud Build service account
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
echo "Cloud Build SA: $CLOUD_BUILD_SA"

# Check if Cloud Build SA exists
if gcloud iam service-accounts describe "$CLOUD_BUILD_SA" --project="$PROJECT_ID" &>/dev/null; then
    echo "✅ Cloud Build service account exists"
else
    echo "⚠️  Cloud Build service account not found (will be created when Cloud Build is first used)"
fi

# Cloud Run runtime service account (Compute Engine default)
CLOUD_RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Cloud Run SA: $CLOUD_RUN_SA"

# Check if Cloud Run SA exists
if gcloud iam service-accounts describe "$CLOUD_RUN_SA" --project="$PROJECT_ID" &>/dev/null; then
    echo "✅ Cloud Run service account exists"
else
    echo "⚠️  Cloud Run service account not found (will be created automatically)"
fi

echo ""

# ============================================
# Step 6: Create Custom Service Account (Optional)
# ============================================
echo "🔧 Step 6: Custom Service Account (Optional)"
echo "============================================"
echo "Do you want to create a custom service account for Cloud Run?"
echo "This provides better security isolation (recommended for production)."
echo ""
read -p "Create custom service account? (y/N): " CREATE_CUSTOM

if [[ "$CREATE_CUSTOM" =~ ^[Yy]$ ]]; then
    SA_NAME="agora-cloudrun-sa"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    echo "Creating service account: $SA_NAME"

    # Create service account
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Agora Cloud Run Service Account" \
        --description="Service account for running Agora backend on Cloud Run" \
        --project="$PROJECT_ID"

    echo "✅ Custom service account created: $SA_EMAIL"
    echo ""

    # Grant necessary permissions
    echo "Granting permissions to custom service account..."

    # Secret Manager access (to read API keys)
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None

    echo "✅ Granted Secret Manager access"

    # Store for later use
    echo ""
    echo "📝 IMPORTANT: When deploying to Cloud Run, use this service account:"
    echo "   --service-account=$SA_EMAIL"
    echo ""
    echo "Update your cloudbuild.yaml with:"
    echo "   --service-account=$SA_EMAIL"
    echo ""
else
    echo "Skipping custom service account creation"
    echo "Will use default Compute Engine service account"
fi

echo ""

# ============================================
# Step 7: List All Service Accounts
# ============================================
echo "📋 Step 7: All Service Accounts in Project"
echo "============================================"

gcloud iam service-accounts list --project="$PROJECT_ID"

echo ""

# ============================================
# Summary
# ============================================
echo "============================================"
echo "✅ Service Account Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/setup_gcloud_infrastructure.sh"
echo "  2. Or continue with manual setup"
echo ""
echo "Service accounts ready:"
echo "  ✓ Cloud Build: $CLOUD_BUILD_SA"
echo "  ✓ Cloud Run: $CLOUD_RUN_SA"
if [[ "$CREATE_CUSTOM" =~ ^[Yy]$ ]]; then
    echo "  ✓ Custom Cloud Run: $SA_EMAIL"
fi
echo ""
