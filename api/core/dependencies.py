"""FastAPI dependencies for dependency injection."""
from functools import lru_cache
from api.config.settings import Settings


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

