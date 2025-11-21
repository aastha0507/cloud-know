"""API routes for conversational agent."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from api.core.dependencies import get_settings

router = APIRouter(prefix="/agent", tags=["agent"])


class FolderQueryRequest(BaseModel):
    """Request for folder query agent."""
    folder_id: str = Field(..., description="Google Drive folder ID")
    query: str = Field(..., description="Query/question about the files")
    limit: Optional[int] = Field(None, ge=1, description="Maximum number of files to process")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")


class FolderQueryResponse(BaseModel):
    """Response from folder query agent."""
    success: bool
    query: str
    folder_id: str
    files_processed: int
    files_with_relevant_content: int
    files: List[Dict[str, Any]]
    ingestion_summary: Dict[str, Any]
    error: Optional[str] = None
    message: Optional[str] = None


@router.post("/folder-query", response_model=FolderQueryResponse)
async def folder_query_agent(
    request: FolderQueryRequest,
    settings=Depends(get_settings)
):
    """ADK Agent that ingests Google Drive folder and answers queries.
    
    This agent:
    1. Ingests all files from the specified Google Drive folder
    2. Queries the ingested content using semantic search
    3. Returns file names with brief descriptions of relevant content
    
    Example:
        {
            "folder_id": "1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW",
            "query": "What are the binary tree algorithms?",
            "limit": 10,
            "min_score": 0.6
        }
    """
    try:
        # Lazy import to avoid circular dependency
        from agents.workflows.conversational_agent import ConversationalAgent
        agent = ConversationalAgent()
        result = agent.process_folder_query(
            folder_id=request.folder_id,
            query=request.query,
            limit=request.limit,
            min_score=request.min_score
        )
        
        return FolderQueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

