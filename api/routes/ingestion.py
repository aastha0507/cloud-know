"""API routes for ingesting documents from various sources."""
from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import (
    IngestDriveRequest,
    IngestDriveResponse
)
from api.core.dependencies import get_settings
from rag.ingestion.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/google-drive", response_model=IngestDriveResponse)
async def ingest_from_google_drive(
    request: IngestDriveRequest,
    settings=Depends(get_settings)
):
    """Ingest documents from a Google Drive folder."""
    try:
        ingestion_service = IngestionService()
        result = ingestion_service.ingest_from_google_drive(
            folder_id=request.folder_id,
            limit=request.limit
        )
        
        return IngestDriveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

