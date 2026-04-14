"""LLM client module for fine-tuned model REST API.

Usage:
    from src.llm import LLMClient

    client = LLMClient(
        api_key="your-api-key",
        base_url="http://localhost:8000"
    )

    response = client.query("Your text prompt here")
"""

from .client import LLMClient

__all__ = ["LLMClient"]
