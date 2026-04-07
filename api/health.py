import httpx
from typing import Dict, Any, List
import os


async def check_ollama_models() -> List[Dict[str, Any]]:
    """Check which models are available in Ollama."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_url}/models")
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"id": m["id"], "created": m.get("created")}
                    for m in data.get("data", [])
                ]
    except Exception:
        pass
    return []


async def get_health() -> Dict[str, Any]:
    """Get health status of the API and Ollama backend."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model_name = os.getenv("MODEL_NAME", "mosdac-coder")
    
    ollama_reachable = False
    model_loaded = False
    available_models = []
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if Ollama is reachable
            resp = await client.get(f"{ollama_url}/models")
            ollama_reachable = resp.status_code == 200
            
            if ollama_reachable:
                data = resp.json()
                available_models = [m["id"] for m in data.get("data", [])]
                model_loaded = model_name in available_models
    except Exception:
        pass
    
    # Determine status
    if not ollama_reachable:
        status = "unhealthy"
    elif not model_loaded:
        status = "degraded"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "ollama_reachable": ollama_reachable,
        "model_loaded": model_loaded,
        "model": model_name,
        "available_models": available_models,
    }