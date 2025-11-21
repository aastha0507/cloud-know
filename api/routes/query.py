"""API routes for querying the knowledge base."""
from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import QueryRequest, QueryResponse
from api.core.dependencies import get_settings
from rag.retrieval.retrieval_service import RetrievalService

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    settings=Depends(get_settings)
):
    """Query the knowledge base using RAG."""
    try:
        retrieval_service = RetrievalService()
        
        if request.include_relationships:
            result = retrieval_service.retrieve_with_context(
                query=request.query,
                limit=request.limit
            )
        else:
            results = retrieval_service.retrieve(
                query=request.query,
                limit=request.limit,
                source_filter=request.source_filter,
                min_score=request.min_score
            )
            result = {
                "query": request.query,
                "results": results,
                "count": len(results)
            }
        
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_knowledge_base(
    q: str,
    limit: int = 10,
    source: str = None,
    settings=Depends(get_settings)
):
    """Simple GET endpoint for searching."""
    try:
        retrieval_service = RetrievalService()
        results = retrieval_service.retrieve(
            query=q,
            limit=limit,
            source_filter=source
        )
        
        return {
            "query": q,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

