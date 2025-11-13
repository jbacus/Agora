# 🚀 Quick Start: Deploy to Google Cloud

Get your Virtual Debate Panel running in the cloud in 15 minutes!

## Prerequisites Checklist

- [ ] Google Cloud account with billing enabled
- [ ] `gcloud` CLI installed ([download](https://cloud.google.com/sdk/docs/install))
- [ ] Gemini API key ([get one](https://aistudio.google.com/app/apikey))
- [ ] Git repository (GitHub recommended)

## Step-by-Step Deployment

### 1️⃣ Authenticate with Google Cloud (2 min)

```bash
# Login to Google Cloud
gcloud auth login

# Set up Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 2️⃣ Run Infrastructure Setup (5 min)

```bash
# Navigate to project directory
cd Agora

# Run setup script
chmod +x scripts/setup_gcloud_infrastructure.sh
./scripts/setup_gcloud_infrastructure.sh
```

**The script will prompt you for:**
- Google Cloud Project ID (or create a new one)
- Gemini API Key

**What it creates:**
- ✅ Artifact Registry for Docker images
- ✅ Cloud Storage bucket for frontend
- ✅ Secret Manager for API key
- ✅ IAM permissions for Cloud Build

### 3️⃣ Connect GitHub Repository (3 min)

#### Option A: Cloud Console (Recommended)

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **"Connect Repository"**
3. Select **GitHub** → Authorize
4. Choose your `Agora` repository
5. Click **"Create Trigger"**:
   - **Name**: `agora-backend-deploy`
   - **Event**: Push to branch `^main$`
   - **Configuration**: `cloudbuild.yaml`
6. Click **"Create"**

#### Option B: Command Line

```bash
gcloud beta builds triggers create github \
  --repo-name=Agora \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --region=us-central1
```

### 4️⃣ Deploy! (5 min)

```bash
# Commit the new CI/CD files
git add .
git commit -m "Add CI/CD configuration"

# Push to trigger deployment
git push origin main
```

### 5️⃣ Monitor Deployment

```bash
# Watch build progress
gcloud builds list --limit=5

# View detailed logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)')
```

### 6️⃣ Test Your API

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe agora-backend \
  --region=us-central1 \
  --format='value(status.url)')

echo "🎉 Your API is live at: $SERVICE_URL"

# Test health endpoint
curl $SERVICE_URL/api/health

# Test authors endpoint
curl $SERVICE_URL/api/authors
```

---

## Common Issues & Quick Fixes

### ❌ "Permission denied" during build

```bash
# Re-run IAM configuration
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
```

### ❌ "Build timeout"

Edit `cloudbuild.yaml` and increase timeout:
```yaml
timeout: '3600s'  # Increase to 60 minutes
```

### ❌ "No data loaded" error

The backend needs data ingestion first! See the main README for instructions on:
1. Adding author texts to `data/raw/`
2. Running `python scripts/ingest_author.py`
3. Rebuilding and redeploying

### ❌ "Invalid API key"

```bash
# Update the secret
echo -n "YOUR_NEW_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

# Redeploy service
gcloud run services update agora-backend \
  --region=us-central1 \
  --update-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest
```

---

## What's Next?

Now that your backend is deployed:

1. **Add Data**:
   - Download author texts (see README Phase 1A)
   - Run ingestion locally
   - Rebuild Docker image with data

2. **Build Frontend**:
   - Create UI in `src/ui/`
   - Deploy to Cloud Storage bucket
   - Point to your backend API

3. **Custom Domain**:
   - Map `api.yourdomain.com` to Cloud Run
   - Set up SSL certificate

4. **Monitoring**:
   - View metrics in Cloud Console
   - Set up alerting
   - Monitor costs

---

## Cost Estimate

**Monthly costs for light usage (100 requests/day):**

| Service | Cost |
|---------|------|
| Cloud Run | $5-20 |
| Cloud Storage | $0.50 |
| Artifact Registry | $0.10 |
| Secret Manager | $0.06 |
| **Total** | **~$6-21/month** |

**Tips to reduce costs:**
- Use `min-instances=0` (accept cold starts)
- Use Gemini Flash instead of Pro
- Enable response caching
- Set reasonable `max-instances`

---

## Full Documentation

- **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) (comprehensive)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API Documentation**: [docs/API.md](docs/API.md)

---

## Support

- 🐛 **Issues**: [Open an issue](../../issues)
- 📚 **Docs**: See `docs/` folder
- 💬 **Questions**: Check [Google Cloud Run docs](https://cloud.google.com/run/docs)

---

**Made it this far?** 🎉 Your Virtual Debate Panel is now running in the cloud!
