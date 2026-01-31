"""API routes for querying the knowledge base."""
from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import (
    QueryRequest,
    QueryResponse,
    AnswerRequest,
    AnswerResponse,
    TokenUsageSchema,
    CostReportResponse,
    CachingMetricsSchema,
)
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


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(
    request: AnswerRequest,
    settings=Depends(get_settings)
):
    """
    Evaluation agent: accept natural language question, retrieve from knowledge base,
    generate accurate answer grounded in source documents, cite sources, support
    follow-up via conversation_id, and acknowledge when information isn't available.
    Uses OpenAI models and embeddings; token usage is tracked and reported.
    """
    openai_key = getattr(settings, "openai_api_key", None)
    if not openai_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is required for the answer agent. Set OPENAI_API_KEY.",
        )
    try:
        from rag.answer.answer_service import AnswerService
        service = AnswerService()
        result = service.answer(
            question=request.question,
            conversation_id=request.conversation_id,
            limit=request.limit,
            min_score=request.min_score,
        )
        return AnswerResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            token_usage=TokenUsageSchema(**result.get("token_usage", {})),
            answered_from_context=result.get("answered_from_context", False),
            error=result.get("error"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage", response_model=TokenUsageSchema)
async def get_token_usage(settings=Depends(get_settings)):
    """Report cumulative token usage for evaluation."""
    from rag.answer.token_usage import token_usage_tracker
    return TokenUsageSchema(**token_usage_tracker.get())


@router.get("/cost-report", response_model=CostReportResponse)
async def get_cost_report(settings=Depends(get_settings)):
    """
    Full cost report for evaluation: total tokens (input/output breakdown),
    embedding API calls made, and caching metrics.
    """
    from rag.answer.cost_report import cost_report_tracker
    report = cost_report_tracker.get_full_report()
    return CostReportResponse(
        token_usage=TokenUsageSchema(**report["token_usage"]),
        embedding_calls=report["embedding_calls"],
        caching=CachingMetricsSchema(**report["caching"]),
    )

