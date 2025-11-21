"""API routes."""
from api.routes.documents import router as documents_router
from api.routes.query import router as query_router
from api.routes.ingestion import router as ingestion_router
from api.routes.relationships import router as relationships_router
from api.routes.agent import router as agent_router

__all__ = [
    "documents_router",
    "query_router",
    "ingestion_router",
    "relationships_router",
    "agent_router"
]

