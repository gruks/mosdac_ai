# Phase 2: API Gateway & Multi-Model - Research

**Researched:** 2026-04-07
**Domain:** FastAPI API gateway, authentication, rate limiting, vLLM proxying
**Confidence:** HIGH

## Summary

Phase 2 builds a FastAPI gateway that sits between clients and multiple vLLM inference backends. The gateway handles API key authentication (Bearer token), per-key rate limiting via Redis token bucket, request timeout management, model routing, and OpenAI-compatible error responses. This is a well-solved problem space with mature libraries for every component.

The architecture is a thin proxy layer: authenticate → rate limit → route to correct vLLM instance → stream response back to client. The key complexity is proxying Server-Sent Events (SSE) streams from vLLM while maintaining connection integrity, handling timeouts, and preserving OpenAI-compatible error schemas.

**Primary recommendation:** Use `slowapi` + Redis for rate limiting, `httpx.AsyncClient` for proxying to vLLM backends, FastAPI dependency injection for auth, and `StreamingResponse` for SSE passthrough.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | >=0.115.x | API framework | Async-native, dependency injection, OpenAPI schema generation |
| `uvicorn` | >=0.34.x | ASGI server | Production-grade, supports HTTP/2, worker management |
| `httpx` | >=0.28.x | Async HTTP client for proxying | Native async, streaming support, timeout handling |
| `slowapi` | >=0.1.9 | Rate limiting middleware | FastAPI-native, Redis backend, per-key limits |
| `redis` (redis-py) | >=5.2.x | Redis client for rate limiting + caching | Official client, async support, well-maintained |
| `pydantic` | >=2.x | Request/response validation | Built into FastAPI, type safety |
| `python-multipart` | >=0.0.18 | Form data parsing | Required by FastAPI for request body parsing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `passlib[bcrypt]` | >=1.7.4 | API key hashing | Store hashed keys, not plaintext |
| `python-dotenv` | >=1.0.1 | Environment config | Local development, secrets management |
| `structlog` or `loguru` | latest | Structured logging | Production observability |
| `prometheus-client` | >=0.21.x | Metrics | GPU utilization, TTFT, queue depth |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `slowapi` | `limits` library directly | `limits` is the engine `slowapi` wraps; `slowapi` adds FastAPI integration |
| `slowapi` | Custom Redis token bucket | More control but reinvents well-tested logic |
| `httpx` | `aiohttp` | `httpx` has better typing, modern API, built-in timeout types |
| `passlib` | `hashlib` directly | `passlib` handles salting, algorithm upgrades, timing-safe comparison |

**Installation:**
```bash
pip install fastapi uvicorn[standard] httpx slowapi redis pydantic python-multipart passlib[bcrypt] python-dotenv
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── gateway/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry, middleware registration
│   ├── config.py            # Settings via pydantic-settings
│   ├── auth.py              # API key verification dependency
│   ├── rate_limiter.py      # Slowapi + Redis configuration
│   ├── models.py            # Pydantic request/response schemas
│   ├── errors.py            # OpenAI-compatible error handlers
│   └── proxy.py             # vLLM request forwarding + streaming
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── chat.py          # /v1/chat/completions endpoint
│   │   ├── completions.py   # /v1/completions endpoint
│   │   └── models.py        # /v1/models endpoint
├── core/
│   ├── __init__.py
│   ├── redis.py             # Redis connection pool
│   └── logging.py           # Structured logging setup
└── tests/
    ├── test_auth.py
    ├── test_rate_limit.py
    ├── test_proxy.py
    └── test_errors.py
```

### Pattern 1: FastAPI Dependency Injection for Auth
**What:** Use `Depends()` to extract and validate API keys from Bearer tokens before route handlers execute.
**When to use:** Every protected route. This is the FastAPI-standard pattern.
**Example:**
```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import hashlib

security = HTTPBearer()

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """Validate Bearer token and return API key metadata."""
    key_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    api_key = await db.get_api_key_by_hash(key_hash)
    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid authentication credentials",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                    "param": None
                }
            }
        )
    return api_key
```
Source: FastAPI security docs (https://fastapi.tiangolo.com/tutorial/security/)

### Pattern 2: SlowAPI + Redis Rate Limiting
**What:** Use `slowapi` with a `RedisStorage` backend for distributed per-key rate limiting with token bucket algorithm.
**When to use:** Per-API-key rate limits that must be consistent across multiple gateway instances.
**Example:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.storage import RedisStorage
import redis

redis_client = redis.Redis(host="localhost", port=6379, db=0)
storage = RedisStorage(redis_client)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    strategy="moving-window",  # or "fixed-window-elastic-expiry"
)
```
Source: slowapi docs (https://slowapi.readthedocs.io/)

### Pattern 3: SSE Streaming Proxy to vLLM
**What:** Forward requests to vLLM using `httpx.AsyncClient.stream()` and yield SSE events back to the client via `StreamingResponse`.
**When to use:** Any endpoint that proxies streaming LLM responses.
**Example:**
```python
from fastapi.responses import StreamingResponse
import httpx

async def proxy_stream(method, url, headers, json_body, timeout):
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(method, url, headers=headers, json=json_body) as response:
            async for chunk in response.aiter_text():
                yield chunk

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, api_key=Depends(verify_api_key)):
    vllm_url = get_vllm_url_for_model(request.model)
    return StreamingResponse(
        proxy_stream("POST", f"{vllm_url}/v1/chat/completions", ...),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )
```
Source: httpx streaming docs (https://www.python-httpx.org/advanced/streaming/)

### Pattern 4: Model Routing via Registry
**What:** Maintain a model-to-vLLM-instance mapping. Route requests based on the `model` parameter in the request body.
**When to use:** Multi-model deployments where different models run on different vLLM instances.
**Example:**
```python
MODEL_REGISTRY = {
    "Qwen/Qwen2.5-Coder-32B-Instruct": "http://vllm-qwen:8000",
    "codellama/CodeLlama-70b-Instruct-hf": "http://vllm-codellama:8001",
}

def get_vllm_url_for_model(model: str) -> str:
    if model not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": f"Model '{model}' not found", "type": "invalid_request_error", "code": "model_not_found", "param": "model"}}
        )
    return MODEL_REGISTRY[model]
```

### Anti-Patterns to Avoid
- **Sync HTTP calls in async routes:** Using `requests` instead of `httpx` blocks the event loop, serializing all requests.
- **In-memory rate limiting:** Dict-based rate limiters don't share state across workers/instances. Use Redis.
- **Forking vLLM's server:** Modifying vLLM's built-in server creates merge conflicts on updates. Use it as a backend, not a base.
- **Buffering streaming responses:** Reading the full response before returning defeats streaming. Use `httpx.stream()` + `StreamingResponse`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key auth from Bearer header | Custom header parsing | `fastapi.security.HTTPBearer` + `Depends()` | Handles edge cases (missing header, malformed token, scheme case) |
| Rate limiting with Redis | Custom Lua scripts | `slowapi` with Redis storage | Tested token/sliding window algorithms, Retry-After headers, decorator + middleware patterns |
| HTTP timeout handling | Manual `asyncio.wait_for()` | `httpx.Timeout()` | Connect, read, write, pool timeouts handled separately; proper cancellation |
| OpenAI error schema | Custom JSON dict | Pydantic model matching OpenAI schema | Type safety, consistent format, easy to extend |
| SSE streaming proxy | Manual chunk reading | `httpx.AsyncClient.stream()` + `StreamingResponse` | Proper connection lifecycle, chunked transfer encoding, client disconnect detection |
| API key hashing | `hashlib.sha256()` alone | `passlib` with bcrypt | Salt management, timing-safe comparison, algorithm migration |
| Configuration | `os.environ` scattered | `pydantic-settings` | Type validation, defaults, env file support, nested config |

**Key insight:** Every component in this stack has deceptively complex edge cases. Token bucket refill timing, SSE connection drops, Bearer token parsing, Redis connection pooling — all solved better by established libraries.

## Common Pitfalls

### Pitfall 1: Streaming Response Buffering
**What goes wrong:** Reverse proxies (nginx, traefik) and even some middleware buffer streaming responses, sending all data at once instead of token-by-token.
**Why it happens:** Default proxy buffering behavior. HTTP proxies accumulate response body before forwarding.
**How to avoid:** Set `X-Accel-Buffering: no` header on streaming responses. Configure upstream proxies to disable buffering for SSE paths.
**Warning signs:** Client sees no output until generation completes, defeating streaming purpose.

### Pitfall 2: Client Disconnect Not Detected
**What goes wrong:** When a client closes the connection mid-stream, vLLM continues generating tokens, wasting GPU cycles.
**Why it happens:** The proxy doesn't check if the client is still connected during streaming.
**How to avoid:** Check `request.is_disconnected()` periodically during streaming. Cancel the vLLM generation when the client disconnects.
**Warning signs:** GPU utilization stays high even when clients have disconnected.

### Pitfall 3: Rate Limit State Lost Across Workers
**What goes wrong:** Using in-memory rate limiting with multiple Uvicorn workers means each worker tracks its own counters.
**Why it happens:** Uvicorn spawns separate processes; memory is not shared.
**How to avoid:** Use Redis-backed rate limiting (slowapi with RedisStorage). Every worker reads/writes to the same Redis instance.
**Warning signs:** Rate limits appear to work with 1 worker but are ineffective with multiple workers.

### Pitfall 4: Timeout Not Propagated to Client
**What goes wrong:** When a request times out, the client receives a generic 500 or hangs indefinitely instead of a structured error.
**Why it happens:** `asyncio.TimeoutError` or `httpx.ReadTimeout` is not caught and converted to an OpenAI-compatible error response.
**How to avoid:** Wrap proxy calls in try/except for `httpx.TimeoutException`. Return 504 with OpenAI error schema.
**Warning signs:** Clients hang for 60+ seconds on long generations with no feedback.

### Pitfall 5: Model Parameter Not Validated Before Routing
**What goes wrong:** Invalid model names reach vLLM backend, which returns its own error format (not OpenAI-compatible).
**Why it happens:** The gateway passes the `model` parameter through without validating it against the registry.
**How to avoid:** Validate `model` against the MODEL_REGISTRY before forwarding. Return 400 with OpenAI error schema for unknown models.
**Warning signs:** Clients receive raw vLLM error JSON instead of gateway-formatted errors.

### Pitfall 6: SSE Error Mid-Stream
**What goes wrong:** If an error occurs after streaming has started, you can't change the HTTP status code. The client receives partial data with no error indication.
**Why it happens:** HTTP headers are sent before the body. Once streaming starts, status code is locked.
**How to avoid:** Send error events in the SSE stream format: `data: {"error": {...}}\n\n`. Document this behavior for clients.
**Warning signs:** Clients receive truncated responses with no error indication.

### Pitfall 7: Bearer Token Scheme Case Sensitivity
**What goes wrong:** Some clients send `bearer` (lowercase) instead of `Bearer`. Custom parsing rejects valid tokens.
**Why it happens:** String comparison is case-sensitive.
**How to avoid:** Use `HTTPBearer` from FastAPI which handles scheme normalization. If custom parsing, use case-insensitive comparison.
**Warning signs:** Some valid API keys are rejected with 401.

## Code Examples

### OpenAI-Compatible Error Response
```python
from pydantic import BaseModel
from typing import Optional

class OpenAIError(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None

class OpenAIErrorResponse(BaseModel):
    error: OpenAIError

# Usage in exception handler:
@app.exception_handler(HTTPException)
async def openai_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=OpenAIErrorResponse(
            error=OpenAIError(
                message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                type="invalid_request_error",
                code=get_error_code(exc.status_code),
            )
        ).model_dump(),
    )

def get_error_code(status_code: int) -> str:
    return {
        400: "invalid_request_error",
        401: "invalid_api_key",
        403: "permission_error",
        404: "not_found",
        429: "rate_limit_exceeded",
        500: "server_error",
        503: "service_unavailable",
        504: "request_timeout",
    }.get(status_code, "api_error")
```

### Request Timeout Handling
```python
import httpx

# Configure timeouts per operation
DEFAULT_TIMEOUT = httpx.Timeout(
    connect=5.0,      # Connection to vLLM
    read=300.0,       # Time to read streaming response (5 min for long generations)
    write=10.0,       # Time to send request body
    pool=5.0,         # Time waiting for connection from pool
)

async def proxy_with_timeout(method, url, headers, json_body):
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            async with client.stream(method, url, headers=headers, json=json_body) as resp:
                async for chunk in resp.aiter_text():
                    yield chunk
    except httpx.ConnectTimeout:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="Request timed out during generation")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timed out")
```

### Per-Key Rate Limiting with SlowAPI
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function that extracts API key identity
def get_api_key_identifier(request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]  # Return the raw token for rate limiting
    return request.client.host

limiter = Limiter(
    key_func=get_api_key_identifier,
    storage_uri="redis://localhost:6379",
    default_limits=["100/minute"],
)

@app.post("/v1/chat/completions")
@limiter.limit("60/minute")  # Override default for this endpoint
async def chat_completions(request: Request, ...):
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync Flask + gunicorn | Async FastAPI + uvicorn | 2022+ | Native streaming, better concurrency |
| Custom rate limiter dicts | `slowapi` + Redis backend | 2023+ | Distributed, multi-worker safe |
| `requests` for proxying | `httpx.AsyncClient.stream()` | 2023+ | Non-blocking, proper timeout handling |
| Manual error JSON | Pydantic models matching OpenAI schema | 2024+ | Type safety, consistent format |
| vLLM server forked | vLLM as backend, FastAPI as gateway | 2024+ | Clean separation, easy updates |

**Deprecated/outdated:**
- `starlette-limiter`: Superseded by `slowapi` which has active maintenance
- `flask-limiter`: Flask-based, not compatible with async FastAPI
- Manual `aiohttp` proxying: `httpx` provides better typing and timeout types

## Open Questions

1. **CodeLlama 70B GPU requirements**
   - What we know: CodeLlama 70B requires significant GPU memory (~140GB for FP16)
   - What's unclear: Exact vLLM configuration (TP size, quantization) for the available hardware
   - Recommendation: Validate hardware specs during Phase 1; Phase 2 assumes vLLM instance is already running

2. **API key storage backend**
   - What we know: Keys need to be stored hashed, looked up per request
   - What's unclear: Whether to use a file-based store, SQLite, or full database for Phase 2
   - Recommendation: Start with a simple JSON/YAML file or SQLite for Phase 2; can migrate to PostgreSQL later

3. **Rate limit tiers per API key**
   - What we know: Different keys may need different limits
   - What's unclear: Whether Phase 2 needs tier support or uniform limits
   - Recommendation: Implement uniform limits first; tier support is a Phase 3+ concern

4. **vLLM instance health checking**
   - What we know: Model routing needs to know which vLLM instances are alive
   - What's unclear: Whether to implement active health checks or assume instances are always up
   - Recommendation: Start with static registry; add health checks if needed

## Sources

### Primary (HIGH confidence)
- FastAPI security docs (https://fastapi.tiangolo.com/tutorial/security/) - HTTPBearer, dependency injection patterns
- httpx streaming docs (https://www.python-httpx.org/advanced/streaming/) - AsyncClient.stream(), SSE handling
- slowapi docs (https://slowapi.readthedocs.io/) - Redis storage, decorator patterns, rate limit strategies
- vLLM OpenAI-compatible server docs (https://docs.vllm.ai/en/stable/serving/openai_compatible_server/) - API endpoints, streaming format
- OpenAI API reference (https://platform.openai.com/docs/api-reference/overview) - Bearer auth, error schema, rate limit headers
- FreeCodeCamp token bucket guide (https://www.freecodecamp.org/news/token-bucket-rate-limiting-fastapi/) - Token bucket implementation with FastAPI middleware

### Secondary (MEDIUM confidence)
- Prem AI blog: "Building a Production LLM API Server: FastAPI + vLLM Complete Guide (2026)" (https://blog.premai.io/building-a-production-llm-api-server-fastapi-vllm-complete-guide-2026/) - Architecture patterns, token-aware rate limiting, SSE gotchas
- OneUptime: "How to Implement FastAPI Rate Limiting with Redis" (https://oneuptime.com/blog/post/2026-03-31-redis-fastapi-rate-limiting/view) - Redis rate limiting patterns
- OneUptime: "How to Implement vLLM with OpenAI-Compatible API" (https://oneuptime.com/blog/post/2026-01-28-vllm-openai-compatible-api/view) - vLLM proxy patterns

### Tertiary (LOW confidence)
- Various Medium articles on FastAPI rate limiting - Need verification against slowapi official docs
- Reddit discussion on vLLM model selection (https://www.reddit.com/r/mlops/comments/1okosuq/) - Community patterns, not official guidance

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are well-documented, actively maintained, and widely used in production
- Architecture: HIGH - FastAPI gateway pattern is well-established; patterns verified against official docs and recent production guides
- Pitfalls: HIGH - All pitfalls are from verified sources (production guides, official docs, Stack Overflow issues)
- Open questions: MEDIUM - Hardware-specific decisions depend on Phase 1 outcomes

**Research date:** 2026-04-07
**Valid until:** 2026-07-07 (stable libraries, 90-day validity)
