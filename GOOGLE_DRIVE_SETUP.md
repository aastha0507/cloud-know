# Google Drive Integration Setup

This guide will help you connect CloudKnow to Google Drive.

## Step 1: Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `cloudknow-478811`
3. Navigate to **APIs & Services** → **Library**
4. Search for "Google Drive API"
5. Click **Enable**

Or use the command line:
```bash
gcloud services enable drive.googleapis.com --project=cloudknow-478811
```

## Step 2: Choose Authentication Method

You have two options:

### Option A: Use Your User Credentials (Easier for Local Development)

This uses your personal Google account credentials:

```bash
# Authenticate with your Google account (includes required cloud-platform scope)
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.readonly
```

**Pros:**
- Quick setup
- No service account needed
- Works immediately

**Cons:**
- Uses your personal account
- Not suitable for production
- Requires re-authentication periodically

### Option B: Use Service Account (Recommended for Production)

1. **Create a Service Account:**
   ```bash
   gcloud iam service-accounts create cloudknow-drive-sa \
     --display-name="CloudKnow Drive Service Account" \
     --project=cloudknow-478811
   ```

2. **Grant Drive API access:**
   ```bash
   gcloud projects add-iam-policy-binding cloudknow-478811 \
     --member="serviceAccount:cloudknow-drive-sa@cloudknow-478811.iam.gserviceaccount.com" \
     --role="roles/serviceusage.serviceUsageConsumer"
   ```

3. **Create and download key:**
   ```bash
   gcloud iam service-accounts keys create cloudknow-drive-key.json \
     --iam-account=cloudknow-drive-sa@cloudknow-478811.iam.gserviceaccount.com
   ```

4. **Share Google Drive folders with the service account:**
   - Get the service account email: `cloudknow-drive-sa@cloudknow-478811.iam.gserviceaccount.com`
   - In Google Drive, right-click the folder you want to access
   - Click "Share"
   - Add the service account email
   - Give it "Viewer" or "Editor" access

## Step 3: Get a Folder ID

1. Open Google Drive in your browser
2. Navigate to the folder you want to ingest
3. Open the folder
4. Look at the URL - it will look like:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```
5. Copy the `FOLDER_ID_HERE` part

## Step 4: Update .env File

Add to your `.env` file:

**For Option A (User Credentials):**
```env
# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
# No credentials file needed - uses gcloud auth
```

**For Option B (Service Account):**
```env
# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
GOOGLE_APPLICATION_CREDENTIALS=./cloudknow-drive-key.json
```

## Step 5: Test the Connection

Run the test script:

```bash
python3 test_google_drive.py
```

Or test via API:

```bash
curl -X POST http://localhost:8080/ingestion/google-drive \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "your-folder-id",
    "limit": 5
  }'
```

## Troubleshooting

### Error: "Insufficient Permission"
- Make sure the Google Drive API is enabled
- Check that you've shared the folder with the service account (if using Option B)
- Verify authentication: `gcloud auth list`

### Error: "File not found"
- Verify the folder ID is correct
- Make sure the folder is shared with your account/service account
- Check that the folder exists and is accessible

### Error: "Access denied"
- For service accounts: Make sure you've shared the folder with the service account email
- For user credentials: Make sure you've granted the correct scopes

## Next Steps

Once Google Drive is connected:
1. Test with a small folder first
2. Monitor the ingestion process
3. Check MongoDB and Spanner for stored documents
4. Test querying the ingested documents

