# Google ADK Setup for CloudKnow

This guide will help you set up Google ADK (Agent Development Kit) for CloudKnow with an interactive chat UI.

## Prerequisites

1. **Get a Google AI Studio API Key**:
   - Go to https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Copy your API key

2. **Install ADK**:
   ```bash
   pip install google-adk
   ```

## Setup Steps

### Step 1: Configure Environment

1. Open `cloudknow_agent/.env` file
2. Replace `PASTE_YOUR_ACTUAL_API_KEY_HERE` with your actual API key from Google AI Studio
3. Make sure `GOOGLE_GENAI_USE_VERTEXAI=FALSE` (for Google AI Studio)

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-actual-api-key-here
```

### Step 2: Install Dependencies

```bash
# Install ADK and other dependencies
pip install -r requirements.txt
```

### Step 3: Launch the Interactive UI

```bash
# Navigate to project root
cd /Users/diksharanjan/cloudknow

# Launch ADK web UI
adk web
```

**Note**: If you encounter `_make_subprocess_transport NotImplementedError`, use:
```bash
adk web --no-reload
```

### Step 4: Access the UI

1. Open the URL provided (usually `http://localhost:8000` or `http://127.0.0.1:8000`)
2. In the top-left corner dropdown, select **"cloudknow_agent"**
3. Start chatting!

## Using Vertex AI (Alternative)

If you prefer to use Vertex AI instead of Google AI Studio:

1. **Update `.env`**:
   ```env
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   GCP_PROJECT_ID=cloudknow
   GCP_LOCATION=europe-west1
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth application-default login
   gcloud config set project cloudknow-478811
   ```

3. **Enable Vertex AI API**:
   ```bash
   gcloud services enable aiplatform.googleapis.com --project=cloudknow-478811
   ```

## Available Tools

The CloudKnow agent has three main tools:

### 1. `query_documents`
Query the knowledge base to find relevant documents.

**Parameters**:
- `query` (str): Your search query
- `limit` (int): Max results (default: 10)
- `source_filter` (str, optional): Filter by source ("google_drive", "jira", etc.)
- `min_score` (float): Minimum similarity (0.0-1.0, default: 0.7)

**Example**:
```
Query: "What are the data privacy rules?"
Limit: 5
Min Score: 0.7
```

### 2. `ingest_google_drive_folder`
Ingest documents from a Google Drive folder.

**Parameters**:
- `folder_id` (str): Google Drive folder ID
- `limit` (int, optional): Max files to process

**Example**:
```
Folder ID: 1nNsuC0z8IsssvbM2lAS4hCMMvJzaHF1DxFW
Limit: 10
```

### 3. `query_folder_with_context`
Query a specific folder and get contextual answers with file descriptions.

**Parameters**:
- `folder_id` (str): Google Drive folder ID
- `query` (str): Your question
- `limit` (int, optional): Max files to process
- `min_score` (float): Minimum similarity (default: 0.7)

**Example**:
```
Folder ID: 1nNsuC0z8IvbM2lAS4ssshCMMvJzaHF1DxFW
Query: "What are the compliance requirements?"
Min Score: 0.7
```

## Example Conversations

### Example 1: Query Documents
```
You: "What are the data privacy rules in my documents?"
Agent: [Uses query_documents tool]
Agent: "I found 3 documents related to data privacy rules..."
```

### Example 2: Ingest Folder
```
You: "Ingest files from folder 1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW"
Agent: [Uses ingest_google_drive_folder tool]
Agent: "Successfully processed 5 files from Google Drive."
```

### Example 3: Query with Context
```
You: "What files in folder 1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW contain information about compliance?"
Agent: [Uses query_folder_with_context tool]
Agent: "I found 2 files with relevant content:
- Compliance_Rules.pdf (relevance: 0.85)
- Security_Guidelines.docx (relevance: 0.78)"
```

## Troubleshooting

### Error: "API key not found"
- Make sure you've set `GOOGLE_API_KEY` in `cloudknow_agent/.env`
- Check that the API key is correct

### Error: "Module not found"
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the project root directory

### Error: "_make_subprocess_transport NotImplementedError"
- Use `adk web --no-reload` instead of `adk web`

### Error: "No documents found"
- Make sure you've ingested documents first using `ingest_google_drive_folder`
- Try lowering the `min_score` parameter

### Error: "Google Drive authentication failed"
- Run: `gcloud auth application-default login`
- Make sure you have access to the Google Drive folder

## Project Structure

```
cloudknow/
├── cloudknow_agent/
│   ├── agent.py          # ADK agent definition
│   └── .env              # ADK configuration
├── rag/                  # RAG services
├── agents/               # Agent workflows
├── mcp/                  # MCP tools
└── requirements.txt      # Dependencies
```

## Next Steps

1. ✅ Get API key from Google AI Studio
2. ✅ Update `.env` file with your API key
3. ✅ Install dependencies
4. ✅ Launch `adk web`
5. ✅ Start chatting with CloudKnow!

## Additional Resources

- [Google ADK Documentation](https://cloud.google.com/adk/docs)
- [Google AI Studio](https://aistudio.google.com/)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)


