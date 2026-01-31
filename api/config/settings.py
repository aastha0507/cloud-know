"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and Secret Manager."""
    
    # GCP Configuration
    gcp_project_id: str
    google_application_credentials: Optional[str] = None
    
    # MongoDB Atlas Configuration
    mongodb_atlas_uri: str
    mongodb_database_name: str = "cloudknow"
    mongodb_collection_name: str = "documents"
    
    # Spanner Configuration
    spanner_project_id: str
    spanner_instance_id: str = "cloudknow-instance"
    spanner_database_id: str = "cloudknow-db"
    
    # Gemini API Configuration (legacy / non-eval)
    gemini_api_key: str
    gemini_model_name: str = "gemini-2.0-flash"
    
    # OpenAI API Configuration (required for evaluation agent)
    # Set OPENAI_API_KEY in .env or environment
    openai_api_key: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_dimensions: int = 1536
    mongodb_collection_openai: str = "documents"
    
    # ADK Configuration (optional, for local dev)
    google_genai_use_vertexai: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Google Drive Configuration
    google_drive_folder_id: Optional[str] = None
    
    # Jira Configuration
    jira_server: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    
    # Slack Configuration
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    
    # Application Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    log_level: str = "INFO"
    environment: str = "production"
    
    class Config:
        env_file = ".env" if os.path.exists(".env") else None
        case_sensitive = False
        extra = "ignore"


# Global settings instance
try:
    settings = Settings()
    logger.info("Settings loaded successfully")
except Exception as e:
    logger.error(f"Error loading settings: {str(e)}")
    raise
