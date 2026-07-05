"""
Settings for API configuration.
"""

from pydantic import BaseSettings, Field
from typing import List, Optional


class APISettings(BaseSettings):
    """API-specific settings."""
    
    # API Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # CORS Configuration
    cors_origins: List[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: List[str] = ["Content-Type", "Authorization"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 20
    
    # API Versioning
    api_version: str = "v1"
    
    # OpenAPI Configuration
    docs_enabled: bool = True
    redoc_enabled: bool = True
    
    # Request/Response Configuration
    max_request_size_mb: int = 100
    request_timeout_seconds: int = 30
    
    class Config:
        env_prefix = "API_"
        env_file = ".env"


# Default settings instance
settings = APISettings()
