"""CloudKnow - AI Knowledge Hub Application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from api.routes import (
    documents_router,
    query_router,
    ingestion_router,
    relationships_router,
    agent_router
)
from api.models.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Determine environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

app = FastAPI(
    title="CloudKnow",
    description="CloudKnow - AI Knowledge Hub (FastAPI + ADK + MCP + RAG)",
    version="0.1.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None
)

# CORS middleware - configure for production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if ENVIRONMENT == "production" and "*" in allowed_origins:
    logger.warning("CORS is set to allow all origins in production. Consider restricting this.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred" if ENVIRONMENT == "production" else str(exc)
        }
    )

# Include routers
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(ingestion_router)
app.include_router(relationships_router)
app.include_router(agent_router)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for Cloud Run."""
    try:
        return HealthResponse(status="ok", app="CloudKnow")
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "app": "CloudKnow", "error": str(e)}
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CloudKnow API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs" if ENVIRONMENT != "production" else "disabled"
    }
