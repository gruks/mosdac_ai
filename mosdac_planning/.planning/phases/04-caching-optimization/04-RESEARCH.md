# Phase 4: Caching & Optimization - Research

**Researched:** 2026-04-11
**Domain:** LLM response caching, Ollama KV cache management, GPU memory optimization
**Confidence:** MEDIUM-HIGH

## Summary

This phase implements multi-layer caching for the Ollama-backed code generation API. Three caching strategies are required: (1) Redis-based exact-match response caching for identical requests, (2) Ollama's built-in KV cache (prefix caching) via keep_alive configuration, and (3) GPU memory management to maintain 85-90% utilization. Key findings: Ollama does not natively cache response outputs—response caching must be implemented at the API gateway layer using Redis; Ollama's KV cache is automatic but controlled via `keep_alive` parameter and `OLLAMA_KEEP_ALIVE` environment variable; GPU memory tuning for consumer GPUs requires adjusting context length and layer allocation. The implementation builds on existing Redis infrastructure from Phase 2.

**Primary recommendation:** Implement exact-match response caching in the FastAPI gateway using the existing Redis client, configure Ollama keep_alive for KV cache persistence, and monitor GPU memory to maintain 85-90% utilization via nvidia-smi metrics.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| redis | 5.x | Response caching backend | Already integrated in Phase 2 |
| redis.asyncio | 5.x | Async Redis operations | Used by existing rate limiter |
| fastapi | 0.115.x | API gateway | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib | built-in | Cache key generation | For exact-match hashing |
| json | built-in | Response serialization | For caching OpenAI-format responses |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Exact-match only | RedisVL SemanticCache | Higher hit rate but more complexity; requires embedding model |
| Custom KV cache | llama.cpp proper | Ollama wraps this already; not needed |
| Separate Redis instance | Reuse Phase 2 Redis | Simplifies infrastructure; existing connection pool works |

**Installation:**
```bash
pip install redis
```
(redis is already a project dependency)

## Architecture Patterns

### Recommended Project Structure
```
src/
├── api/v1/              # Existing API endpoints
│   ├── chat.py
│   └── completions.py
├── gateway/
│   ├── main.py          # FastAPI app
│   ├── config.py        # Settings
│   └── proxy.py         # Ollama proxy
├── core/
│   ├── redis.py         # Existing Redis client
│   └── cache.py         # NEW: Response cache layer
└── services/
    └── cache_service.py # NEW: Caching business logic
```

### Pattern 1: Exact-Match Response Caching
**What:** Hash the complete request (model + messages + parameters) and store the response in Redis with TTL.
**When to use:** Identical requests (same prompt, same parameters) should return cached responses instantly.
**Example:**
```python
# Source: https://redis.io/docs/latest/develop/ai/redisvl/user_guide/llmcache/
import hashlib
import json

def generate_cache_key(messages: list, model: str, **params) -> str:
    """Generate deterministic cache key from request parameters."""
    key_data = {
        "model": model,
        "messages": messages,
        **{k: v for k, v in params.items() if v is not None}
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return f"llm:response:{hashlib.sha256(key_string.encode()).hexdigest()}"
```

**Cache key must include:**
- Model name
- Complete messages array (system + user)
- Temperature, max_tokens, and other generation parameters
- API key (for tenant isolation)

### Pattern 2: Ollama Keep-Alive for KV Cache
**What:** Configure Ollama to keep models loaded in GPU memory to reuse KV cache across requests.
**When to use:** Requests with shared system prompts benefit from pre-loaded model state.
**Example:**
```python
# Per-request keep_alive (from FastAPI to Ollama)
ollama_payload = {
    "model": "qwen2.5-coder:1.5b",
    "messages": messages,
    "keep_alive": "1h",  # Keep model loaded for 1 hour
}
```
**Server-side (environment variable):**
```bash
# In .env or systemd service
OLLAMA_KEEP_ALIVE=1h
```
**Valid values:** `"5m"` (default), `"30m"`, `"1h"`, `"24h"`, `-1` (infinite), `0` (immediate unload)

### Pattern 3: GPU Memory Monitoring
**What:** Track GPU utilization to maintain 85-90% usage under sustained load.
**When to use:** Ensuring efficient GPU memory use without OOM.
**Example:**
```python
import subprocess

def get_gpu_memory_usage() -> dict:
    """Get current GPU memory utilization."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    used, total, util = result.stdout.strip().split(",")
    return {
        "used_mb": int(used),
        "total_mb": int(total),
        "utilization_percent": int(util),
        "used_percent": int(used) / int(total) * 100
    }
```

### Anti-Patterns to Avoid
- **Semantic caching without validation gates:** Returns wrong answers for semantically similar but different queries (e.g., "refund policy for electronics" vs "refund policy for groceries")
- **Caching personalized responses without tenant isolation:** Leaks data between users when API key is not in cache key
- **TTL too long for dynamic content:** Serves stale responses when RAG context changes
- **Exact hash without normalization:** "Hello" and "hello" become different cache keys, reducing hit rate
- **Caching streaming responses naively:** Breaks SSE contract; cached full response must be streamed back character-by-character

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cache key generation | Custom hashing with edge cases | hashlib.sha256 on normalized JSON | Handles all edge cases, deterministic |
| Redis connection management | Manual connection handling | redis.asyncio with existing pool | Already implemented in src/core/redis.py |
| Semantic similarity search | Build vector index manually | RedisVL SemanticCache (if needed later) | Requires embedding model; adds complexity |
| KV cache management | Custom GPU memory tracking | Ollama built-in keep_alive | Automatic, managed by Ollama process |

**Key insight:** Ollama itself manages KV cache internally—there's no API to inspect or control it directly. The `keep_alive` parameter controls how long the model stays loaded, which indirectly controls KV cache retention. For response-level caching (bypassing the model entirely), implement at the gateway layer.

## Common Pitfalls

### Pitfall 1: Cache Key Missing Parameters
**What goes wrong:** Identical requests with different temperature/max_tokens return wrong cached responses.
**Why it happens:** Cache key only includes messages, not generation parameters.
**How to avoid:** Include all relevant parameters in cache key: temperature, max_tokens, top_p, seed.
**Warning signs:** Users report getting responses with wrong "creativity" or length.

### Pitfall 2: Cache Poisoning from Hallucinated Responses
**What goes wrong:** LLM generates incorrect response, it's cached, and future similar queries get wrong answer.
**Why it happens:** No validation before caching—any response is stored.
**How to avoid:** For high-risk responses, implement validation gate before caching. For code generation, at minimum validate JSON syntax if format is expected.
**Warning signs:** Increasing support tickets for "wrong answers" after cache warms.

### Pitfall 3: Semantic Caching False Positives
**What goes wrong:** Queries embed similarly but need different answers (e.g., "electronics refund" vs "grocery refund").
**Why it happens:** Cosine similarity threshold too low (below 0.90).
**How to avoid:** Start with threshold 0.95, monitor quality, adjust conservatively. Disable semantic caching for ambiguous domains.
**Warning signs:** Users report getting irrelevant code completions.

### Pitfall 4: GPU OOM from Concurrent Requests
**What goes wrong:** Multiple concurrent requests cause KV cache to grow beyond available memory, triggering OOM or eviction.
**Why it happens:** No limit on concurrent requests; each request allocates KV cache.
**How to avoid:** Set `OLLAMA_NUM_PARALLEL` environment variable to limit concurrent requests (e.g., 2-4 for 4GB GPU).
**Warning signs:** "failed to find a kv cache slot" errors in Ollama logs.

### Pitfall 5: Streaming Cache Hits
**What goes wrong:** Cached response returned but client expects SSE stream—the cached text is sent all at once.
**Why it happens:** Naive cache implementation returns full response; streaming requires token-by-token replay.
**How to avoid:** Store cache entries as list of tokens; on cache hit, stream tokens individually to maintain SSE contract.
**Warning signs:** Clients report missing `data: [DONE]` message or malformed stream.

## Code Examples

Verified patterns from official sources:

### Redis Exact-Match Caching
```python
# Source: https://redis.io/docs/latest/develop/ai/langcache (adapted for self-managed)
import hashlib
import json
import redis.asyncio as redis

class ResponseCache:
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl

    def _make_key(self, request_data: dict) -> str:
        """Generate cache key from normalized request."""
        normalized = json.dumps(request_data, sort_keys=True)
        return f"llm:resp:{hashlib.sha256(normalized.encode()).hexdigest()}"

    async def get(self, request_data: dict) -> str | None:
        """Get cached response if exists."""
        key = self._make_key(request_data)
        return await self.redis.get(key)

    async def set(self, request_data: dict, response: str) -> None:
        """Store response with TTL."""
        key = self._make_key(request_data)
        await self.redis.setex(key, self.ttl, response)

# Usage in FastAPI endpoint
cache = ResponseCache(redis_client, ttl=3600)

async def chat_completion(request: CompletionRequest):
    cache_key = {"model": request.model, "messages": [m.dict() for m in request.messages]}
    
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return json.loads(cached)  # Return cached OpenAI response
    
    # Call Ollama, cache result
    response = await call_ollama(request)
    await cache.set(cache_key, json.dumps(response))
    return response
```

### Ollama Keep-Alive Configuration
```python
# Source: https://docs.ollama.com/api/generate (keep_alive parameter)
import httpx

async def call_ollama_with_cache(model: str, messages: list, keep_alive: str = "1h"):
    """Call Ollama with keep_alive to maintain KV cache."""
    payload = {
        "model": model,
        "messages": messages,
        "keep_alive": keep_alive,  # "30m", "1h", "-1" for infinite
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:11434/api/chat", json=payload)
        return response.json()
```

### Multi-Tier Cache Flow
```python
# Source: https://redis.io/blog/what-is-prompt-caching/ (architecture pattern)
async def cached_completion(request: CompletionRequest) -> dict:
    """Three-tier caching: exact → Ollama KV → fresh inference."""
    
    # Tier 1: Exact-match response cache (bypasses model entirely)
    cache_key = build_cache_key(request)
    cached = await redis_cache.get(cache_key)
    if cached:
        metrics.inc("cache.exact_hit")
        return parse_cached_response(cached)
    
    # Tier 2: Ollama KV cache (via keep_alive, model still generates output)
    # Model stays loaded, processes shared prefix faster
    response = await ollama_chat(request, keep_alive="1h")
    
    # Store in Tier 1 for next exact match
    await redis_cache.set(cache_key, serialize_response(response))
    metrics.inc("cache.miss")
    return response
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No response caching | Exact-match Redis caching | 2024+ | 15-30% hit rate for repeated queries |
| Prompt reprocessing every request | Ollama KV cache via keep_alive | Ollama 0.1+ | 40-60% faster for follow-up in same conversation |
| Semantic vs exact caching debate | Multi-tier approach | 2025+ | Combines benefits; exact first for safety, semantic for hit rate |
| Single TTL for all responses | Content-aware TTL | 2025+ | Short TTL for dynamic content, long for static |

**Deprecated/outdated:**
- GPTCache: Early semantic caching tool; RedisVL supersedes it with better vector search
- SQLite-backed caches: Inadequate for production; Redis handles concurrent access better
- Prompt caching via custom middle layer: Now built into major LLM providers (Anthropic, OpenAI); Ollama handles via KV cache

## Open Questions

1. **Should semantic caching be implemented now or later?**
   - What we know: Exact-match caching covers CACHE-01 requirement. Semantic caching increases hit rate but adds complexity.
   - What's unclear: Whether the codebase has enough repeated-but-rephrased queries to justify embedding model overhead.
   - Recommendation: Implement exact-match first (CACHE-01), defer semantic to Phase 4.2 if hit rate is insufficient.

2. **What TTL value is appropriate for code generation responses?**
   - What we know: Code completions don't have the staleness issues of real-time data (pricing, inventory).
   - What's unclear: How often does the codebase context change? If RAG updates, cached completions referencing old context become stale.
   - Recommendation: Start with 1 hour TTL; add cache invalidation when RAG index updates.

3. **How to handle streaming cache hits correctly?**
   - What we know: Streaming requires SSE format with `data: [DONE]` terminator.
   - What's unclear: Whether to cache tokenized stream or replay from stored full response.
   - Recommendation: Store full response, replay as stream on cache hit—this maintains SSE contract.

## Sources

### Primary (HIGH confidence)
- https://docs.ollama.com/api/generate — Ollama API, keep_alive parameter documentation
- https://docs.ollama.com/faq — Ollama server configuration, OLLAMA_KEEP_ALIVE
- https://redis.io/docs/latest/develop/ai/redisvl/user_guide/llmcache/ — RedisVL SemanticCache API

### Secondary (MEDIUM confidence)
- https://redis.io/blog/what-is-prompt-caching/ — Multi-tier caching architecture
- https://markaicode.com/ollama-caching-strategies-improve-repeat-query-performance/ — Ollama caching patterns
- https://amitkoth.com/llm-caching-strategies/ — Response caching pitfalls

### Tertiary (LOW confidence)
- https://vipinpg.com/blog/implementing-llm-response-caching-with-redis/ — Redis + Ollama semantic caching (requires verification)
- https://tianpan.co/blog/2026-04-09-semantic-caching-llm-production — Production hit rate benchmarks (20-45%)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Uses existing Redis infrastructure from Phase 2
- Architecture: HIGH — Patterns verified from Ollama docs and Redis documentation
- Pitfalls: MEDIUM — Documented from production case studies; some are specific to semantic caching which is optional

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days — caching strategies are relatively stable)