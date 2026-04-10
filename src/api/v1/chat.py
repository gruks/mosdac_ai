"""API v1 router for /v1/chat/completions endpoint."""

import logging
import os
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from src.gateway import auth, proxy
from src.gateway.models import ChatCompletionRequest
from src.gateway.rate_limiter import limiter
from src.rag.index import CodeIndex
from src.rag.ingest import split_directory
from src.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

# Global RAG index stored in app state
_rag_index: Optional[CodeIndex] = None


def get_rag_index() -> Optional[CodeIndex]:
    """Get or build the RAG index."""
    global _rag_index

    if _rag_index is not None:
        return _rag_index

    # Try to load from cache
    cache_path = ".rag_cache/index.faiss"
    if os.path.exists(cache_path):
        try:
            _rag_index = CodeIndex()
            _rag_index.load_index(cache_path)
            logger.info("Loaded RAG index from cache")
            return _rag_index
        except Exception as e:
            logger.warning(f"Failed to load cached index: {e}")

    # Build index from src/ directory
    try:
        chunks = split_directory("src")
        _rag_index = CodeIndex()
        _rag_index.build_index(chunks)

        # Save to cache
        os.makedirs(".rag_cache", exist_ok=True)
        _rag_index.save_index(".rag_cache/index.faiss")
        logger.info(f"Built RAG index with {len(chunks)} chunks")
        return _rag_index
    except Exception as e:
        logger.error(f"Failed to build RAG index: {e}")
        return None


@router.post("/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    request: Request,
    token: str = Depends(auth.verify_api_key),
    enable_rag: bool = Query(False, description="Enable RAG context enrichment"),
) -> Any:
    """
    OpenAI-compatible /v1/chat/completions endpoint.

    Handles both streaming and non-streaming requests.
    Proxies to vLLM backend with model routing.

    Args:
        enable_rag: If True, retrieve relevant code context and inject into prompt
    """
    # Apply rate limiting
    await limiter.check(request, token)

    # Get messages - potentially enriched with RAG context
    messages = [msg.model_dump() for msg in request_body.messages]

    # RAG enrichment
    if enable_rag:
        rag_index = get_rag_index()
        if rag_index is not None:
            # Extract user message for context retrieval
            user_msg = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_msg = msg.get("content", "")
                    break

            if user_msg:
                # Retrieve relevant context
                rag_pipeline = RAGPipeline(rag_index, top_k=3)
                context = rag_pipeline.retrieve_context(user_msg)

                if context:
                    # Build enriched prompt
                    enriched_user = rag_pipeline.build_enriched_prompt(
                        messages, context
                    )

                    # Replace user message with enriched version
                    for msg in messages:
                        if msg.get("role") == "user":
                            msg["content"] = enriched_user
                            break

                    logger.info(f"Enriched prompt with {len(context)} code chunks")

    # Get vLLM URL for the model
    vllm_url = proxy.get_vllm_url_for_model(request_body.model)

    # Build vLLM request - use modified messages (potentially enriched)
    vllm_payload = {
        "model": request_body.model,
        "messages": messages,
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
                url=f"{vllm_url}/v1/chat/completions",
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
                f"{vllm_url}/v1/chat/completions",
                headers=headers,
                json=vllm_payload,
            )
            response.raise_for_status()
            return response.json()
