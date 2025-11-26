# CloudKnow - AI Knowledge Hub

CloudKnow is an agentic architecture designed to transform fragmented enterprise data into actionable intelligence. It acts as a reasoning engine, connecting and understanding relationships between documents and conversations across platforms like Google Drive, Jira, and Slack, providing employees with instant access to synthesized and cited information.

## Architecture

CloudKnow's architecture consists of three main layers:

### (A) Application Layer
- **FastAPI** application running on **Google Cloud Run**
- RESTful API for user interaction
- Document handling and agent orchestration
- API endpoints for querying, ingestion, and document management

### (B) ADK Agent Orchestration Layer
Specialized agents for:
- **File Extraction Agent**: Extracts content from various file types (PDF, DOCX, XLSX, text, etc.)
- **Chunking Agent**: Splits documents into manageable chunks for embedding
- **Embedding Agent**: Generates vector embeddings using Gemini API
- **Metadata Analysis Agent**: Analyzes and extracts metadata, entities, and patterns
- **Summary/Insight Agent**: Generates summaries and actionable insights using Gemini

### (C) MCP Toolbox
Provides access to:
- **Google Drive Tool**: List, search, and extract content from Google Drive
- **MongoDB Atlas Tool**: Vector database operations for semantic search
- **Spanner Tool**: Metadata storage and relationship management

## Features

- 🔍 **Semantic Search**: Query documents using natural language with RAG (Retrieval-Augmented Generation)
- 📄 **Multi-Format Support**: Process PDFs, Word docs, Excel, text files, and more
- 🔗 **Relationship Mapping**: Track relationships between documents and conversations
- 📊 **Metadata Analysis**: Extract entities, keywords, and patterns from content
- 🤖 **AI-Powered Insights**: Generate summaries and insights using Gemini
- 🔌 **Platform Integrations**: Connect to Google Drive, Jira, and Slack
- ☁️ **Cloud-Native**: Built for Google Cloud Platform (Cloud Run, Spanner, MongoDB Atlas)

## Setup Instructions

### Prerequisites

1. **Google Cloud Project** with the following APIs enabled:
   - Cloud Run API
   - Cloud Spanner API
   - Secret Manager API
   - Google Drive API

2. **MongoDB Atlas** cluster with vector search enabled

3. **Python 3.11+**

4. **Service Account** with appropriate permissions

### Installation

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd cloudknow
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   GCP_PROJECT_ID=your-project-id
   MONGODB_ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net/
   SPANNER_PROJECT_ID=your-project-id
   SPANNER_INSTANCE_ID=cloudknow-instance
   SPANNER_DATABASE_ID=cloudknow-db
   GEMINI_API_KEY=your-gemini-api-key
   # ... other configuration
   ```

5. **Set up Google Cloud credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
   ```

6. **Create Spanner instance and database**:
   ```bash
   gcloud spanner instances create cloudknow-instance \
     --config=regional-us-central1 \
     --description="CloudKnow metadata database" \
     --processing-units=100
   
   gcloud spanner databases create cloudknow-db \
     --instance=cloudknow-instance
   ```

   The schema will be created automatically on first use.

7. **Set up MongoDB Atlas vector search index**:
   - Create a search index named `vector_index` on your collection
   - Use the following configuration:
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

### Running Locally

1. **Start the FastAPI server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8080
   ```

2. **Access the API**:
   - API: http://localhost:8080
   - Interactive docs: http://localhost:8080/docs
   - Health check: http://localhost:8080/health

### Deployment to Google Cloud Run

1. **Build and push the Docker image**:
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

   Or manually:
   ```bash
   docker build -t gcr.io/YOUR_PROJECT_ID/cloudknow .
   docker push gcr.io/YOUR_PROJECT_ID/cloudknow
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy cloudknow \
     --image gcr.io/YOUR_PROJECT_ID/cloudknow \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2
   ```

## API Usage

### Health Check
```bash
curl http://localhost:8080/health
```

### Process a Document
```bash
curl -X POST http://localhost:8080/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "source": "google_drive",
    "source_id": "file-id-123",
    "content": "Your document content here...",
    "file_name": "example.txt"
  }'
```

### Query the Knowledge Base
```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features of our product?",
    "limit": 10
  }'
```

### Ingest from Google Drive
```bash
curl -X POST http://localhost:8080/ingestion/google-drive \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "your-folder-id",
    "limit": 50
  }'
```

## Project Structure

```
cloudknow/
├── api/                    # Application Layer
│   ├── config/            # Configuration
│   ├── core/              # Core dependencies
│   ├── middleware/        # Middleware
│   ├── models/            # Pydantic models
│   ├── routes/            # API routes
│   └── services/          # Business logic services
├── agents/                # ADK Agent Orchestration
│   ├── skills/           # Individual agent skills
│   └── workflows/        # Agent workflows
├── connectors/           # Platform connectors
│   ├── google_drive/
│   ├── jira/
│   └── slack/
├── mcp/                  # MCP Toolbox
│   └── tools/            # MCP tools
├── rag/                  # RAG pipeline
│   ├── embedding/       # Embedding service
│   ├── ingestion/       # Ingestion service
│   ├── retrieval/       # Retrieval service
│   └── vectorstore/     # Vector store
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
└── cloudbuild.yaml     # Cloud Build configuration
```

## Next Steps

1. **Configure Authentication**: Set up proper authentication for production
2. **Add More Connectors**: Extend support for Confluence, Notion, etc.
3. **Enhance Agents**: Add more sophisticated NLP capabilities
4. **Monitoring**: Set up logging and monitoring with Cloud Logging
5. **Testing**: Add comprehensive test suite
6. **Documentation**: Expand API documentation with examples

## Contributing

This is a foundational implementation. Areas for enhancement:
- Error handling and retry logic
- Caching for improved performance
- Batch processing capabilities
- Webhook support for real-time updates
- Advanced relationship detection
- Multi-language support



