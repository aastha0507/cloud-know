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


class IngestDriveRequest(BaseModel):
    """Request to ingest from Google Drive."""
    folder_id: str = Field(..., description="Google Drive folder ID")
    limit: Optional[int] = Field(None, ge=1, description="Maximum number of files to process")


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

