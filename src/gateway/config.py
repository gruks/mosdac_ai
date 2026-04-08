"""Application configuration using pydantic-settings."""

import json
from pathlib import Path
from typing import Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL for Redis connection",
    )
    redis_max_connections: int = Field(
        default=10,
        description="Maximum number of Redis connections in pool",
    )

    # vLLM Backend Configuration
    vllm_backends: Dict[str, str] = Field(
        default_factory=lambda: {"default": "http://localhost:11434"},
        description="JSON mapping of model names to backend URLs",
    )

    # Timeout Configuration (seconds)
    default_timeout_connect: float = Field(
        default=5.0,
        description="Connection timeout in seconds",
    )
    default_timeout_read: float = Field(
        default=300.0,
        description="Read timeout in seconds (for long-running inference)",
    )
    default_timeout_write: float = Field(
        default=10.0,
        description="Write timeout in seconds",
    )
    default_timeout_pool: float = Field(
        default=5.0,
        description="Pool acquisition timeout in seconds",
    )

    # Rate Limiting
    rate_limit_default: str = Field(
        default="100/minute",
        description="Default rate limit for requests",
    )

    # API Keys
    api_keys_file: str = Field(
        default="data/api_keys.json",
        description="Path to JSON file containing API keys",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    def __init__(self, **kwargs):
        """Initialize settings with JSON parsing for vllm_backends."""
        # Handle vllm_backends JSON string conversion
        if "vllm_backends" in kwargs and isinstance(kwargs["vllm_backends"], str):
            kwargs["vllm_backends"] = json.loads(kwargs["vllm_backends"])
        super().__init__(**kwargs)

    def load_vllm_backends(self) -> Dict[str, str]:
        """Load vLLM backends from environment variable as JSON string.

        Returns:
            Dict mapping model names to backend URLs.
        """
        # Already parsed in __init__, just return
        return self.vllm_backends


# Singleton instance - DO NOT modify at runtime in multi-process environments
settings = Settings()
