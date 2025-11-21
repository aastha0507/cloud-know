"""API routes for document relationships."""
from fastapi import APIRouter, Depends, HTTPException
import hashlib
from datetime import datetime

from api.models.schemas import RelationshipRequest, RelationshipResponse
from api.core.dependencies import get_settings
from cloudknow_tools.tools import SpannerTool

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post("", response_model=RelationshipResponse)
async def create_relationship(
    request: RelationshipRequest,
    settings=Depends(get_settings)
):
    """Create a relationship between two documents."""
    try:
        spanner_tool = SpannerTool()
        
        # Generate relationship ID
        combined = f"{request.source_document_id}:{request.target_document_id}:{request.relationship_type}"
        relationship_id = hashlib.sha256(combined.encode()).hexdigest()[:32]
        
        success = spanner_tool.create_relationship(
            relationship_id=relationship_id,
            source_document_id=request.source_document_id,
            target_document_id=request.target_document_id,
            relationship_type=request.relationship_type,
            strength=request.strength,
            metadata=request.metadata
        )
        
        if success:
            return RelationshipResponse(
                success=True,
                relationship_id=relationship_id
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create relationship")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

