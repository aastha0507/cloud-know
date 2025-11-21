# Google Drive Ingestion Flow - Complete Explanation

## Overview

When you send a curl request with a Google Drive folder ID, here's the complete flow of what happens:

```bash
curl -X POST http://localhost:8080/ingestion/google-drive \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "your_folder_id_here",
    "limit": 10
  }'
```

---

## Step-by-Step Flow

### **Step 1: API Endpoint Receives Request**
**File:** `api/routes/ingestion.py`

- FastAPI receives the POST request at `/ingestion/google-drive`
- Validates the request body using Pydantic schema (`IngestDriveRequest`)
- Extracts `folder_id` and `limit` from the request
- Creates an `IngestionService` instance
- Calls `ingest_from_google_drive(folder_id, limit)`

**What happens:**
```python
# Request validation
request = IngestDriveRequest(
    folder_id="1nNsuC0zdddd8IvbM2lAS4hCMMvJzaHF1DxFW",
    limit=10
)

# Service initialization
ingestion_service = IngestionService()
result = ingestion_service.ingest_from_google_drive(
    folder_id=request.folder_id,
    limit=request.limit
)
```

---

### **Step 2: Initialize Google Drive Tool**
**File:** `rag/ingestion/ingestion_service.py` → `mcp/tools/google_drive_tool.py`

- `IngestionService` creates a `GoogleDriveTool` instance
- Google Drive Tool authenticates using:
  - Service account credentials (if `GOOGLE_APPLICATION_CREDENTIALS` is set), OR
  - Application Default Credentials (from `gcloud auth application-default login`)
- Builds Google Drive API v3 client

**What happens:**
```python
# Authentication
if credentials_path:
    creds = service_account.Credentials.from_service_account_file(...)
else:
    creds, _ = default()  # Uses gcloud auth

# Build API client
service = build("drive", "v3", credentials=creds)
```

---

### **Step 3: List Files in Folder**
**File:** `mcp/tools/google_drive_tool.py` → `list_files()`

- Calls Google Drive API to list all files in the specified folder
- Query: `'FOLDER_ID' in parents and trashed=false`
- Retrieves: file ID, name, MIME type, modified time, size, web view link
- Orders by: `modifiedTime desc` (newest first)
- Returns list of file metadata

**What happens:**
```python
results = service.files().list(
    q=f"'{folder_id}' in parents and trashed=false",
    fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
    pageSize=limit or 100,
    orderBy="modifiedTime desc"
).execute()

files = results.get("files", [])
# Example: [{"id": "1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t", "name": "file.pdf", ...}]
```

---

### **Step 4: Process Each File (Loop)**

For each file found, the following steps are executed:

#### **4a. Get File Content**
**File:** `mcp/tools/google_drive_tool.py` → `get_file_content()`

- Retrieves file metadata (name, MIME type, owners, etc.)
- Downloads/exports file content based on MIME type:
  - **Text files**: Direct download
  - **Google Docs**: Export as plain text
  - **Google Sheets**: Export as CSV
  - **Google Slides**: Export as plain text
  - **PDFs/Binary**: Download as binary (will be extracted later)
- Returns file content + metadata

**What happens:**
```python
# Get metadata
file_metadata = service.files().get(
    fileId=file_id,
    fields="id, name, mimeType, modifiedTime, size, webViewLink, owners"
).execute()

# Get content based on type
if mime_type == "application/vnd.google-apps.document":
    # Google Doc - export as text
    content = service.files().export_media(
        fileId=file_id,
        mimeType="text/plain"
    ).execute().decode("utf-8")
elif mime_type == "application/pdf":
    # PDF - download binary
    content = service.files().get_media(fileId=file_id).execute()
else:
    # Text file - direct download
    content = service.files().get_media(fileId=file_id).execute().decode("utf-8")
```

---

#### **4b. Process Document Through Pipeline**
**File:** `agents/workflows/document_processing_workflow.py` → `process_document()`

The document goes through a 7-step processing pipeline:

##### **Step 4b.1: Extract Content**
**Agent:** `FileExtractionAgent`

- Extracts text from various file formats:
  - PDF → PyPDF2 extraction
  - DOCX → python-docx extraction
  - XLSX → openpyxl extraction
  - CSV → CSV parsing
  - JSON → JSON parsing
  - Text → Direct use
- Returns extracted text content

**What happens:**
```python
extraction_result = extraction_agent.extract(
    file_content=bytes,  # Binary file content
    mime_type="application/pdf",
    file_name="document.pdf"
)
content = extraction_result["content"]  # Extracted text
```

---

##### **Step 4b.2: Analyze Metadata**
**Agent:** `MetadataAnalysisAgent`

- Analyzes document content to extract:
  - **Patterns**: Emails, URLs, dates, phone numbers, Jira tickets
  - **Keywords**: Top 10 most frequent words (excluding stop words)
  - **Entities**: People, organizations, locations (simple extraction)
  - **Reading time**: Estimated reading time
  - **Word count**: Total words
  - **Source-specific analysis**: Google Drive structure, Jira issues, Slack mentions

**What happens:**
```python
analysis_metadata = metadata_agent.analyze(
    content="...",
    source="google_drive",
    source_id="1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t",
    file_name="document.pdf",
    mime_type="application/pdf"
)
# Returns: {
#   "word_count": 1234,
#   "keywords": ["coder", "army", "programming", ...],
#   "entities": {"people": [...], "organizations": [...]},
#   "extracted_patterns": {"email": [...], "url": [...]},
#   ...
# }
```

---

##### **Step 4b.3: Generate Summary & Insights**
**Agent:** `SummaryInsightAgent` (uses Gemini AI)

- **Summary Generation**:
  - Sends content to Gemini API (`gemini-pro` model)
  - Generates concise summary (~200 words)
  - Extracts key points
- **Insights Generation**:
  - Analyzes content for themes and topics
  - Identifies relationships and connections
  - Suggests action items or recommendations
  - Lists potential questions the content answers

**What happens:**
```python
# Generate summary
summary_result = summary_agent.generate_summary(
    content="...",
    max_length=200,
    include_key_points=True
)
# Returns: {
#   "summary": "This document discusses...",
#   "key_points": ["Point 1", "Point 2", ...],
#   "word_count": 150
# }

# Generate insights
insights_result = summary_agent.generate_insights(
    content="...",
    context=analysis_metadata
)
# Returns: {
#   "insights": "Main themes: programming, algorithms...",
#   "themes": ["programming", "algorithms"],
#   "action_items": [...]
# }
```

---

##### **Step 4b.4: Chunk the Document**
**Agent:** `ChunkingAgent`

- Splits document into smaller chunks (default: 1000 characters)
- Uses intelligent splitting:
  - Tries paragraph breaks first (`\n\n`)
  - Falls back to line breaks (`\n`)
  - Then sentence endings (`. `)
  - Finally word breaks (` `)
- Adds overlap between chunks (default: 200 characters) for context
- Each chunk gets:
  - Unique chunk ID: `{document_id}_chunk_{index}`
  - Chunk index and total chunks
  - All document metadata

**What happens:**
```python
chunks = chunking_agent.chunk(
    text="Long document content...",
    metadata={
        "document_id": "0fc9556a33b7bea46eba7df68d7d0a34",
        "source": "google_drive",
        ...
    }
)
# Returns: [
#   {
#     "chunk_id": "0fc9556a33b7bea46eba7df68d7d0a34_chunk_0",
#     "content": "First 1000 chars...",
#     "chunk_index": 0,
#     "metadata": {...}
#   },
#   {
#     "chunk_id": "0fc9556a33b7bea46eba7df68d7d0a34_chunk_1",
#     "content": "Next 1000 chars (with 200 char overlap)...",
#     ...
#   }
# ]
```

---

##### **Step 4b.5: Generate Embeddings & Store in MongoDB**
**Services:** `EmbeddingService` + `MongoDBAtlasTool`

For each chunk:

1. **Generate Embedding**:
   - Uses Gemini API (`text-embedding-004` model)
   - Converts chunk text to 768-dimensional vector
   - Returns list of floats

2. **Store in MongoDB Atlas**:
   - Stores chunk with:
     - `_id`: chunk_id (e.g., `document_id_chunk_0`)
     - `content`: Full chunk text
     - `embedding`: 768-dimensional vector array
     - `metadata`: All chunk metadata
   - Uses `replace_one()` with `upsert=True` (handles duplicates)

**What happens:**
```python
for chunk in chunks:
    # Generate embedding
    embedding = embedding_service.embed(chunk["content"])
    # Returns: [0.123, -0.456, 0.789, ...] (768 numbers)
    
    # Store in MongoDB
    mongodb_tool.insert_document(
        document_id=chunk["chunk_id"],
        content=chunk["content"],
        embedding=embedding,
        metadata=chunk["metadata"],
        source="google_drive"
    )
    # MongoDB stores in: cloudknow.documents collection
    # Vector search index: vector_index (for semantic search)
```

---

##### **Step 4b.6: Store Metadata in Spanner**
**Tool:** `SpannerTool`

- Generates document ID: `SHA256(source:source_id)[:32]`
- Stores document-level metadata in Spanner:
  - Document ID, source, source ID
  - Title, content type, file path, file size
  - Created/updated timestamps
  - Owner, tags (from keywords)
  - Summary, key points, insights, themes
  - Word count, chunk count
- Uses `insert_or_update()` to handle duplicates (preserves `created_at`)

**What happens:**
```python
document_id = hashlib.sha256(
    f"google_drive:1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t".encode()
).hexdigest()[:32]
# Returns: "0fc9556a33b7bea46eba7df68d7d0a34"

spanner_tool.store_document_metadata(
    document_id=document_id,
    source="google_drive",
    source_id="1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t",
    title="Coder Army Sheet - Sheet1.pdf",
    content_type="application/pdf",
    file_size=12345,
    tags=["coder", "army", "programming", ...],
    metadata={
        "summary": "Document summary...",
        "key_points": [...],
        "insights": "...",
        "word_count": 1234,
        "chunk_count": 1
    }
)
# Stores in: Spanner table `document_metadata`
```

---

##### **Step 4b.7: Generate Citation**
**Agent:** `SummaryInsightAgent`

- Creates citation information for the document
- Formats based on source type
- Includes: title, source, source ID, URL (if available)

**What happens:**
```python
citation = summary_agent.generate_citation(
    content="...",
    source="google_drive",
    source_id="1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t",
    metadata={"title": "...", "web_view_link": "https://..."}
)
# Returns: {
#   "source": "google_drive",
#   "source_id": "1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t",
#   "title": "Coder Army Sheet - Sheet1.pdf",
#   "url": "https://drive.google.com/...",
#   "formatted": "Coder Army Sheet - Sheet1.pdf - Google Drive (https://...)"
# }
```

---

### **Step 5: Return Results**

After processing all files, returns summary:

**Response Format:**
```json
{
  "source": "google_drive",
  "folder_id": "1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW",
  "files_found": 1,
  "total_processed": 1,
  "processed": [
    {
      "file_id": "1IZ_RJaHPYUo1sntLlw4NTkTxBoCHXB6t",
      "file_name": "Coder Army Sheet - Sheet1.pdf",
      "document_id": "0fc9556a33b7bea46eba7df68d7d0a34"
    }
  ],
  "failed": []
}
```

---

## Data Storage Summary

### **MongoDB Atlas** (Vector Database)
- **Collection**: `cloudknow.documents`
- **Stores**: Document chunks with embeddings
- **Purpose**: Semantic search using vector similarity
- **Index**: `vector_index` (knnVector, 768 dimensions, cosine similarity)

### **Google Cloud Spanner** (Metadata Database)
- **Table**: `document_metadata`
- **Stores**: Document-level metadata, summaries, insights
- **Purpose**: Fast metadata queries, relationships, filtering
- **Indexes**: `idx_source` (source, source_id)

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Curl Request                                             │
│    POST /ingestion/google-drive                             │
│    {folder_id: "1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW"}        │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. API Route (ingestion.py)                                │
│    - Validates request                                      │
│    - Creates IngestionService                               │
│    - Calls ingest_from_google_drive()                       │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Google Drive Tool                                        │
│    - Authenticates (gcloud auth or service account)         │
│    - Lists files in folder                                  │
│    - For each file:                                         │
│      • Gets file content (download/export)                  │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Document Processing Workflow                             │
│    ┌──────────────────────────────────────────────────┐    │
│    │ 4.1 Extract Content (FileExtractionAgent)        │    │
│    │     PDF/DOCX/XLSX → Text                         │    │
│    └────────────────┬─────────────────────────────────┘    │
│                     │                                        │
│    ┌────────────────▼──────────────────────────────────┐    │
│    │ 4.2 Analyze Metadata (MetadataAnalysisAgent)       │    │
│    │     Keywords, Entities, Patterns                   │    │
│    └────────────────┬─────────────────────────────────┘    │
│                     │                                        │
│    ┌────────────────▼──────────────────────────────────┐    │
│    │ 4.3 Generate Summary/Insights (SummaryInsightAgent)│    │
│    │     Uses Gemini AI                                │    │
│    └────────────────┬─────────────────────────────────┘    │
│                     │                                        │
│    ┌────────────────▼──────────────────────────────────┐    │
│    │ 4.4 Chunk Document (ChunkingAgent)                │    │
│    │     Split into 1000-char chunks with overlap      │    │
│    └────────────────┬─────────────────────────────────┘    │
│                     │                                        │
│    ┌────────────────▼──────────────────────────────────┐    │
│    │ 4.5 Generate Embeddings (EmbeddingService)       │    │
│    │     Text → 768-dim vector (Gemini API)            │    │
│    └────────────────┬─────────────────────────────────┘    │
│                     │                                        │
│    ┌────────────────▼──────────────────────────────────┐    │
│    │ 4.6 Store in MongoDB Atlas                        │    │
│    │     Chunks + Embeddings (for semantic search)     │    │
│    └────────────────┬─────────────────────────────────┘    │
│                     │                                        │
│    ┌────────────────▼──────────────────────────────────┐    │
│    │ 4.7 Store Metadata in Spanner                     │    │
│    │     Document metadata, summaries, insights        │    │
│    └───────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Return Results                                            │
│    {files_found, processed, failed}                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Points

1. **Authentication**: Uses Google Application Default Credentials or service account
2. **File Types**: Handles PDFs, Google Docs/Sheets/Slides, text files, etc.
3. **AI Processing**: Uses Gemini for embeddings and summaries
4. **Storage**: 
   - MongoDB = Vector search (semantic queries)
   - Spanner = Metadata (fast lookups, relationships)
5. **Error Handling**: Continues processing other files if one fails
6. **Idempotency**: Can re-process same files (upsert handles duplicates)

---

## Example: Processing a PDF

1. **List files**: Finds `Coder Army Sheet - Sheet1.pdf`
2. **Download**: Gets PDF binary from Google Drive
3. **Extract**: PyPDF2 extracts text from PDF
4. **Analyze**: Finds keywords like "coder", "army", "programming"
5. **Summarize**: Gemini generates: "This document contains a coding practice sheet..."
6. **Chunk**: Splits into 1 chunk (small document)
7. **Embed**: Converts to 768-dim vector: `[0.123, -0.456, ...]`
8. **Store MongoDB**: Saves chunk with embedding
9. **Store Spanner**: Saves document metadata with summary
10. **Return**: `{document_id: "0fc9556a...", success: true}`

Now the document is searchable via semantic queries! 🎉

