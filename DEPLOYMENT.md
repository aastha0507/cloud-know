# CloudKnow - Cloud Run Deployment Guide

## Prerequisites

1. Google Cloud Project: `cloudknow-478811`
2. Region: `europe-west1`
3. Required APIs enabled:
   - Cloud Run API
   - Cloud Build API
   - Secret Manager API
   - Spanner API

## Pre-Deployment Setup

### 1. Create Secrets in Secret Manager

```bash
# MongoDB Atlas URI
echo -n "mongodb+srv://user:password@cluster.mongodb.net/" | \
  gcloud secrets create mongodb-uri --data-file=- --project=cloudknow-478811

# Gemini API Key
echo -n "your-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=- --project=cloudknow-478811

# Spanner Configuration
echo -n "cloudknow-478811" | \
  gcloud secrets create spanner-project-id --data-file=- --project=cloudknow-478811

echo -n "cloudknow-instance" | \
  gcloud secrets create spanner-instance-id --data-file=- --project=cloudknow-478811

echo -n "cloudknow-db" | \
  gcloud secrets create spanner-database-id --data-file=- --project=cloudknow-478811
```

### 2. Create Service Account

```bash
gcloud iam service-accounts create cloudknow-sa \
  --display-name="CloudKnow Service Account" \
  --project=cloudknow-478811

# Grant necessary permissions
gcloud projects add-iam-policy-binding cloudknow-478811 \
  --member="serviceAccount:cloudknow-sa@cloudknow-478811.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding cloudknow-478811 \
  --member="serviceAccount:cloudknow-sa@cloudknow-478811.iam.gserviceaccount.com" \
  --role="roles/spanner.databaseUser"
```

### 3. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  spanner.googleapis.com \
  --project=cloudknow-478811
```

## Deployment

### Option 1: Using Cloud Build (Recommended)

```bash
gcloud builds submit --config cloudbuild.yaml --project=cloudknow-478811
```

### Option 2: Manual Deployment

```bash
# Build image
gcloud builds submit --tag gcr.io/cloudknow-478811/cloudknow

# Deploy to Cloud Run
gcloud run deploy cloudknow \
  --image gcr.io/cloudknow-478811/cloudknow \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-secrets MONGODB_ATLAS_URI=mongodb-uri:latest,GEMINI_API_KEY=gemini-api-key:latest \
  --service-account cloudknow-sa@cloudknow-478811.iam.gserviceaccount.com \
  --project=cloudknow-478811
```

## Post-Deployment

1. Get the service URL:
```bash
gcloud run services describe cloudknow --region europe-west1 --format="value(status.url)"
```

2. Test the health endpoint:
```bash
curl https://your-service-url/health
```

## Environment Variables

All sensitive values are stored in Secret Manager and injected at runtime.

## Monitoring

- View logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
- Monitor in Cloud Console: https://console.cloud.google.com/run

## Troubleshooting

- Check logs: `gcloud run services logs read cloudknow --region europe-west1`
- Verify secrets: `gcloud secrets versions access latest --secret=mongodb-uri`

