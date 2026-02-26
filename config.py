"""
Centralized configuration using Pydantic Settings.
Loads environment variables and provides typed access throughout the application.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider
    openai_api_key: str = ""
    nvidia_api_key: str = ""
    llm_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    
    # API Security
    api_key: str = ""  # Set API_KEY in .env to enable auth
    
    # File Upload
    max_file_size_mb: int = 10
    
    # Error Tracking
    sentry_dsn: str = ""
    
    # Upstash Redis (Celery broker)
    upstash_redis_url: str = ""
    
    # Neon PostgreSQL
    database_url: str = ""
    
    # Debug mode
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def celery_broker_url(self) -> str:
        """Get Celery broker URL (Upstash Redis)."""
        return self.upstash_redis_url
    
    @property
    def celery_result_backend(self) -> str:
        """Get Celery result backend (same as broker for Upstash)."""
        return self.upstash_redis_url


settings = Settings()
