"""API v1 router for /v1/models endpoint."""

import time

from fastapi import APIRouter

from src.gateway.models import ModelInfo, ModelListResponse
from src.gateway.proxy import MODEL_REGISTRY

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """
    List available models.
    
    Returns list of all models from MODEL_REGISTRY.
    No authentication required.
    """
    current_time = int(time.time())
    
    models = [
        ModelInfo(
            id=model_id,
            object="model",
            created=current_time,
            owned_by="gateway",
        )
        for model_id in MODEL_REGISTRY.keys()
    ]
    
    return ModelListResponse(
        object="list",
        data=models,
    )