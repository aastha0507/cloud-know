"""API routes for document operations."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
import base64

from api.models.schemas import (
    DocumentProcessRequest,
    DocumentProcessResponse,
    DocumentMetadataResponse
)
from api.core.dependencies import get_settings
from rag.ingestion.ingestion_service import IngestionService
from cloudknow_tools.tools import SpannerTool

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/process", response_model=DocumentProcessResponse)
async def process_document(
    request: DocumentProcessRequest,
    settings=Depends(get_settings)
):
    """Process a document through the complete pipeline."""
    try:
        ingestion_service = IngestionService()
        
        if request.content:
            # Process text content
            result = ingestion_service.ingest_text(
                text=request.content,
                source=request.source,
                source_id=request.source_id,
                title=request.file_name,
                metadata=request.metadata
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'content' or file upload required"
            )
        
        return DocumentProcessResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/upload", response_model=DocumentProcessResponse)
async def process_uploaded_document(
    file: UploadFile = File(...),
    source: str = "upload",
    source_id: Optional[str] = None,
    settings=Depends(get_settings)
):
    """Process an uploaded file."""
    try:
        # Read file content
        content = await file.read()
        
        # Generate source_id if not provided
        if not source_id:
            import hashlib
            source_id = hashlib.sha256(content).hexdigest()[:16]
        
        ingestion_service = IngestionService()
        workflow = ingestion_service.workflow
        
        result = workflow.process_document(
            file_content=content,
            source=source,
            source_id=source_id,
            mime_type=file.content_type or "application/octet-stream",
            file_name=file.filename,
            metadata={}
        )
        
        return DocumentProcessResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/metadata", response_model=DocumentMetadataResponse)
async def get_document_metadata(
    document_id: str,
    settings=Depends(get_settings)
):
    """Get metadata for a document."""
    try:
        spanner_tool = SpannerTool()
        metadata = spanner_tool.get_document_metadata(document_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentMetadataResponse(**metadata)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/relationships")
async def get_document_relationships(
    document_id: str,
    relationship_type: Optional[str] = None,
    settings=Depends(get_settings)
):
    """Get relationships for a document."""
    try:
        spanner_tool = SpannerTool()
        relationships = spanner_tool.get_document_relationships(
            document_id,
            relationship_type=relationship_type
        )
        
        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

