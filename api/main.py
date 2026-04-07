from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
import os

from config.settings import settings
from proxy import proxy_chat_completions
from health import get_health
from auth import verify_api_key

app = FastAPI(
    title="MOSDAC Code Generation API",
    description="OpenAI-compatible code generation API powered by Ollama",
    version="0.1.0",
)

# Set environment variables from settings
os.environ["OLLAMA_URL"] = settings.ollama_url
os.environ["MODEL_NAME"] = settings.model_name
os.environ["API_KEY"] = settings.api_key
os.environ["REQUEST_TIMEOUT"] = str(settings.request_timeout_seconds)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "MOSDAC Code Generation API",
        "version": "0.1.0",
        "model": settings.model_name,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return await get_health()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, _: bool = Depends(verify_api_key)):
    """Proxy to Ollama chat completions."""
    return await proxy_chat_completions(request)


@app.post("/v1/completions")
async def completions(request: Request, _: bool = Depends(verify_api_key)):
    """Proxy to Ollama completions (non-chat)."""
    return await proxy_chat_completions(request)


@app.get("/v1/models")
async def models(_: bool = Depends(verify_api_key)):
    """List available models."""
    from health import check_ollama_models
    models = await check_ollama_models()
    return {
        "object": "list",
        "data": [
            {
                "id": m["id"],
                "object": "model",
                "created": m.get("created", 0),
                "owned_by": "local",
            }
            for m in models
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )