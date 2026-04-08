"""FastAPI gateway application with auth and rate limiting."""

from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded

from .auth import verify_api_key
from .config import settings
from .errors import generic_exception_handler, openai_exception_handler, validation_exception_handler
from .rate_limiter import limiter

# Import API v1 routers
from src.api.v1 import chat, completions, models


async def _rate_limit_exceeded_handler(request: Request, exc: Any) -> JSONResponse:
    """Handle rate limit exceeded errors with OpenAI-compatible error schema.
    
    Args:
        request: The FastAPI request.
        exc: The exception (usually RateLimitExceeded).
        
    Returns:
        JSONResponse with OpenAI error schema and Retry-After header.
    """
    # Get retry-after from exception detail if available
    retry_after = "60"
    if hasattr(exc, "detail") and isinstance(exc.detail, dict):
        retry_after = exc.detail.get("retry_after", "60")
    
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "message": "Rate limit exceeded",
                "type": "invalid_request_error",
                "code": "rate_limit_exceeded",
                "param": None,
            }
        },
        headers={"Retry-After": retry_after},
    )


# Create FastAPI app instance
app = FastAPI(
    title="MOSDAC AI Gateway",
    description="OpenAI-compatible API gateway with multi-model support",
    version="0.1.0",
)


# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register exception handlers for OpenAI-compatible errors
from fastapi import HTTPException
app.add_exception_handler(HTTPException, openai_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register API v1 routers
app.include_router(chat.router)
app.include_router(completions.router)
app.include_router(models.router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint - no auth required.
    
    Returns:
        Simple status response.
    """
    return {"status": "ok"}


@app.get("/v1/auth-test")
@limiter.limit("60/minute")
async def auth_test(request: Request, api_key: dict = Depends(verify_api_key)) -> dict:
    """Test endpoint requiring API key authentication.
    
    Args:
        request: The FastAPI request (for rate limiting).
        api_key: Verified API key metadata from verify_api_key dependency.
        
    Returns:
        Authentication status with key name.
    """
    return {
        "authenticated": True,
        "key_name": api_key.get("name", "unknown"),
    }
