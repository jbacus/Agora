# Google Secret Manager Integration

This guide explains how to use Google Cloud Secret Manager to securely store and manage API keys for the Agora application.

## 🔒 Why Secret Manager?

**Security Benefits:**
- ✅ Never commit API keys to git
- ✅ Centralized secret management
- ✅ Automatic secret rotation support
- ✅ IAM-based access control
- ✅ Audit logging of secret access
- ✅ Encrypted at rest and in transit

**Development Workflow:**
- **Production**: Secrets fetched from Secret Manager automatically
- **Local Development**: Falls back to `.env` file seamlessly

---

## 🚀 Quick Start

### 1. Enable Secret Manager

```bash
# Enable the Secret Manager API
gcloud services enable secretmanager.googleapis.com
```

### 2. Create Secrets (Automated)

Use our setup script:

```bash
./scripts/setup_secrets.sh
```

This will:
- Enable Secret Manager API
- Create secrets for all API keys
- Prompt you to enter secret values
- Grant Cloud Run access to secrets

### 3. Deploy Application

Secrets are automatically fetched when deployed to Cloud Run:

```bash
git push origin main  # Triggers automated deployment
```

---

## 📝 Manual Setup

### Create a Secret

```bash
# Create the secret
gcloud secrets create GEMINI_API_KEY \
  --replication-policy="automatic" \
  --labels=app=agora

# Add the secret value
echo -n "your-api-key-here" | gcloud secrets versions add GEMINI_API_KEY \
  --data-file=-
```

### Grant Access to Cloud Run

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID \
  --format="value(projectNumber)")

# Cloud Run service account
CLOUD_RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:$CLOUD_RUN_SA" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 🔑 Supported Secrets

The application looks for these secrets in Secret Manager:

| Secret Name | Description | Get From |
|------------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | [AI Studio](https://aistudio.google.com/app/apikey) |
| `OPENAI_API_KEY` | OpenAI API key | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | Anthropic API key | [Anthropic Console](https://console.anthropic.com/settings/keys) |
| `PINECONE_API_KEY` | Pinecone API key | [Pinecone Console](https://app.pinecone.io/organizations) |

---

## 🎯 How It Works

### Priority Order

The application fetches secrets in this order:

1. **Google Secret Manager** (if `GCP_PROJECT_ID` is set)
2. **Environment Variables** (if Secret Manager fails or is disabled)
3. **.env File** (for local development)

### Configuration

Control Secret Manager behavior with environment variables:

```bash
# Enable/disable Secret Manager (default: true)
USE_SECRET_MANAGER=true

# Set GCP project ID (auto-detected in Cloud Run)
GCP_PROJECT_ID=your-project-id

# Or use this variable (Cloud Run sets this automatically)
GOOGLE_CLOUD_PROJECT=your-project-id
```

### Code Example

```python
from config.settings import settings

# Settings automatically fetches from Secret Manager or env vars
llm_config = settings.get_llm_config()
api_key = llm_config["api_key"]  # Fetched from Secret Manager if available
```

### Direct Access

You can also use the secrets module directly:

```python
from src.utils.secrets import get_secret, set_secret

# Get a secret
api_key = get_secret("GEMINI_API_KEY", project_id="my-project")

# Create or update a secret
set_secret("MY_SECRET", "secret-value", project_id="my-project")
```

---

## 🧪 Local Development

### Option 1: Use .env File (Recommended)

Secret Manager is **optional** for local development:

```bash
# .env file
GEMINI_API_KEY=your-api-key-here
USE_SECRET_MANAGER=false  # Disable Secret Manager locally
```

### Option 2: Use Secret Manager Locally

To test Secret Manager integration locally:

```bash
# 1. Set project ID
export GCP_PROJECT_ID=your-project-id

# 2. Authenticate with gcloud
gcloud auth application-default login

# 3. Run application
python -m uvicorn src.api.main:app --reload
```

The application will fetch secrets from Secret Manager using your local credentials.

---

## 🔐 Production Deployment

### Cloud Run Setup

Secrets are automatically available in Cloud Run via the service account:

```yaml
# cloudbuild.yaml (already configured)
steps:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'agora-backend'
      - '--set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest'
```

### Environment Variables

Set these in Cloud Run:

```bash
gcloud run services update agora-backend \
  --region=us-central1 \
  --set-env-vars="USE_SECRET_MANAGER=true" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

---

## 🛠️ Management Commands

### List All Secrets

```bash
gcloud secrets list
```

### View Secret Metadata

```bash
gcloud secrets describe GEMINI_API_KEY
```

### Access Secret Value

```bash
# Latest version
gcloud secrets versions access latest --secret=GEMINI_API_KEY

# Specific version
gcloud secrets versions access 1 --secret=GEMINI_API_KEY
```

### Update Secret

```bash
# Add new version (old versions are kept)
echo -n "new-api-key-value" | gcloud secrets versions add GEMINI_API_KEY \
  --data-file=-
```

### Delete Secret

```bash
# Delete a specific version
gcloud secrets versions destroy 1 --secret=GEMINI_API_KEY

# Delete entire secret
gcloud secrets delete GEMINI_API_KEY
```

### List Secret Versions

```bash
gcloud secrets versions list GEMINI_API_KEY
```

---

## 🔄 Secret Rotation

### Automatic Rotation

To rotate a secret:

1. Create new API key from provider
2. Add new version to Secret Manager:
   ```bash
   echo -n "new-key" | gcloud secrets versions add GEMINI_API_KEY --data-file=-
   ```
3. Cloud Run automatically uses the latest version
4. Disable old API key after verification

### Gradual Rollout

```bash
# Pin to specific version temporarily
gcloud run services update agora-backend \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:1"

# After testing, switch to latest
gcloud run services update agora-backend \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

---

## 🐛 Troubleshooting

### Secret Not Found

**Error**: `Secret 'GEMINI_API_KEY' not found`

**Solution**:
```bash
# Create the secret
./scripts/setup_secrets.sh

# Or manually
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
echo -n "your-key" | gcloud secrets versions add GEMINI_API_KEY --data-file=-
```

### Permission Denied

**Error**: `Permission denied accessing secret`

**Solution**:
```bash
# Grant access to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Local Development Not Working

**Error**: `Failed to fetch secret from Secret Manager`

**Solution**:
```bash
# Option 1: Disable Secret Manager for local dev
echo "USE_SECRET_MANAGER=false" >> .env

# Option 2: Authenticate locally
gcloud auth application-default login
export GCP_PROJECT_ID=your-project-id
```

### Cloud Run Not Picking Up Secrets

**Solution**:
```bash
# Verify secrets are mounted
gcloud run services describe agora-backend \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env)'

# Update if missing
gcloud run services update agora-backend \
  --region=us-central1 \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

---

## 💰 Costs

**Secret Manager Pricing** (as of 2024):

- **Secret Versions**: $0.06 per active secret version per month
- **Access Operations**: First 10,000/month free, then $0.03 per 10,000
- **Rotation**: Free (just version storage costs)

**Example Monthly Cost**:
- 4 secrets × 2 versions each = 8 versions
- 8 × $0.06 = **$0.48/month**
- Plus ~1,000 access operations/month = **Free**

**Total: ~$0.50/month** for production secret management

---

## 📚 Best Practices

1. **Never commit secrets to git**
   - Use `.env` for local development
   - Add `.env` to `.gitignore`

2. **Use different secrets per environment**
   ```
   GEMINI_API_KEY_DEV
   GEMINI_API_KEY_STAGING
   GEMINI_API_KEY_PROD
   ```

3. **Rotate secrets regularly**
   - Set calendar reminders for rotation
   - Keep 2 versions during rotation
   - Delete old versions after validation

4. **Use labels for organization**
   ```bash
   gcloud secrets create MY_SECRET \
     --labels=app=agora,environment=prod,team=backend
   ```

5. **Enable audit logging**
   ```bash
   gcloud logging read 'resource.type="secretmanager.googleapis.com/Secret"'
   ```

6. **Principle of least privilege**
   - Only grant `secretmanager.secretAccessor` role
   - Grant to specific service accounts, not all users

---

## 🔗 Additional Resources

- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [IAM Roles for Secret Manager](https://cloud.google.com/secret-manager/docs/access-control)
- [Secret Manager Pricing](https://cloud.google.com/secret-manager/pricing)
- [Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)

---

**Questions?** Check [Troubleshooting](#-troubleshooting) or open an issue on GitHub.
