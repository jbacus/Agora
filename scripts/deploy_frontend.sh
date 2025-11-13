#!/bin/bash
# ============================================
# Frontend Deployment Script
# Deploys Agora frontend to Google Cloud Storage
# ============================================

set -e

echo "🚀 Agora Frontend Deployment"
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

# Configuration
BUCKET_NAME="${PROJECT_ID}-agora-frontend"
FRONTEND_DIR="src/ui"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

echo "📁 Frontend directory: $FRONTEND_DIR"
echo "🪣  Bucket: gs://$BUCKET_NAME"
echo ""

# Check if bucket exists
if ! gsutil ls "gs://$BUCKET_NAME" &>/dev/null; then
    echo "⚠️  Bucket does not exist. Creating..."
    gsutil mb -l us-central1 -c STANDARD "gs://$BUCKET_NAME"
    
    # Configure for website hosting
    gsutil web set -m index.html -e 404.html "gs://$BUCKET_NAME"
    
    # Make public
    gsutil iam ch allUsers:objectViewer "gs://$BUCKET_NAME"
    
    echo "✅ Bucket created and configured"
else
    echo "✅ Bucket exists"
fi

echo ""
echo "📤 Uploading frontend files..."

# Upload files
gsutil -m rsync -r -c -d "$FRONTEND_DIR/" "gs://$BUCKET_NAME/"

echo "✅ Files uploaded"
echo ""

# Get frontend URL
FRONTEND_URL="http://$BUCKET_NAME.storage.googleapis.com/index.html"

echo "============================================"
echo "✅ Frontend Deployed Successfully!"
echo "============================================"
echo ""
echo "📍 Frontend URL:"
echo "   $FRONTEND_URL"
echo ""
echo "🔗 Alternative URL:"
echo "   https://storage.googleapis.com/$BUCKET_NAME/index.html"
echo ""
echo "📝 Next steps:"
echo "   1. Open frontend URL in browser"
echo "   2. Update API_URL in src/ui/app.js with your backend URL"
echo "   3. Redeploy if needed: ./scripts/deploy_frontend.sh"
echo ""
echo "💡 Tip: Set up a custom domain for a cleaner URL"
echo ""
