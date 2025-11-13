# Automated Deployment Guide

## Overview

The Agora Virtual Debate Panel now features **true full-stack automated deployment** via Google Cloud Build. A single push to the `main` branch automatically deploys both backend and frontend with zero manual intervention.

## What Gets Automated

### Backend Deployment
1. ✅ Docker image build with multi-stage optimization
2. ✅ Push to Artifact Registry
3. ✅ Deploy to Cloud Run with auto-scaling
4. ✅ Environment variables and secrets configuration
5. ✅ Health checks and readiness probes

### Frontend Deployment
1. ✅ GCS bucket creation (if doesn't exist)
2. ✅ Static website hosting configuration
3. ✅ API endpoint auto-configuration in frontend
4. ✅ File sync to Cloud Storage
5. ✅ Cache control headers for optimal performance
6. ✅ Public access permissions

## How It Works

### Trigger Event
```bash
git push origin main
```

### Cloud Build Pipeline (7 Steps)

```
Step 1: Build Docker Image
   ├─ Multi-stage build for optimal size
   ├─ Install dependencies
   └─ Configure runtime environment

Step 2: Push to Artifact Registry
   └─ Store versioned Docker images

Step 3: Deploy Backend to Cloud Run
   ├─ Deploy with latest image
   ├─ Configure auto-scaling (0-10 instances)
   ├─ Set environment variables
   └─ Inject secrets from Secret Manager

Step 4: Create Frontend Bucket
   └─ Create GCS bucket if doesn't exist

Step 5: Configure Bucket for Web Hosting
   └─ Set index.html as main page

Step 6: Deploy Frontend Files
   ├─ Auto-update API endpoint in app.js
   ├─ Sync all frontend files
   └─ Set cache control headers

Step 7: Set Public Permissions
   └─ Make bucket publicly accessible
```

### Total Deployment Time
- **Backend**: ~5-8 minutes
- **Frontend**: ~30-60 seconds
- **Total**: ~6-9 minutes

## Configuration

### Cloud Build Substitution Variables

Located in `cloudbuild.yaml`:

```yaml
substitutions:
  _REGION: 'us-central1'                          # GCP region
  _SERVICE_NAME: 'agora-backend'                  # Cloud Run service name
  _ARTIFACT_REGISTRY_REPO: 'agora-images'         # Docker repository
  _FRONTEND_BUCKET: 'agora-frontend-${PROJECT_ID}' # GCS bucket
  _LLM_PROVIDER: 'gemini'                         # LLM provider
  _VECTOR_DB: 'chromadb'                          # Vector database
  _EMBEDDING_MODEL: 'text-embedding-004'          # Embedding model
  _LOG_LEVEL: 'INFO'                              # Logging level
  _GEMINI_API_KEY_SECRET: 'GEMINI_API_KEY:latest' # Secret name
```

### Customization

You can override these in the Cloud Build trigger settings:

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click on your trigger (`agora-full-stack-deploy`)
3. Click "Edit"
4. Scroll to "Substitution variables"
5. Override any defaults
6. Click "Save"

## Deployment URLs

After successful deployment:

### Backend API
```bash
# Get URL
gcloud run services describe agora-backend \
  --region=us-central1 \
  --format='value(status.url)'

# Example: https://agora-backend-abc123-uc.a.run.app
```

### Frontend Web App
```bash
# Get URL
export PROJECT_ID=$(gcloud config get-value project)
echo "https://storage.googleapis.com/agora-frontend-${PROJECT_ID}/index.html"

# Example: https://storage.googleapis.com/agora-frontend-my-project/index.html
```

## Monitoring Deployments

### View Build Status

**Cloud Console:**
1. Go to [Cloud Build History](https://console.cloud.google.com/cloud-build/builds)
2. See all builds with status, duration, and logs

**CLI:**
```bash
# List recent builds
gcloud builds list --limit=10

# View specific build logs
gcloud builds log BUILD_ID

# Follow latest build
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)') --stream
```

### Build Notifications

Set up email/Slack notifications:

```bash
# Enable Cloud Build notifications
gcloud alpha builds connections create github \
  --region=us-central1

# Configure in Cloud Console:
# Cloud Build > Settings > Notifications
```

## Testing Automated Deployment

### End-to-End Test

1. **Make a change:**
   ```bash
   echo "// Test change" >> src/api/routes.py
   ```

2. **Commit and push:**
   ```bash
   git add .
   git commit -m "test: Verify automated deployment"
   git push origin main
   ```

3. **Monitor deployment:**
   ```bash
   # Watch build progress
   gcloud builds list --limit=1 --ongoing

   # Wait for completion (~6-9 minutes)
   ```

4. **Verify backend:**
   ```bash
   curl $(gcloud run services describe agora-backend \
     --region=us-central1 \
     --format='value(status.url)')/api/health

   # Expected: {"status": "healthy", ...}
   ```

5. **Verify frontend:**
   ```bash
   export PROJECT_ID=$(gcloud config get-value project)
   curl -I "https://storage.googleapis.com/agora-frontend-${PROJECT_ID}/index.html"

   # Expected: HTTP/2 200
   ```

## Rollback

### Automatic Rollback
Cloud Run keeps previous revisions. To rollback:

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

### Frontend Rollback
Frontend files in GCS don't have automatic versioning. Options:

1. **Re-deploy from git:**
   ```bash
   git revert HEAD
   git push origin main
   # Automated deployment will restore previous version
   ```

2. **Manual rollback:**
   ```bash
   git checkout <previous-commit>
   ./scripts/deploy_frontend.sh
   ```

3. **Enable GCS versioning (recommended):**
   ```bash
   gsutil versioning set on gs://agora-frontend-${PROJECT_ID}

   # List versions
   gsutil ls -a gs://agora-frontend-${PROJECT_ID}/

   # Restore specific version
   gsutil cp gs://agora-frontend-${PROJECT_ID}/index.html#<generation> \
     gs://agora-frontend-${PROJECT_ID}/index.html
   ```

## Cost Optimization

### Cloud Build
- **Free tier**: 120 build-minutes/day
- **Cost**: $0.003/build-minute after free tier
- **Average cost**: $0.02-0.03 per deployment

### Cloud Run
- **Free tier**: 2M requests/month, 360K GB-seconds/month
- **Auto-scaling**: Scales to zero when idle
- **Average cost**: $0-5/month for low-traffic

### Cloud Storage
- **Free tier**: 5 GB storage, 1 GB egress
- **Frontend size**: ~50 KB (well within free tier)
- **Average cost**: $0-1/month

### Total Monthly Cost
- **Development**: $0-5 (within free tiers)
- **Light production**: $5-20
- **Heavy production**: $50-200 (depends on traffic)

## Security

### Secrets Management
- ✅ API keys stored in Secret Manager
- ✅ Never committed to git
- ✅ Encrypted at rest and in transit
- ✅ Access via IAM permissions only

### Network Security
- ✅ HTTPS-only for Cloud Run
- ✅ Cloud Run service URL is publicly accessible (required for frontend)
- ✅ Rate limiting via Cloud Run (max 80 concurrent requests per instance)

### IAM Permissions
Cloud Build service account requires:
- `roles/run.admin` - Deploy to Cloud Run
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/secretmanager.secretAccessor` - Access secrets
- `roles/artifactregistry.writer` - Push Docker images
- `roles/storage.admin` - Deploy frontend to GCS

## Troubleshooting

### Build Failures

**Symptom**: Build fails at Step 1 (Docker build)
```
ERROR: failed to build: exit status 1
```

**Solution**:
1. Check Dockerfile syntax
2. Verify dependencies in requirements.txt
3. Test locally: `docker build -t test .`

---

**Symptom**: Build fails at Step 3 (Cloud Run deploy)
```
ERROR: (gcloud.run.deploy) Permission denied
```

**Solution**:
1. Check IAM permissions (see [Service Account Guide](SERVICE_ACCOUNTS_GUIDE.md))
2. Verify Cloud Run API is enabled
3. Run: `./scripts/enable_service_accounts.sh`

---

**Symptom**: Build fails at Step 6 (Frontend deploy)
```
ERROR: AccessDeniedException: 403 Forbidden
```

**Solution**:
1. Ensure Cloud Build has Storage Admin role
2. Check bucket exists: `gsutil ls gs://agora-frontend-${PROJECT_ID}`
3. Verify bucket permissions

### Frontend Not Loading

**Symptom**: Frontend loads but shows "API connection failed"

**Solution**:
1. Check API URL in browser console
2. Verify backend is running:
   ```bash
   curl $(gcloud run services describe agora-backend \
     --region=us-central1 \
     --format='value(status.url)')/api/health
   ```
3. Check CORS configuration in backend

---

**Symptom**: Frontend shows 404 on GCS

**Solution**:
1. Verify files were uploaded:
   ```bash
   gsutil ls gs://agora-frontend-${PROJECT_ID}
   ```
2. Check bucket website configuration:
   ```bash
   gsutil web get gs://agora-frontend-${PROJECT_ID}
   ```
3. Manually deploy: `./scripts/deploy_frontend.sh`

### Slow Deployments

**Symptom**: Builds taking >15 minutes

**Solution**:
1. Check machine type in cloudbuild.yaml (currently N1_HIGHCPU_8)
2. Review Docker layer caching
3. Consider Cloud Build private pools for faster builds

## Advanced Configuration

### Custom Domain

Set up custom domain for cleaner URLs:

**Backend (Cloud Run):**
```bash
# Map custom domain
gcloud beta run domain-mappings create \
  --service agora-backend \
  --domain api.yourdomain.com \
  --region us-central1

# Follow DNS setup instructions
```

**Frontend (Cloud Storage):**
```bash
# Configure load balancer with custom domain
# See: https://cloud.google.com/storage/docs/hosting-static-website
```

### Multiple Environments

Create separate triggers for staging/production:

**Staging:**
- Branch: `develop`
- Services: `agora-backend-staging`, `agora-frontend-staging`

**Production:**
- Branch: `main`
- Services: `agora-backend`, `agora-frontend`

```bash
# Create staging trigger
gcloud builds triggers create github \
  --repo-name=Agora \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^develop$" \
  --build-config=cloudbuild.yaml \
  --name=agora-staging-deploy \
  --substitutions=_SERVICE_NAME=agora-backend-staging
```

### Build Optimization

**Docker Layer Caching:**
```yaml
# In cloudbuild.yaml
options:
  machineType: 'N1_HIGHCPU_8'
  logging: 'CLOUD_LOGGING_ONLY'
  dynamicSubstitutions: true
  # Add Kaniko cache
  env:
    - 'DOCKER_BUILDKIT=1'
```

**Parallel Steps:**
Currently backend and frontend deploy sequentially. For faster deployment, consider:
- Separate triggers for backend/frontend
- Deploy in parallel when changes don't affect both

## Next Steps

Now that deployment is fully automated:

1. ✅ **Set up custom domain** for cleaner URLs
2. ✅ **Enable monitoring** with Cloud Monitoring
3. ✅ **Configure alerts** for errors/high latency
4. ✅ **Set up staging environment** for testing
5. ✅ **Enable GCS versioning** for frontend rollback
6. ✅ **Configure CDN** for global performance

## Additional Resources

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/tips)
- [GCS Static Website Hosting](https://cloud.google.com/storage/docs/hosting-static-website)
- [CI/CD Guide](CI_CD_SETUP.md)
- [Service Account Setup](SERVICE_ACCOUNTS_GUIDE.md)

---

**Questions?** Check [Troubleshooting](#troubleshooting) or open an issue on GitHub.
