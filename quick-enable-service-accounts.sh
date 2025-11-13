#!/bin/bash
# Quick Service Account Enablement
# Run this to enable service accounts for Google Cloud deployment

set -e

echo "🔧 Enabling Service Accounts..."

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ No project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📦 Project: $PROJECT_ID"

# Enable APIs
echo "Enabling IAM API..."
gcloud services enable iam.googleapis.com

echo "Enabling Service Usage API..."
gcloud services enable serviceusage.googleapis.com

echo "⏳ Waiting 30 seconds for APIs to propagate..."
sleep 30

# Verify
echo ""
echo "📋 Service Accounts:"
gcloud iam service-accounts list

echo ""
echo "✅ Done! Service accounts are now enabled."
echo ""
echo "Next step: Run ./scripts/setup_gcloud_infrastructure.sh"
