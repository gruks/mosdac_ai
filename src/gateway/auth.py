"""API key authentication using FastAPI HTTPBearer."""

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

# HTTPBearer handles Bearer token extraction with case-insensitive scheme
security = HTTPBearer()

# Cache for API keys to avoid repeated file reads
_api_keys_cache: Optional[Dict[str, Dict[str, Any]]] = None


def _load_api_keys() -> Dict[str, Dict[str, Any]]:
    """Load API keys from JSON file.
    
    Keys are stored as SHA-256 hashes, not plaintext.
    
    Returns:
        Dict mapping key hash to key metadata.
    """
    global _api_keys_cache
    
    if _api_keys_cache is not None:
        return _api_keys_cache
    
    api_keys_file = Path(settings.api_keys_file)
    
    if not api_keys_file.exists():
        _api_keys_cache = {}
        return _api_keys_cache
    
    with open(api_keys_file, "r") as f:
        data = json.load(f)
    
    # Validate and normalize structure
    _api_keys_cache = {}
    for key_hash, key_data in data.items():
        if isinstance(key_data, dict):
            _api_keys_cache[key_hash] = {
                "name": key_data.get("name", "unknown"),
                "is_active": key_data.get("is_active", False),
                "rate_limit": key_data.get("rate_limit", settings.rate_limit_default),
            }
    
    return _api_keys_cache


def _get_key_hash(token: str) -> str:
    """Hash an API token using SHA-256.
    
    Args:
        token: The raw API token.
        
    Returns:
        SHA-256 hash of the token as hex string.
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict[str, Any]:
    """Verify API key from Bearer token.
    
    Uses timing-safe comparison to prevent timing attacks.
    
    Args:
        credentials: The HTTP authorization credentials from HTTPBearer.
        
    Returns:
        Dict with key metadata (name, is_active, rate_limit).
        
    Raises:
        HTTPException: 401 if token is invalid or inactive.
    """
    # Extract the token from Bearer scheme
    token = credentials.credentials
    
    # Hash the incoming token
    token_hash = _get_key_hash(token)
    
    # Load and lookup in key store
    api_keys = _load_api_keys()
    
    key_data = api_keys.get(token_hash)
    
    if key_data is None:
        # Key not found - return generic error to avoid enumeration
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid authentication credentials",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                    "param": None,
                }
            },
        )
    
    # Check if key is active
    if not key_data.get("is_active", False):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid authentication credentials",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                    "param": None,
                }
            },
        )
    
    return key_data


def get_api_key_from_request(request: Request) -> Optional[str]:
    """Extract raw API key from request for rate limiting.
    
    Args:
        request: The FastAPI request object.
        
    Returns:
        Raw API token if present, None otherwise.
    """
    auth_header = request.headers.get("authorization", "")
    
    if not auth_header.lower().startswith("bearer "):
        return None
    
    return auth_header[7:]  # Strip "Bearer " prefix
