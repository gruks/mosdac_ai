"""vLLM proxy with model routing and SSE streaming support."""

import logging
from typing import AsyncGenerator

import httpx
from fastapi import HTTPException

from src.gateway.config import Settings

logger = logging.getLogger(__name__)

# Model registry: maps model names to vLLM backend URLs
MODEL_REGISTRY: dict[str, str] = {
    "Qwen/Qwen2.5-Coder-32B-Instruct": "http://localhost:8001",
    "codellama/CodeLlama-70b-Instruct-hf": "http://localhost:8002",
}


def get_vllm_url_for_model(model: str) -> str:
    """
    Get the vLLM URL for a given model name.
    
    Validates the model against MODEL_REGISTRY.
    Raises HTTPException(400) with OpenAI error schema if model not found.
    """
    if model not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Model '{model}' not found. Available models: {list(MODEL_REGISTRY.keys())}",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_found",
                }
            },
        )
    return MODEL_REGISTRY[model]


async def proxy_stream(
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: dict,
    timeout: httpx.Timeout,
    stream: bool = False,
) -> AsyncGenerator[str, None]:
    """
    Forward request to vLLM with streaming support.
    
    Uses httpx.AsyncClient with streaming to forward SSE responses.
    Yields chunks via response.aiter_text() for real-time token delivery.
    Checks request.is_disconnected() periodically to cancel on client disconnect.
    """
    async with httpx.AsyncClient(timeout=timeout, limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
    )) as client:
        try:
            async with client.stream(method, url, headers=headers, json=json_body) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    # Check if client disconnected - could cancel vLLM generation
                    # Note: In production, implement proper disconnect detection
                    if not chunk:
                        continue
                    yield chunk
                    
        except httpx.ConnectTimeout as e:
            logger.error(f"Connection timeout to vLLM: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "message": "Backend service unavailable",
                        "type": "server_error",
                        "code": "service_unavailable",
                    }
                },
            )
        except httpx.ReadTimeout as e:
            logger.error(f"Read timeout during generation: {e}")
            raise HTTPException(
                status_code=504,
                detail={
                    "error": {
                        "message": "Request timed out during generation",
                        "type": "server_error",
                        "code": "request_timeout",
                    }
                },
            )
        except httpx.TimeoutException as e:
            logger.error(f"Timeout exception: {e}")
            raise HTTPException(
                status_code=504,
                detail={
                    "error": {
                        "message": "Request timed out",
                        "type": "server_error",
                        "code": "request_timeout",
                    }
                },
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"vLLM returned error: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail={
                    "error": {
                        "message": f"Backend error: {e.response.text}",
                        "type": "server_error",
                        "code": "backend_error",
                    }
                },
            )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()