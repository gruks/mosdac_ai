from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import os
import json
from typing import AsyncGenerator


async def proxy_chat_completions(request: Request) -> StreamingResponse | dict:
    """Proxy chat completion requests to Ollama, handling streaming."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model_name = os.getenv("MODEL_NAME", "mosdac-coder")
    
    # Get request body
    body = await request.json()
    
    # Force our model (server-side override)
    body["model"] = model_name
    
    # Check for streaming
    is_streaming = body.get("stream", False)
    
    timeout = float(os.getenv("REQUEST_TIMEOUT", "120.0"))
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        if is_streaming:
            # Proxy streaming response
            async def generate() -> AsyncGenerator[str, None]:
                async with client.stream(
                    "POST",
                    f"{ollama_url}/chat/completions",
                    json=body,
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=error_body.decode()
                        )
                    
                    async for chunk in response.aiter_text():
                        yield chunk
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                }
            )
        else:
            # Non-streaming response
            resp = await client.post(
                f"{ollama_url}/chat/completions",
                json=body
            )
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=resp.text
                )
            
            return resp.json()