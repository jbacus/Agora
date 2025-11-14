#!/bin/bash
# ============================================
# Google Secret Manager Setup Script
# Creates secrets for API keys in GCP
# ============================================

set -e

echo "🔐 Google Secret Manager Setup"
echo "============================================"
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📦 Project: $PROJECT_ID"
echo ""

# Enable Secret Manager API
echo "🔧 Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
echo "✅ Secret Manager API enabled"
echo ""

# Function to create or update a secret
create_secret() {
    local SECRET_NAME=$1
    local SECRET_DESCRIPTION=$2

    echo "🔑 Setting up: $SECRET_NAME"

    # Check if secret exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "  ℹ️  Secret $SECRET_NAME already exists"
        read -p "  Do you want to add a new version? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "  ⏭️  Skipping $SECRET_NAME"
            return
        fi
    else
        # Create the secret
        echo "  Creating secret..."
        gcloud secrets create $SECRET_NAME \
            --project=$PROJECT_ID \
            --replication-policy="automatic" \
            --labels=app=agora,environment=production
        echo "  ✅ Secret created"
    fi

    # Prompt for secret value
    echo "  📝 Enter value for $SECRET_NAME:"
    echo "     ($SECRET_DESCRIPTION)"
    read -s SECRET_VALUE
    echo ""

    if [ -z "$SECRET_VALUE" ]; then
        echo "  ⚠️  Empty value, skipping..."
        return
    fi

    # Add secret version
    echo "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME \
        --project=$PROJECT_ID \
        --data-file=-

    echo "  ✅ Secret version added"
    echo ""
}

# Create secrets for each API key
echo "============================================"
echo "Setting up API key secrets"
echo "============================================"
echo ""

create_secret "GEMINI_API_KEY" "Get from https://aistudio.google.com/app/apikey"
create_secret "OPENAI_API_KEY" "Get from https://platform.openai.com/api-keys"
create_secret "ANTHROPIC_API_KEY" "Get from https://console.anthropic.com/settings/keys"
create_secret "PINECONE_API_KEY" "Get from https://app.pinecone.io/organizations"

echo "============================================"
echo "✅ Secret Manager Setup Complete!"
echo "============================================"
echo ""

# Grant Cloud Run service account access to secrets
echo "🔐 Granting Cloud Run access to secrets..."
echo ""

# Get Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
CLOUD_RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Cloud Run Service Account: $CLOUD_RUN_SA"
echo ""

# Grant Secret Accessor role for each secret
for SECRET_NAME in GEMINI_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY PINECONE_API_KEY; do
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "  Granting access to $SECRET_NAME..."
        gcloud secrets add-iam-policy-binding $SECRET_NAME \
            --project=$PROJECT_ID \
            --member="serviceAccount:$CLOUD_RUN_SA" \
            --role="roles/secretmanager.secretAccessor" \
            --quiet 2>/dev/null || true
        echo "  ✅ Access granted"
    fi
done

echo ""
echo "============================================"
echo "📋 Next Steps"
echo "============================================"
echo ""
echo "1. Verify secrets:"
echo "   gcloud secrets list --project=$PROJECT_ID"
echo ""
echo "2. View a secret value (for testing):"
echo "   gcloud secrets versions access latest --secret=GEMINI_API_KEY"
echo ""
echo "3. Deploy to Cloud Run:"
echo "   The application will automatically fetch secrets from Secret Manager"
echo ""
echo "4. For local development:"
echo "   Continue using .env file (Secret Manager is optional locally)"
echo ""
echo "5. Update cloudbuild.yaml if needed:"
echo "   Secrets are already configured to be mounted in Cloud Run"
echo ""
