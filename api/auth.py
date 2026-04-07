from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os

security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> bool:
    """Verify API key from Authorization header."""
    if not credentials:
        # For development, allow requests without auth (toggle with env var)
        if os.getenv("REQUIRE_AUTH", "false").lower() == "false":
            return True
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    expected_key = os.getenv("API_KEY", "dev-key-123")
    if credentials.credentials != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True