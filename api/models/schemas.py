"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    app: str


class DocumentProcessRequest(BaseModel):
    """Request to process a document."""
    source: str = Field(..., description="Source platform (e.g., 'google_drive', 'jira')")
    source_id: str = Field(..., description="ID in the source platform")
    content: Optional[str] = Field(None, description="Text content (if already extracted)")
    file_name: Optional[str] = Field(None, description="File name")
    mime_type: Optional[str] = Field(None, description="MIME type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentProcessResponse(BaseModel):
    """Response from document processing."""
    success: bool
    document_id: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    chunks_created: Optional[int] = None
    summary: Optional[Dict[str, Any]] = None
    insights: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processed_at: Optional[str] = None


class QueryRequest(BaseModel):
    """Request to query the knowledge base."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    source_filter: Optional[str] = Field(None, description="Filter by source platform")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    include_relationships: bool = Field(True, description="Include document relationships")


class QueryResponse(BaseModel):
    """Response from query."""
    query: str
    results: List[Dict[str, Any]]
    count: int
    relationships: Optional[List[Dict[str, Any]]] = None


class AnswerRequest(BaseModel):
    """Request for evaluation agent answer (natural language Q&A with citations)."""
    question: str = Field(..., description="Natural language question")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for follow-up context")
    limit: int = Field(6, ge=1, le=20, description="Max chunks to use as context")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score for retrieval")


class TokenUsageSchema(BaseModel):
    """Token usage for reporting."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CachingMetricsSchema(BaseModel):
    """Caching metrics for cost report (embedding + LLM answer cache)."""
    enabled: bool = False
    cache_hits: int = 0
    cache_misses: int = 0
    llm_cache_hits: int = 0


class CostReportResponse(BaseModel):
    """Full cost report: tokens (input/output), embedding calls, caching metrics."""
    token_usage: TokenUsageSchema = Field(..., description="Total tokens used (input/output breakdown)")
    embedding_calls: int = Field(0, description="Number of embedding API calls made")
    caching: CachingMetricsSchema = Field(default_factory=CachingMetricsSchema, description="Caching metrics (if enabled)")


class AnswerResponse(BaseModel):
    """Response from evaluation agent: answer grounded in sources with citations."""
    answer: str = Field(..., description="Generated answer (grounded in source documents)")
    sources: List[str] = Field(default_factory=list, description="Document(s) the answer came from")
    token_usage: TokenUsageSchema = Field(default_factory=lambda: TokenUsageSchema())
    answered_from_context: bool = Field(..., description="True if answer was grounded in retrieved docs")
    error: Optional[str] = None


class IngestDriveRequest(BaseModel):
    """Request to ingest from Google Drive."""
    folder_id: str = Field(..., description="Google Drive folder ID")
    limit: Optional[int] = Field(None, ge=1, description="Maximum number of files to process")


class IngestGitHubRequest(BaseModel):
    """Request to ingest from a GitHub repository path (e.g. NovaTech KB)."""
    owner: str = Field(..., description="Repository owner (e.g. Rapid-Claim)")
    repo: str = Field(..., description="Repository name (e.g. hackathon-ps)")
    path: str = Field("novatech-kb", description="Path inside repo (e.g. novatech-kb)")
    ref: str = Field("dev", description="Branch or ref (e.g. dev)")
    limit: Optional[int] = Field(None, ge=1, description="Maximum number of files to process")
    github_token: Optional[str] = Field(None, description="Optional GitHub token for private repos")


class IngestDriveResponse(BaseModel):
    """Response from Google Drive ingestion."""
    source: str
    folder_id: str
    files_found: int
    total_processed: int
    processed: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    error: Optional[str] = None
    success: Optional[bool] = None


class IngestGitHubResponse(BaseModel):
    """Response from GitHub repository ingestion."""
    source: str = "github"
    owner: str = ""
    repo: str = ""
    path: str = ""
    ref: str = ""
    files_found: int = 0
    total_processed: int = 0
    processed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    error: Optional[str] = None


class DocumentMetadataResponse(BaseModel):
    """Response with document metadata."""
    document_id: str
    source: str
    source_id: str
    title: Optional[str] = None
    content_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RelationshipRequest(BaseModel):
    """Request to create a document relationship."""
    source_document_id: str = Field(..., description="Source document ID")
    target_document_id: str = Field(..., description="Target document ID")
    relationship_type: str = Field(..., description="Type of relationship")
    strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relationship strength")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RelationshipResponse(BaseModel):
    """Response from relationship creation."""
    success: bool
    relationship_id: Optional[str] = None
    error: Optional[str] = None

