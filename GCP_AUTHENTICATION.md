# Google Cloud Authentication Guide

## Why Service Accounts?

You're right to question this! Since you already have a Google Cloud project with credits, you have **two options** for authentication:

## Option 1: Use Your User Credentials (Easier for Local Development) ✅

**For local development**, you can use your own Google Cloud user credentials instead of creating a service account:

### Setup Steps:

1. **Authenticate with your Google Cloud account**:
   ```bash
   gcloud auth application-default login
   ```
   
   This will:
   - Open a browser window
   - Ask you to sign in with your Google account
   - Store credentials locally for your application to use

2. **Set your project**:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **That's it!** Your application will automatically use these credentials.

### Update your .env file:

You can **remove or leave empty** the `GOOGLE_APPLICATION_CREDENTIALS` line:

```env
GCP_PROJECT_ID=your-actual-project-id
# GOOGLE_APPLICATION_CREDENTIALS=  # Not needed when using gcloud auth
```

## Option 2: Service Account (Required for Cloud Run Deployment)

**Service accounts are only required if:**
- You're deploying to Cloud Run (production)
- You want to use a specific service account with limited permissions
- You're running in an environment where user credentials aren't available

### When to Use Service Accounts:

- ✅ **Cloud Run deployment**: Cloud Run automatically uses a service account
- ✅ **Production environments**: Better security and access control
- ✅ **CI/CD pipelines**: Automated deployments

### For Local Development:

- ❌ **Not required** if you use `gcloud auth application-default login`
- ✅ **Optional** if you prefer explicit service account authentication

## What the Code Does

The application uses **Application Default Credentials (ADC)**, which means it will:

1. **First check**: `GOOGLE_APPLICATION_CREDENTIALS` environment variable (service account key file)
2. **If not found**: Use your user credentials from `gcloud auth application-default login`
3. **In Cloud Run**: Automatically use the service account attached to the Cloud Run service

## Quick Setup for Your Case

Since you have a GCP project with credits, here's the simplest setup:

```bash
# 1. Authenticate with your account
gcloud auth application-default login

# 2. Set your project
gcloud config set project YOUR_PROJECT_ID

# 3. Enable required APIs
gcloud services enable \
  spanner.googleapis.com \
  secretmanager.googleapis.com \
  drive.googleapis.com

# 4. Update .env file (no service account key needed!)
# Just set:
GCP_PROJECT_ID=your-actual-project-id
SPANNER_PROJECT_ID=your-actual-project-id
```

## Required Permissions

Make sure your Google account has these roles in your project:
- **Spanner Database User** (for Spanner access)
- **Secret Manager Secret Accessor** (if using Secret Manager)
- **Editor** or **Owner** (for general GCP operations)

You can check your permissions:
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:user:YOUR_EMAIL"
```

## Summary

| Scenario | Authentication Method |
|----------|----------------------|
| **Local Development** | `gcloud auth application-default login` (your user account) |
| **Cloud Run Deployment** | Service account (automatically attached) |
| **CI/CD** | Service account key file |

**For your case (local development with existing GCP project):**
- ✅ Use `gcloud auth application-default login`
- ❌ Don't need to create a service account
- ✅ Just set `GCP_PROJECT_ID` in your `.env` file

## Next Steps

1. Run: `gcloud auth application-default login`
2. Set your project: `gcloud config set project YOUR_PROJECT_ID`
3. Enable APIs: `gcloud services enable spanner.googleapis.com`
4. Update `.env` with your `GCP_PROJECT_ID`
5. Start developing! 🚀

