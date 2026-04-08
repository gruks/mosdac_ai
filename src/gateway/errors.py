"""OpenAI-compatible error handling for the gateway."""

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def get_error_code(status_code: int) -> str:
    """Map HTTP status codes to OpenAI error codes."""
    mapping = {
        400: "invalid_request_error",
        401: "invalid_api_key",
        403: "permission_error",
        404: "not_found_error",
        429: "rate_limit_exceeded",
        500: "server_error",
        502: "server_error",
        503: "service_unavailable",
        504: "request_timeout",
    }
    return mapping.get(status_code, "server_error")


async def openai_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Convert HTTPException to OpenAI-compatible error response format.
    
    Wraps any HTTPException into OpenAIErrorResponse format.
    Handles both string detail and dict detail.
    """
    # Extract error details
    detail = exc.detail
    if isinstance(detail, dict):
        # Already formatted as OpenAI error
        error_data = detail.get("error", {})
        message = error_data.get("message", str(exc.detail))
        error_type = error_data.get("type", get_error_code(exc.status_code))
        param = error_data.get("param")
        code = error_data.get("code")
    else:
        # String detail - format as OpenAI error
        message = str(detail)
        error_type = get_error_code(exc.status_code)
        param = None
        code = None
    
    # Return OpenAI-compatible format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": param,
                "code": code,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Wrap RequestValidationError into OpenAI error schema.
    
    Pydantic validation errors become invalid_request_error.
    """
    errors = exc.errors()
    error_messages = [
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors
    ]
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "; ".join(error_messages),
                "type": "invalid_request_error",
                "param": None,
                "code": "validation_error",
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.
    
    Converts any unexpected error to 500 with OpenAI error schema.
    """
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An unexpected error occurred",
                "type": "server_error",
                "param": None,
                "code": "internal_error",
            }
        },
    )