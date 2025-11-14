# Deployment Guide - Virtual Debate Panel

This guide covers deploying the Virtual Debate Panel to Google Cloud Platform with automatic CI/CD.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Manual Setup](#manual-setup)
5. [Local Development](#local-development)
6. [Production Deployment](#production-deployment)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Deployment Architecture

```
GitHub Repository
    ↓ (push to main)
Cloud Build Trigger
    ↓
    ├─→ Build Docker Image
    │      ↓
    │   Push to Artifact Registry
    │      ↓
    │   Deploy Backend to Cloud Run
    │
    └─→ Deploy Frontend to Cloud Storage
           ↓
        Configure bucket for web hosting
           ↓
        Set public permissions
```

### Components

- **Backend**: FastAPI app on Google Cloud Run
- **Frontend**: Static files on Google Cloud Storage
- **Vector DB**: ChromaDB (in-container, persistent volume)
- **Images**: Artifact Registry
- **Secrets**: Secret Manager
- **CI/CD**: Cloud Build (automated full-stack deployment)

### Resource Names

| Resource | Name | Purpose |
|----------|------|---------|
| Cloud Run Service | `agora-backend` | FastAPI application |
| Artifact Registry | `agora-images` | Docker images |
| GCS Bucket | `{project-id}-agora-frontend` | Frontend static files |
| Secret | `GEMINI_API_KEY` | LLM API key |

---

## Prerequisites

### Required Tools

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Verify installation
gcloud --version

# Authenticate
gcloud auth login

# Set up Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Required Accounts

1. **Google Cloud Platform**
   - Active GCP project with billing enabled
   - Owner or Editor permissions

2. **Gemini API**
   - API key from https://aistudio.google.com/app/apikey

3. **GitHub**
   - Repository with code
   - Admin access to repository

---

## Quick Start

### Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/Agora.git
cd Agora

# 2. Run infrastructure setup script
chmod +x scripts/setup_gcloud_infrastructure.sh
./scripts/setup_gcloud_infrastructure.sh

# Follow the interactive prompts:
#   - Enter your GCP Project ID (or create new)
#   - Enter your Gemini API Key
#   - Review the created resources
```

This script will:
- ✅ Enable required Google Cloud APIs
- ✅ Create Artifact Registry repository
- ✅ Create Cloud Storage bucket for frontend
- ✅ Store API key in Secret Manager
- ✅ Configure IAM permissions for Cloud Build
- ✅ Provide instructions for Cloud Build trigger setup

### Create Cloud Build Trigger

After running the setup script, create a Cloud Build trigger:

**Option 1: Cloud Console (Recommended)**

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **"Connect Repository"**
3. Select **GitHub** and authorize
4. Choose your repository: `YOUR_USERNAME/Agora`
5. Click **"Create Trigger"** with these settings:
   - **Name**: `agora-full-stack-deploy`
   - **Event**: Push to a branch
   - **Branch**: `^main$`
   - **Configuration**: Cloud Build configuration file
   - **Location**: `cloudbuild.yaml`
6. Click **"Create"**

**What Gets Deployed Automatically:**
- ✅ Backend Docker image → Artifact Registry → Cloud Run
- ✅ Frontend static files → Cloud Storage bucket
- ✅ Bucket configured for web hosting with public access
- ✅ API endpoint automatically configured in frontend

**Option 2: gcloud CLI**

```bash
# Connect repository first (if not already connected)
gcloud beta builds triggers create github \
  --repo-name=Agora \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name=agora-full-stack-deploy \
  --description="Deploy Agora backend and frontend (full-stack)" \
  --region=us-central1
```

### Test Deployment

```bash
# Push to main branch to trigger deployment
git add .
git commit -m "Initial deployment"
git push origin main

# Monitor build (both backend and frontend deployment)
gcloud builds list --limit=5

# View logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)')

# Get backend API URL
gcloud run services describe agora-backend \
  --region=us-central1 \
  --format='value(status.url)'

# Get frontend URL
export PROJECT_ID=$(gcloud config get-value project)
echo "Frontend URL: https://storage.googleapis.com/agora-frontend-${PROJECT_ID}/index.html"

# Test backend health
curl $(gcloud run services describe agora-backend --region=us-central1 --format='value(status.url)')/api/health

# Open frontend in browser
open "https://storage.googleapis.com/agora-frontend-${PROJECT_ID}/index.html"
```

**Expected Results:**
- ✅ Cloud Build completes all 7 steps successfully
- ✅ Backend API responds at `/api/health`
- ✅ Frontend loads and connects to backend
- ✅ Both backend and frontend update on every push to main

---

## Manual Setup

If you prefer to set up infrastructure manually:

### 1. Create Google Cloud Project

```bash
# Set project ID
export PROJECT_ID="your-project-id"

# Create project
gcloud projects create $PROJECT_ID --name="Virtual Debate Panel"

# Set as default
gcloud config set project $PROJECT_ID

# Link billing account (required!)
# Visit: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID
```

### 2. Enable APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 3. Create Artifact Registry

```bash
gcloud artifacts repositories create agora-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for Virtual Debate Panel"
```

### 4. Create Cloud Storage Bucket

```bash
# Create bucket
gsutil mb -l us-central1 -c STANDARD gs://$PROJECT_ID-agora-frontend

# Configure for website hosting
gsutil web set -m index.html -e 404.html gs://$PROJECT_ID-agora-frontend

# Make public
gsutil iam ch allUsers:objectViewer gs://$PROJECT_ID-agora-frontend
```

### 5. Store API Key in Secret Manager

```bash
# Create secret
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --replication-policy="automatic"

# Verify
gcloud secrets versions access latest --secret="GEMINI_API_KEY"
```

### 6. Configure IAM Permissions

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Cloud Build service account
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant Cloud Run admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role="roles/run.admin"

# Grant service account user
gcloud iam service-accounts add-iam-policy-binding \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role="roles/iam.serviceAccountUser"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role="roles/secretmanager.secretAccessor"

# Grant Artifact Registry writer
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role="roles/artifactregistry.writer"
```

---

## Local Development

### Using Docker Compose

```bash
# 1. Create .env file
cp .env.example .env

# 2. Edit .env and add your API keys
nano .env

# 3. Start services
docker-compose up -d

# 4. View logs
docker-compose logs -f backend

# 5. Test API
curl http://localhost:8000/api/health

# 6. Stop services
docker-compose down
```

### Using Python Directly (Poetry)

```bash
# 1. Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# 2. Install dependencies (Poetry automatically creates virtual environment)
poetry install

# 3. Set environment variables
export GEMINI_API_KEY="your-key"
export LLM_PROVIDER="gemini"
export VECTOR_DB="chromadb"

# 4. Run the application using Poetry
poetry run uvicorn src.api.main:app --reload --port 8000

# 5. Open browser
# http://localhost:8000/docs  (API documentation)
```

**Alternative: Using pip directly**
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
uvicorn src.api.main:app --reload --port 8000
```

### Local Testing Workflow

```bash
# Test Docker build
docker build -t agora-backend:local .

# Run container
docker run -p 8000:8080 \
  -e GEMINI_API_KEY="your-key" \
  -e LLM_PROVIDER="gemini" \
  agora-backend:local

# Test endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/authors
```

---

## Production Deployment

### Deployment Process

1. **Commit changes**
   ```bash
   git add .
   git commit -m "Your commit message"
   ```

2. **Push to main branch**
   ```bash
   git push origin main
   ```

3. **Monitor Cloud Build**
   - View in console: https://console.cloud.google.com/cloud-build/builds
   - Or via CLI:
     ```bash
     gcloud builds list --limit=5
     gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)')
     ```

4. **Verify deployment**
   ```bash
   # Get service URL
   SERVICE_URL=$(gcloud run services describe agora-backend \
     --region=us-central1 \
     --format='value(status.url)')

   echo "Service URL: $SERVICE_URL"

   # Test health endpoint
   curl $SERVICE_URL/api/health

   # Test authors endpoint
   curl $SERVICE_URL/api/authors
   ```

### Environment Variables

Configure in Cloud Run service:

```bash
gcloud run services update agora-backend \
  --region=us-central1 \
  --set-env-vars="LLM_PROVIDER=gemini,VECTOR_DB=chromadb,LOG_LEVEL=INFO"
```

Or in Cloud Console:
1. Go to Cloud Run → agora-backend
2. Click **"Edit & Deploy New Revision"**
3. Go to **"Variables & Secrets"** tab
4. Add environment variables

### Scaling Configuration

```bash
# Update scaling parameters
gcloud run services update agora-backend \
  --region=us-central1 \
  --min-instances=1 \
  --max-instances=10 \
  --concurrency=80 \
  --memory=2Gi \
  --cpu=1 \
  --timeout=300s
```

### Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=agora-backend \
  --domain=api.yourdomain.com \
  --region=us-central1

# Follow DNS instructions provided by the command
```

---

## Monitoring & Maintenance

### View Logs

```bash
# Recent logs
gcloud run services logs read agora-backend \
  --region=us-central1 \
  --limit=100

# Live tail
gcloud run services logs tail agora-backend \
  --region=us-central1

# Filter by severity
gcloud run services logs read agora-backend \
  --region=us-central1 \
  --log-filter='severity>=ERROR'
```

### Monitor Metrics

Cloud Console: https://console.cloud.google.com/run/detail/us-central1/agora-backend/metrics

Key metrics:
- Request count
- Request latency (p50, p95, p99)
- Error rate
- CPU utilization
- Memory utilization
- Container instance count

### Update API Key

```bash
# Update secret
echo -n "NEW_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

# Redeploy service (to pick up new secret)
gcloud run services update agora-backend \
  --region=us-central1 \
  --update-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest
```

### Rollback Deployment

```bash
# List revisions
gcloud run revisions list \
  --service=agora-backend \
  --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic agora-backend \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

---

## Troubleshooting

### Build Failures

**Error: Permission denied**
```bash
# Check Cloud Build service account permissions
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects get-iam-policy $PROJECT_ID \
  --filter="bindings.members:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
```

**Error: Docker build timeout**
```yaml
# Update cloudbuild.yaml timeout
timeout: '3600s'  # Increase from default
```

### Deployment Failures

**Error: Service not found**
```bash
# Check Cloud Run service exists
gcloud run services list --region=us-central1

# Create service if missing (first deployment)
gcloud run deploy agora-backend \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/agora-images/agora-backend:latest \
  --region=us-central1 \
  --platform=managed
```

**Error: Permission denied on Secret**
```bash
# Grant Secret Manager access
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Runtime Errors

**Error: Vector DB not initialized**
```bash
# Check logs for initialization errors
gcloud run services logs read agora-backend --region=us-central1 --limit=100

# Verify ChromaDB directory is writable
# Check Dockerfile USER permissions
```

**Error: API key invalid**
```bash
# Verify secret value
gcloud secrets versions access latest --secret="GEMINI_API_KEY"

# Test API key locally
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_KEY"
```

### Performance Issues

**High latency**
- Increase CPU allocation: `--cpu=2`
- Increase memory: `--memory=4Gi`
- Increase min instances: `--min-instances=1`
- Check embedding generation time in logs

**Out of memory**
```bash
# Increase memory allocation
gcloud run services update agora-backend \
  --region=us-central1 \
  --memory=4Gi
```

---

## Cost Optimization

### Estimated Monthly Costs (Light Usage)

- Cloud Run: $5-20/month (100 requests/day)
- Cloud Storage: $0.50/month (1GB frontend)
- Artifact Registry: $0.10/month (1GB images)
- Secret Manager: $0.06/month (1 secret)
- **Total**: ~$6-21/month

### Cost Reduction Tips

1. **Use minimum instances = 0** (cold starts acceptable)
2. **Use Gemini Flash** instead of Pro for cheaper LLM calls
3. **Enable request caching** to reduce LLM API calls
4. **Set max instances** to prevent runaway costs
5. **Use Cloud Build only on main branch** (not all commits)

---

## Security Best Practices

### Secrets Management

- ✅ Store API keys in Secret Manager (never in code)
- ✅ Use environment variable references in Cloud Run
- ✅ Rotate API keys regularly
- ✅ Use service-specific API keys with minimal permissions

### Network Security

```bash
# Restrict ingress (optional)
gcloud run services update agora-backend \
  --region=us-central1 \
  --ingress=internal-and-cloud-load-balancing

# Enable Cloud Armor (DDoS protection)
# See: https://cloud.google.com/armor/docs/configure-security-policies
```

### Authentication

```bash
# Require authentication
gcloud run services update agora-backend \
  --region=us-central1 \
  --no-allow-unauthenticated

# Then use:
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://YOUR_SERVICE_URL/api/health
```

---

## Next Steps

1. ✅ Deploy backend to Cloud Run
2. ✅ Build frontend UI
3. ✅ Deploy frontend to Cloud Storage (automated via Cloud Build)
4. ✅ Implement streaming responses
5. ✅ Add response caching
6. ✅ Add usage analytics
7. ⏳ Set up custom domain
8. ⏳ Add monitoring alerts

---

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [ChromaDB Documentation](https://docs.trychroma.com/)

---

**Questions?** Open an issue on GitHub or check the [Architecture Documentation](ARCHITECTURE.md).
