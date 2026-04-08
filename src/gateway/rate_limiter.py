"""Rate limiting middleware using slowapi with Redis storage."""

from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings
from .auth import get_api_key_from_request


def get_api_key_identifier(request: Request) -> str:
    """Extract identifier for rate limiting.
    
    Uses Bearer token if present (for per-key rate limiting),
    otherwise falls back to client IP address.
    
    Args:
        request: The FastAPI request object.
        
    Returns:
        Identifier string for rate limiting.
    """
    # Try to get API key for per-key rate limiting
    api_key = get_api_key_from_request(request)
    
    if api_key:
        return api_key
    
    # Fallback to client IP
    return get_remote_address(request)


# Create limiter with Redis storage backend
limiter = Limiter(
    key_func=get_api_key_identifier,
    storage_uri=settings.redis_url,
    default_limits=[settings.rate_limit_default],
)
