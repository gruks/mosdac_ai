"""Pydantic models for OpenAI-compatible API request/response schemas."""

from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Single message in a chat conversation."""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Request body for /v1/chat/completions endpoint."""
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float = 0.7


class CompletionRequest(BaseModel):
    """Request body for /v1/completions endpoint."""
    model: str
    prompt: str
    stream: bool = False
    max_tokens: int | None = None
    temperature: float = 0.7


class OpenAIError(BaseModel):
    """OpenAI error response structure."""
    message: str
    type: str
    param: str | None = None
    code: str | None = None


class OpenAIErrorResponse(BaseModel):
    """Full OpenAI-compatible error response."""
    error: OpenAIError


class ModelInfo(BaseModel):
    """Information about a single model."""
    id: str
    object: str = "model"
    created: int
    owned_by: str = "gateway"


class ModelListResponse(BaseModel):
    """Response for GET /v1/models endpoint."""
    object: str = "list"
    data: list[ModelInfo]