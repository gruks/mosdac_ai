"""LLM Client for fine-tuned model REST API."""

import os
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0


class LLMClient:
    """Client to query fine-tuned model REST API.

    Usage:
        client = LLMClient()
        response = client.query("Your text prompt here")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initialize LLM client.

        Args:
            api_key: API key for authentication. Reads from LLM_API_KEY env var if not provided.
            base_url: Base URL for the API. Reads from LLM_API_URL env var if not provided.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LLM_API_URL", "")).rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "API key required. Set LLM_API_KEY env var or pass api_key."
            )
        if not self.base_url:
            raise ValueError(
                "Base URL required. Set LLM_API_URL env var or pass base_url."
            )

        logger.info(f"LLMClient initialized with base_url: {self.base_url}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            payload: Request payload (for POST/PUT)

        Returns:
            Parsed JSON response as dict.

        Raises:
            requests.exceptions.ConnectionError: If connection fails
            requests.exceptions.HTTPError: For HTTP error responses
            requests.exceptions.Timeout: If request times out
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Sending {method} request to {url}")

        try:
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                response = requests.request(
                    method.upper(),
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {url}: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout to {url}: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise

    def query(
        self,
        text: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send text query to LLM API.

        Args:
            text: Text prompt to send to the model.
            **kwargs: Additional parameters to pass to the API (e.g., max_tokens, temperature).

        Returns:
            JSON response from the API containing model output.
        """
        logger.info("Sending query to LLM API...")

        payload = {
            "messages": [{"role": "user", "content": text}],
            **kwargs,
        }

        response = self._make_request(
            method="POST",
            endpoint="/v1/chat/completions",
            payload=payload,
        )

        logger.info("Response received from LLM API")
        return response

    def health_check(self) -> bool:
        """Check API health status.

        Returns:
            True if API is healthy, False otherwise.
        """
        try:
            response = self._make_request(method="GET", endpoint="/health")
            return response.get("status") == "ok"
        except Exception:
            return False
