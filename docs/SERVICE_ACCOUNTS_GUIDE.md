# Service Accounts Guide - Virtual Debate Panel

## What are Service Accounts?

Service accounts are special Google accounts that represent applications (not humans). They allow your application to authenticate with Google Cloud services.

### Why You Need Them

For the Agora deployment, service accounts are used for:

1. **Cloud Build Service Account** - Builds Docker images and deploys to Cloud Run
2. **Cloud Run Service Account** - Runs your application and accesses secrets/APIs

## Quick Fix: Enable Service Accounts

### Option 1: Run the Enable Script (Easiest)

```bash
# Navigate to project directory
cd Agora

# Run the service account enablement script
chmod +x scripts/enable_service_accounts.sh
./scripts/enable_service_accounts.sh
```

This script will:
- ✅ Enable the Service Account API
- ✅ Enable the IAM API
- ✅ Verify that service accounts exist or will be created
- ✅ Optionally create a custom service account for better security

### Option 2: Manual Setup via gcloud

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable Service Account API
gcloud services enable iam.googleapis.com

# 3. Enable Service Usage API
gcloud services enable serviceusage.googleapis.com

# 4. Wait 30 seconds for APIs to propagate
sleep 30

# 5. Verify service accounts
gcloud iam service-accounts list
```

### Option 3: Enable via Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Navigate to **IAM & Admin → Service Accounts**
4. The page will prompt you to enable the API if needed
5. Click **"Enable API"**

---

## Understanding Service Accounts in Agora

### 1. Cloud Build Service Account

**Email**: `PROJECT_NUMBER@cloudbuild.gserviceaccount.com`

**Purpose**: Executes your CI/CD pipeline

**Permissions Needed**:
- `roles/run.admin` - Deploy to Cloud Run
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/secretmanager.secretAccessor` - Read secrets
- `roles/artifactregistry.writer` - Push Docker images

**Created When**: First time you use Cloud Build

### 2. Cloud Run Service Account (Default)

**Email**: `PROJECT_NUMBER-compute@developer.gserviceaccount.com`

**Purpose**: Runs your application container

**Permissions Needed**:
- `roles/secretmanager.secretAccessor` - Read API keys from Secret Manager

**Created When**: Automatically when you enable Compute Engine or Cloud Run

### 3. Custom Service Account (Optional, Recommended)

**Email**: `agora-cloudrun-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com`

**Purpose**: Dedicated service account for Cloud Run (better security)

**Permissions Needed**:
- `roles/secretmanager.secretAccessor` - Read secrets

**Created When**: You run the enable script and choose "yes"

---

## Common Errors and Solutions

### Error: "Service account does not exist"

**Problem**: Service Account API not enabled

**Solution**:
```bash
# Enable the API
gcloud services enable iam.googleapis.com

# Wait 30 seconds
sleep 30

# Verify
gcloud iam service-accounts list
```

### Error: "Permission denied" when deploying

**Problem**: Service account doesn't have necessary permissions

**Solution**:
```bash
# Get project details
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Cloud Build permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

### Error: "Secret Manager permission denied at runtime"

**Problem**: Cloud Run service account can't access secrets

**Solution**:
```bash
# Grant permission to default Compute Engine SA
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Error: "APIs not enabled"

**Problem**: Required APIs aren't enabled

**Solution**:
```bash
# Enable all required APIs at once
gcloud services enable \
  iam.googleapis.com \
  serviceusage.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com
```

---

## Verifying Service Accounts

### Check if Service Accounts Exist

```bash
# List all service accounts in your project
gcloud iam service-accounts list

# Check specific service account
gcloud iam service-accounts describe \
  SERVICE_ACCOUNT_EMAIL@PROJECT_ID.iam.gserviceaccount.com
```

### Check Service Account Permissions

```bash
# Get IAM policy for project
gcloud projects get-iam-policy YOUR_PROJECT_ID

# Filter for specific service account
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR_SA_EMAIL"
```

### Test Service Account Access

```bash
# Test if service account can access a secret
gcloud secrets versions access latest \
  --secret="GEMINI_API_KEY" \
  --impersonate-service-account="YOUR_SA_EMAIL@PROJECT_ID.iam.gserviceaccount.com"
```

---

## Best Practices

### Security

1. **Use Custom Service Accounts** (Not Default)
   - Create dedicated service accounts for each service
   - Easier to audit and manage permissions

2. **Principle of Least Privilege**
   - Only grant permissions that are actually needed
   - Avoid using `roles/owner` or `roles/editor`

3. **Separate Build and Runtime**
   - Cloud Build SA: Can deploy but shouldn't run services
   - Cloud Run SA: Can run services but shouldn't deploy

### Example: Creating a Custom Service Account

```bash
# Create service account
gcloud iam service-accounts create agora-cloudrun-sa \
  --display-name="Agora Cloud Run Service Account" \
  --description="Runs the Agora Virtual Debate Panel backend"

# Grant only Secret Manager access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:agora-cloudrun-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Use in Cloud Run deployment
gcloud run deploy agora-backend \
  --image=... \
  --service-account=agora-cloudrun-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### Updating cloudbuild.yaml for Custom Service Account

```yaml
# cloudbuild.yaml
steps:
  # ... build steps ...

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'agora-backend'
      - '--service-account=agora-cloudrun-sa@${PROJECT_ID}.iam.gserviceaccount.com'  # Add this line
      # ... other args ...
```

---

## Troubleshooting Workflow

```
┌─────────────────────────────────────┐
│ Service Account Error?              │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 1. Enable Service Account API      │
│    gcloud services enable iam       │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 2. Wait 30 seconds for propagation │
│    sleep 30                          │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 3. Verify service accounts exist   │
│    gcloud iam service-accounts list │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 4. Grant required permissions      │
│    (See IAM setup commands above)   │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 5. Retry deployment                │
└─────────────────────────────────────┘
```

---

## Complete Setup Script

For a complete automated setup including service accounts, use:

```bash
# 1. Enable service accounts
./scripts/enable_service_accounts.sh

# 2. Set up infrastructure
./scripts/setup_gcloud_infrastructure.sh

# 3. Create Cloud Build trigger (manual in Console)

# 4. Deploy
git push origin main
```

---

## Getting Help

### View Current Service Accounts

```bash
# Simple list
gcloud iam service-accounts list

# Detailed view with permissions
gcloud projects get-iam-policy $(gcloud config get-value project) \
  --flatten="bindings[].members" \
  --filter="bindings.members~^serviceAccount:" \
  --format="table(bindings.role, bindings.members)"
```

### Check API Status

```bash
# List enabled APIs
gcloud services list --enabled

# Check specific API
gcloud services list --enabled --filter="name:iam.googleapis.com"
```

### Documentation Links

- [Service Accounts Overview](https://cloud.google.com/iam/docs/service-accounts)
- [Cloud Build Service Account](https://cloud.google.com/build/docs/cloud-build-service-account)
- [Cloud Run Service Identity](https://cloud.google.com/run/docs/securing/service-identity)
- [IAM Roles Reference](https://cloud.google.com/iam/docs/understanding-roles)

---

## Summary

**Quick Fix**: Run this single command:

```bash
./scripts/enable_service_accounts.sh
```

This will enable the Service Account API and verify everything is configured correctly. Then proceed with the main infrastructure setup.

**Still Having Issues?**

Open an issue on GitHub with:
1. Error message (full text)
2. Output of `gcloud iam service-accounts list`
3. Output of `gcloud services list --enabled | grep iam`
