# CI/CD End-to-End Testing Guide

This guide will walk you through testing the entire CI/CD pipeline from local Docker build to Cloud Run deployment.

## 🎯 Testing Objectives

1. ✅ Verify local Docker build works
2. ✅ Test container runs locally
3. ✅ Verify Google Cloud infrastructure is configured
4. ✅ Test Cloud Build configuration
5. ✅ Deploy to Cloud Run (production test)

---

## 🚀 Quick Test (Automated)

Run the automated test script:

```bash
# Run comprehensive CI/CD test
./scripts/test_cicd.sh
```

This script will:
- Check all prerequisites (gcloud, docker, auth)
- Build Docker image locally
- Run container and test endpoints
- Verify Google Cloud setup
- Validate Cloud Build configuration
- Check for Cloud Build triggers
- Provide next steps

---

## 📋 Manual Testing Steps

If you prefer to test manually or the automated script fails:

### Step 1: Setup Environment

```bash
# 1. Create .env file if not already done
cp .env.example .env

# 2. Edit .env and add your GEMINI_API_KEY
nano .env

# 3. Source environment variables
export $(grep -v '^#' .env | xargs)
```

### Step 2: Test Local Docker Build

```bash
# Build the image
docker build -t agora-backend:test .

# Verify build succeeded
docker images | grep agora-backend
```

**Expected output:**
```
agora-backend   test   [image-id]   [timestamp]   [size]
```

### Step 3: Test Local Container

```bash
# Run container
docker run -d \
  --name agora-test \
  -p 8080:8080 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e LLM_PROVIDER="gemini" \
  -e VECTOR_DB="chromadb" \
  agora-backend:test

# Wait for startup (15 seconds)
sleep 15

# Test health endpoint
curl http://localhost:8080/api/health | jq '.'

# Test authors endpoint
curl http://localhost:8080/api/authors | jq '.'

# View logs
docker logs agora-test

# Clean up
docker stop agora-test && docker rm agora-test
```

**Expected health response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "vector_db": "connected",
    "llm": "connected",
    "embeddings": "connected"
  }
}
```

### Step 4: Test with Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Test endpoints
curl http://localhost:8000/api/health

# Stop services
docker-compose down
```

### Step 5: Verify Google Cloud Setup

```bash
# Check current project
gcloud config get-value project

# Verify APIs are enabled
gcloud services list --enabled | grep -E "(iam|cloudbuild|run|artifactregistry|secretmanager)"

# Check Artifact Registry
gcloud artifacts repositories list --location=us-central1

# Check Secret Manager
gcloud secrets list

# Check service account permissions
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members~serviceAccount:${PROJECT_NUMBER}@cloudbuild"
```

**Expected:**
- ✅ All required APIs enabled
- ✅ `agora-images` repository exists
- ✅ `GEMINI_API_KEY` secret exists
- ✅ Cloud Build SA has required roles

### Step 6: Test Cloud Build (Manual Submit)

```bash
# Submit build manually (without trigger)
gcloud builds submit --config=cloudbuild.yaml .

# Monitor build
gcloud builds list --limit=5

# View detailed logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)')
```

**This will:**
1. Build Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run
4. Take ~5-10 minutes

### Step 7: Verify Cloud Run Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe agora-backend \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl $SERVICE_URL/api/health | jq '.'

# Test authors endpoint
curl $SERVICE_URL/api/authors | jq '.'

# View service details
gcloud run services describe agora-backend --region=us-central1

# View logs
gcloud run services logs read agora-backend --region=us-central1 --limit=50
```

### Step 8: Test CI/CD Trigger (Full Pipeline)

```bash
# Make a small change
echo "# Test deployment" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin main

# Monitor build (triggered automatically)
gcloud builds list --ongoing

# View logs in real-time
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)') --stream

# After ~5-10 minutes, verify deployment
curl $(gcloud run services describe agora-backend --region=us-central1 --format='value(status.url)')/api/health
```

---

## 🔍 Troubleshooting

### Build Fails Locally

**Issue:** Docker build fails

```bash
# Check Docker is running
docker ps

# View detailed build output
docker build -t agora-backend:test . --no-cache --progress=plain

# Check Dockerfile syntax
cat Dockerfile
```

### Container Won't Start

**Issue:** Container exits immediately

```bash
# View logs
docker logs agora-test

# Run interactively to debug
docker run -it --rm \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  agora-backend:test /bin/bash

# Check if port 8080 is already in use
lsof -i :8080
```

### Cloud Build Fails

**Issue:** Build fails in Cloud Build

```bash
# View full logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)')

# Common issues:
# 1. Permission denied
#    -> Check IAM permissions (run setup script again)
# 2. Artifact Registry not found
#    -> Run: gcloud artifacts repositories create agora-images --location=us-central1 --repository-format=docker
# 3. Secret not accessible
#    -> Grant Cloud Build SA access to secret
```

### Cloud Run Deployment Fails

**Issue:** Service won't deploy

```bash
# Check deployment status
gcloud run services describe agora-backend --region=us-central1

# Common issues:
# 1. Image not found
#    -> Verify image in Artifact Registry: gcloud artifacts docker images list us-central1-docker.pkg.dev/PROJECT_ID/agora-images
# 2. Container crashes
#    -> View logs: gcloud run services logs read agora-backend --region=us-central1 --limit=100
# 3. Health check fails
#    -> Check /api/health endpoint returns 200
```

### API Returns Errors

**Issue:** Health endpoint returns unhealthy

```bash
# Common causes:
# 1. API key not accessible
#    -> Check secret: gcloud secrets versions access latest --secret=GEMINI_API_KEY
#    -> Grant runtime SA access: gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
#         --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
#         --role="roles/secretmanager.secretAccessor"

# 2. ChromaDB initialization failed
#    -> Check logs for "Failed to initialize"
#    -> Verify memory allocation (should be 2Gi minimum)

# 3. LLM client failed
#    -> Check API key is valid
#    -> Test: curl -H "x-goog-api-key: $GEMINI_API_KEY" \
#         "https://generativelanguage.googleapis.com/v1beta/models"
```

---

## ✅ Success Criteria

Your CI/CD pipeline is working correctly when:

### Local Testing
- [x] Docker build completes without errors
- [x] Container starts and runs without crashing
- [x] `/api/health` returns `{"status": "healthy"}`
- [x] `/api/authors` returns author list (or empty array if no data)

### Google Cloud Setup
- [x] All required APIs enabled
- [x] Artifact Registry repository exists
- [x] Secret Manager has GEMINI_API_KEY
- [x] Cloud Build SA has necessary permissions
- [x] Cloud Build trigger exists for main branch

### Cloud Deployment
- [x] Cloud Build completes successfully (~5-10 min)
- [x] Image pushed to Artifact Registry
- [x] Cloud Run service deployed
- [x] Service URL accessible and returns healthy status
- [x] Logs show no errors

### CI/CD Automation
- [x] Push to main branch triggers automatic build
- [x] Build runs without manual intervention
- [x] Deployment completes automatically
- [x] Service updates with new code

---

## 📊 Test Results Template

Copy and fill this out as you test:

```
# CI/CD Test Results

Date: _________
Tester: _________

## Local Testing
- [ ] Docker build: PASS / FAIL
- [ ] Container run: PASS / FAIL
- [ ] Health endpoint: PASS / FAIL
- [ ] Authors endpoint: PASS / FAIL

## Google Cloud Setup
- [ ] APIs enabled: PASS / FAIL
- [ ] Artifact Registry: PASS / FAIL
- [ ] Secret Manager: PASS / FAIL
- [ ] IAM permissions: PASS / FAIL
- [ ] Build trigger: PASS / FAIL

## Cloud Deployment
- [ ] Manual build submit: PASS / FAIL
- [ ] Cloud Run deployment: PASS / FAIL
- [ ] Service accessible: PASS / FAIL
- [ ] Automated trigger: PASS / FAIL

## Issues Found:
1.
2.
3.

## Service URL:
https://agora-backend-[hash]-uc.a.run.app

## Build Time:
_______ minutes

## Notes:
```

---

## 🎯 Next Steps After Successful Test

1. **Merge to main** (if testing on a branch)
2. **Add author data** (see Phase 1A in README)
3. **Run data ingestion**
4. **Redeploy with data**
5. **Build frontend UI**
6. **Set up monitoring**
7. **Configure custom domain**

---

## 📚 Reference Commands

### Quick Reference

```bash
# Local test
./scripts/test_cicd.sh

# Manual build and test
docker build -t agora-backend:test . && \
docker run -d --name agora-test -p 8080:8080 -e GEMINI_API_KEY="$GEMINI_API_KEY" agora-backend:test && \
sleep 15 && \
curl http://localhost:8080/api/health

# Cloud Build
gcloud builds submit --config=cloudbuild.yaml .

# View Cloud Run service
gcloud run services describe agora-backend --region=us-central1

# Get service URL
gcloud run services describe agora-backend --region=us-central1 --format='value(status.url)'

# View logs
gcloud run services logs read agora-backend --region=us-central1 --limit=100 --format=json | jq '.textPayload'
```

---

**Questions?** See `docs/DEPLOYMENT.md` for comprehensive deployment documentation.
