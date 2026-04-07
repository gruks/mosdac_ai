from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Ollama configuration
    ollama_url: str = "http://localhost:11434/v1"
    model_name: str = "mosdac-coder"
    
    # API server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # API keys (for future auth)
    api_key: str = "dev-key-123"
    api_key_header: str = "Authorization"
    
    # Rate limiting (for future Phase 2)
    requests_per_minute: int = 60
    
    # Context settings
    max_context_tokens: int = 4096
    max_response_tokens: int = 2048
    
    # Timeouts
    request_timeout_seconds: int = 120
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()