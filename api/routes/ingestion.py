"""API routes for ingesting documents from various sources."""
from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import (
    IngestDriveRequest,
    IngestDriveResponse,
    IngestGitHubRequest,
    IngestGitHubResponse,
)
from api.core.dependencies import get_settings
from rag.ingestion.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/google-drive", response_model=IngestDriveResponse)
async def ingest_from_google_drive(
    request: IngestDriveRequest,
    settings=Depends(get_settings)
):
    """Ingest documents from a Google Drive folder (uses Gemini embeddings, default collection)."""
    try:
        ingestion_service = IngestionService()
        result = ingestion_service.ingest_from_google_drive(
            folder_id=request.folder_id,
            limit=request.limit
        )
        
        return IngestDriveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/openai/google-drive", response_model=IngestDriveResponse)
async def ingest_from_google_drive_openai(
    request: IngestDriveRequest,
    settings=Depends(get_settings)
):
    """Ingest documents from Google Drive using OpenAI embeddings into documents_openai (for evaluation agent)."""
    openai_key = getattr(settings, "openai_api_key", None)
    if not openai_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is required for OpenAI ingestion.",
        )
    try:
        from rag.embedding.openai_embedding_service import OpenAIEmbeddingService
        from agents.workflows.document_processing_workflow import DocumentProcessingWorkflow
        from cloudknow_tools.tools.mongodb_tool import MongoDBAtlasTool

        workflow = DocumentProcessingWorkflow(
            embedding_service=OpenAIEmbeddingService(api_key=openai_key),
            mongodb_tool=MongoDBAtlasTool(
                collection_name=getattr(settings, "mongodb_collection_openai", "documents"),
                embedding_dimensions=getattr(settings, "openai_embedding_dimensions", 1536),
            ),
        )
        ingestion_service = IngestionService(workflow=workflow)
        result = ingestion_service.ingest_from_google_drive(
            folder_id=request.folder_id,
            limit=request.limit
        )
        return IngestDriveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/github", response_model=IngestGitHubResponse)
async def ingest_from_github(
    request: IngestGitHubRequest,
    settings=Depends(get_settings)
):
    """Ingest documents from a GitHub repo path (e.g. NovaTech KB) using Gemini embeddings, default collection."""
    try:
        ingestion_service = IngestionService()
        result = ingestion_service.ingest_from_github(
            owner=request.owner,
            repo=request.repo,
            path=request.path or "novatech-kb",
            ref=request.ref or "dev",
            limit=request.limit,
            github_token=request.github_token,
        )
        return IngestGitHubResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/openai/github", response_model=IngestGitHubResponse)
async def ingest_from_github_openai(
    request: IngestGitHubRequest,
    settings=Depends(get_settings)
):
    """Ingest NovaTech KB (or any GitHub path) using OpenAI embeddings into documents_openai for the evaluation agent."""
    openai_key = getattr(settings, "openai_api_key", None)
    if not openai_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is required for OpenAI ingestion.",
        )
    try:
        from rag.embedding.openai_embedding_service import OpenAIEmbeddingService
        from agents.workflows.document_processing_workflow import DocumentProcessingWorkflow
        from cloudknow_tools.tools.mongodb_tool import MongoDBAtlasTool

        workflow = DocumentProcessingWorkflow(
            embedding_service=OpenAIEmbeddingService(api_key=openai_key),
            mongodb_tool=MongoDBAtlasTool(
                collection_name=getattr(settings, "mongodb_collection_openai", "documents"),
                embedding_dimensions=getattr(settings, "openai_embedding_dimensions", 1536),
            ),
        )
        ingestion_service = IngestionService(workflow=workflow)
        result = ingestion_service.ingest_from_github(
            owner=request.owner,
            repo=request.repo,
            path=request.path or "novatech-kb",
            ref=request.ref or "dev",
            limit=request.limit,
            github_token=request.github_token,
            minimal=True,
        )
        return IngestGitHubResponse(**result)
    except Exception as e:
        import logging
        logging.exception("OpenAI GitHub ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))

