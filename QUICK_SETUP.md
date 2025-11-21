# Quick MongoDB Atlas Setup

## Your Configuration Values

**MongoDB Atlas URI:**
```
mongodb+srv://username_db_user:<db_password>@cluster0.4mua0ib.mongodb.net/?appName=Cluster0
```

**Database:** `cloudknow`  
**Collection:** `documents`

## Quick Setup (Replace YOUR_PASSWORD)

```bash
# Set MongoDB Atlas environment variables
export MONGODB_ATLAS_URI="mongodb+srv://username_db_user:YOUR_PASSWORD@cluster0.4mua0ib.mongodb.net/?appName=Cluster0"
export MONGODB_DATABASE_NAME="cloudknow"
export MONGODB_COLLECTION_NAME="documents"
```

## Create .env File Manually

Since `.env` files are protected, create it manually:

```bash
cat > .env << 'EOF'
# MongoDB Atlas Configuration
MONGODB_ATLAS_URI=mongodb+srv://username_db_user:YOUR_PASSWORD@cluster0.4mua0ib.mongodb.net/?appName=Cluster0
MONGODB_DATABASE_NAME=cloudknow
MONGODB_COLLECTION_NAME=documents

# Add other required variables (see .env.example format)
GCP_PROJECT_ID=your-project-id
SPANNER_PROJECT_ID=your-project-id
GEMINI_API_KEY=your-gemini-api-key
EOF
```

Then edit `.env` and replace `YOUR_PASSWORD` with your actual password.

