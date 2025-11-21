# CloudKnow Setup Guide

This guide will walk you through setting up CloudKnow step by step.

## Step 1: Prerequisites

### 1.1 Google Cloud Project Setup

1. Create a new Google Cloud Project or select an existing one

2. **Authenticate with your Google Cloud account** (for local development):
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
   
   > **Note**: This uses your user credentials. No service account needed for local development!
   > See `GCP_AUTHENTICATION.md` for details.

3. Enable the following APIs:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     spanner.googleapis.com \
     secretmanager.googleapis.com \
     drive.googleapis.com \
     cloudbuild.googleapis.com
   ```

4. **Optional - Service Account** (only needed for Cloud Run deployment):
   
   If deploying to Cloud Run, you can create a service account:
   ```bash
   gcloud iam service-accounts create cloudknow-sa \
     --display-name="CloudKnow Service Account"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:cloudknow-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/spanner.databaseUser"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:cloudknow-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```
   
   > **For local development**: Skip this step and use `gcloud auth application-default login` instead.

### 1.2 MongoDB Atlas Setup

1. Create a MongoDB Atlas account at https://www.mongodb.com/cloud/atlas
2. Create a new cluster (free tier is fine for development)
3. Create a database user:
   - Go to Database Access → Add New Database User
   - Choose Password authentication
   - Save the username and password
4. Whitelist your IP address:
   - Go to Network Access → Add IP Address
   - Add `0.0.0.0/0` for development (restrict in production)
5. Get your connection string:
   - Go to Clusters → Connect → Connect your application
   - Copy the connection string (replace `<password>` with your password)
6. Enable Vector Search:
   - Go to your cluster → Search → Create Search Index
   - Use the JSON editor and paste:
     ```json
     {
       "mappings": {
         "dynamic": true,
         "fields": {
           "embedding": {
             "type": "knnVector",
             "dimensions": 768,
             "similarity": "cosine"
           }
         }
       }
     }
     ```
   - Name it `vector_index`

### 1.3 Spanner Setup

1. Create a Spanner instance:
   ```bash
   gcloud spanner instances create cloudknow-instance \
     --config=regional-us-central1 \
     --description="CloudKnow metadata database" \
     --processing-units=100
   ```
   
   > **Note**: For development, `--processing-units=100` is cost-effective. 
   > For production, you can use `--nodes=1` or higher processing units.

2. Create a database:
   ```bash
   gcloud spanner databases create cloudknow-db \
     --instance=cloudknow-instance
   ```

   Note: The schema will be created automatically when you first run the application.

### 1.4 Gemini API Setup

1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Save the key securely

## Step 2: Local Development Setup

### 2.1 Clone and Install

```bash
# Navigate to project directory
cd cloudknow

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2.2 Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```env
   # GCP Configuration
   GCP_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=./cloudknow-key.json
   
   # MongoDB Atlas
   MONGODB_ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net/
   MONGODB_DATABASE_NAME=cloudknow
   MONGODB_COLLECTION_NAME=documents
   
   # Spanner
   SPANNER_PROJECT_ID=your-project-id
   SPANNER_INSTANCE_ID=cloudknow-instance
   SPANNER_DATABASE_ID=cloudknow-db
   
   # Gemini
   GEMINI_API_KEY=your-gemini-api-key
   
   # Google Drive (optional for now)
   GOOGLE_DRIVE_FOLDER_ID=
   
   # Jira (optional)
   JIRA_SERVER=
   JIRA_EMAIL=
   JIRA_API_TOKEN=
   
   # Slack (optional)
   SLACK_BOT_TOKEN=
   SLACK_APP_TOKEN=
   ```

### 2.3 Set Up Google Drive Access (Optional)

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (for user authentication) or use Service Account
3. For Service Account:
   - Create a service account
   - Enable Google Drive API
   - Share your Drive folders with the service account email

### 2.4 Run the Application

```bash
# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

Visit http://localhost:8080/docs to see the API documentation.

## Step 3: Testing the Setup

### 3.1 Health Check

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status":"ok","app":"CloudKnow"}
```

### 3.2 Process a Test Document

```bash
curl -X POST http://localhost:8080/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "source_id": "test-001",
    "content": "This is a test document about artificial intelligence and machine learning.",
    "file_name": "test.txt"
  }'
```

### 3.3 Query the Knowledge Base

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?",
    "limit": 5
  }'
```

## Step 4: Deployment to Cloud Run

### 4.1 Build and Deploy

Option 1: Using Cloud Build (recommended)
```bash
gcloud builds submit --config cloudbuild.yaml
```

Option 2: Manual deployment
```bash
# Build the image
docker build -t gcr.io/YOUR_PROJECT_ID/cloudknow .

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/cloudknow

# Deploy to Cloud Run
gcloud run deploy cloudknow \
  --image gcr.io/YOUR_PROJECT_ID/cloudknow \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars GCP_PROJECT_ID=YOUR_PROJECT_ID
```

### 4.2 Set Secrets in Secret Manager

For production, store sensitive values in Secret Manager:

```bash
# Store MongoDB URI
echo -n "mongodb+srv://..." | gcloud secrets create mongodb-uri --data-file=-

# Store Gemini API key
echo -n "your-api-key" | gcloud secrets create gemini-api-key --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding mongodb-uri \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Then update your code to read from Secret Manager (already implemented in `api/services/secret_manager_service.py`).

## Step 5: Integration Setup

### 5.1 Google Drive Integration

1. Enable Google Drive API in your GCP project
2. Create OAuth credentials or use Service Account
3. Share folders with the service account email
4. Test ingestion:
   ```bash
   curl -X POST http://localhost:8080/ingestion/google-drive \
     -H "Content-Type: application/json" \
     -d '{
       "folder_id": "your-folder-id",
       "limit": 10
     }'
   ```

### 5.2 Jira Integration

1. Generate a Jira API token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create API token
2. Update `.env`:
   ```env
   JIRA_SERVER=https://your-domain.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-api-token
   ```

### 5.3 Slack Integration

1. Create a Slack app:
   - Go to https://api.slack.com/apps
   - Create New App → From scratch
   - Add OAuth scopes: `channels:read`, `groups:read`, `im:read`, `mpim:read`
2. Install the app to your workspace
3. Copy the Bot User OAuth Token
4. Update `.env`:
   ```env
   SLACK_BOT_TOKEN=xoxb-your-token
   ```

## Troubleshooting

### Common Issues

1. **Spanner schema creation fails**:
   - Ensure the service account has `spanner.databaseUser` role
   - Check that the instance and database exist

2. **MongoDB connection fails**:
   - Verify the connection string format
   - Check IP whitelist settings
   - Ensure database user has read/write permissions

3. **Embedding generation fails**:
   - Verify Gemini API key is correct
   - Check API quota limits

4. **Google Drive access denied**:
   - Ensure folders are shared with service account
   - Check OAuth scopes

## Next Steps

- Set up monitoring with Cloud Logging
- Configure alerts for errors
- Set up CI/CD pipeline
- Add authentication/authorization
- Implement caching for better performance
- Add batch processing capabilities

