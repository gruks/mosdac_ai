"""API v1 router for /v1/completions endpoint."""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.gateway import auth, proxy
from src.gateway.models import CompletionRequest
from src.gateway.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["completions"])


@router.post("/completions")
async def completions(
    request_body: CompletionRequest,
    request: Request,
    token: str = Depends(auth.verify_api_key),
) -> Any:
    """
    OpenAI-compatible /v1/completions endpoint.
    
    Handles both streaming and non-streaming requests.
    Proxies to vLLM backend with model routing.
    """
    # Apply rate limiting
    await limiter.check(request, token)
    
    # Get vLLM URL for the model
    vllm_url = proxy.get_vllm_url_for_model(request_body.model)
    
    # Build vLLM request
    vllm_payload = {
        "model": request_body.model,
        "prompt": request_body.prompt,
        "stream": request_body.stream,
    }
    
    if request_body.max_tokens is not None:
        vllm_payload["max_tokens"] = request_body.max_tokens
    if request_body.temperature is not None:
        vllm_payload["temperature"] = request_body.temperature
    
    # Forward the Bearer token to vLLM
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Build timeout settings
    timeout = httpx.Timeout(
        connect=5.0,
        read=300.0,
        write=10.0,
        pool=5.0,
    )
    
    if request_body.stream:
        # Streaming response - use SSE
        return StreamingResponse(
            proxy.proxy_stream(
                method="POST",
                url=f"{vllm_url}/v1/completions",
                headers=headers,
                json_body=vllm_payload,
                timeout=timeout,
                stream=True,
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",  # Prevent proxy buffering
            },
        )
    else:
        # Non-streaming - forward and return JSON
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{vllm_url}/v1/completions",
                headers=headers,
                json=vllm_payload,
            )
            response.raise_for_status()
            return response.json()