# Architecture Patterns

**Domain:** Code Generation API Service (private, multi-model, DGX H200)
**Researched:** 2026-04-07

## Recommended Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│              (IDE plugins, CI/CD, scripts, web UI)               │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Gateway Layer                         │
│                                                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────────┐  │
│  │   Auth &    │ │ Rate Limiter │ │    Model Router           │  │
│  │   API Keys  │ │  (Redis)     │ │  (by model/capability)    │  │
│  └──────┬──────┘ └──────┬───────┘ └──────────┬────────────────┘  │
│         │               │                     │                   │
│  ┌──────▼───────────────▼─────────────────────▼────────────────┐  │
│  │              Request Orchestrator                            │  │
│  │  • Prompt enrichment (system prompts, RAG context)          │  │
│  │ • Response caching (Redis exact-match + semantic)           │  │
│  │  • Session management (conversation state)                   │  │
│  │  • Streaming proxy (SSE passthrough)                         │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
│                             │                                     │
│  ┌──────────────────────────▼──────────────────────────────────┐  │
│  │              RAG Pipeline (LlamaIndex)                       │  │
│  │  • Document ingestion → chunking → embedding → FAISS index  │  │
│  │  • Query-time retrieval → context injection                  │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐
│   vLLM Instance 1 │ │ vLLM Instance 2│ │   vLLM Instance 3 │
│  Qwen2.5-Coder    │ │ CodeLlama 70B │ │ DeepSeek-Coder-V2 │
│  32B (2x GPU)     │ │ (4x GPU, TP=4)│ │ (4-8x GPU, TP=4-8)│
│                   │ │               │ │                   │
│  /v1/chat/        │ │ /v1/chat/     │ │ /v1/chat/         │
│  /v1/completions  │ │ /v1/completions│ │ /v1/completions   │
└────────┬──────────┘ └───────┬───────┘ └────────┬──────────┘
         │                    │                   │
         └────────────────────┼───────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │     DGX H200 (8x H200 GPUs)    │
              │  141GB HBM3e per GPU = 1.1TB  │
              │  NVLink interconnect           │
              └───────────────────────────────┘

┌───────────────────┐     ┌───────────────────┐
│     Redis 7.4     │     │ Prometheus +      │
│  • Response cache │     │     Grafana       │
│  • Rate limiting  │     │  • GPU metrics    │
│  • Session state  │     │  • Request metrics│
│  • Embedding cache│     │  • Alerts         │
└───────────────────┘     └───────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **FastAPI Gateway** | Auth, rate limiting, model routing, request orchestration, streaming proxy, RAG pipeline | Clients (HTTPS), Redis, vLLM instances, FAISS |
| **vLLM Instances** | LLM inference, token generation, OpenAI-compatible API serving | FastAPI Gateway (HTTP), GPUs (CUDA) |
| **Redis** | Response caching, rate limiting state, session storage, embedding cache | FastAPI Gateway |
| **FAISS** | Vector similarity search for RAG | FastAPI Gateway (in-process or sidecar) |
| **Prometheus** | Metrics collection from vLLM `/metrics` and FastAPI | vLLM instances, FastAPI Gateway |
| **Grafana** | Dashboards and alerting | Prometheus |

### Data Flow

**Standard code generation request:**
1. Client sends `POST /v1/chat/completions` with `model` and `messages`
2. FastAPI validates API key, checks rate limit (Redis)
3. FastAPI checks response cache (Redis exact-match on prompt hash)
4. If cache miss → Model Router selects vLLM instance based on `model` parameter
5. If RAG enabled → LlamaIndex queries FAISS, injects retrieved context into system prompt
6. Request forwarded to selected vLLM instance
7. vLLM generates tokens with PagedAttention + continuous batching
8. Response streamed back via SSE through FastAPI to client
9. Response cached in Redis (TTL-based expiry)
10. Metrics recorded to Prometheus

**RAG document ingestion (offline):**
1. Code repositories/docs ingested via LlamaIndex loaders
2. Documents chunked (code-aware chunking: respect function/class boundaries)
3. Embeddings generated via SentenceTransformers (GPU-accelerated)
4. Embeddings stored in FAISS GPU index
5. Embedding results cached in Redis to avoid re-embedding identical content

## Patterns to Follow

### Pattern 1: Thin Gateway, Fat Inference
**What:** FastAPI handles orchestration (auth, routing, caching, RAG). vLLM handles all inference. Never mix inference logic into FastAPI.
**When:** Always. This is the core architectural principle.
**Example:**
```python
# FastAPI gateway — thin orchestration only
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # 1. Auth
    validate_api_key(request.api_key)
    # 2. Rate limit
    await rate_limiter.check(request.api_key)
    # 3. Cache check
    cached = await cache.get(request.prompt_hash())
    if cached:
        return cached
    # 4. RAG enrichment
    if request.enable_rag:
        context = await rag_pipeline.retrieve(request.messages)
        request = enrich_with_context(request, context)
    # 5. Route to vLLM
    vllm_url = router.get_endpoint(request.model)
    # 6. Proxy to vLLM (streaming passthrough)
    return await proxy_to_vllm(vllm_url, request)
```

### Pattern 2: Model-per-Instance Isolation
**What:** Run each model in its own vLLM container with dedicated GPU allocation. Don't share GPUs between models.
**When:** Always for production. Prevents OOM cascades and makes scaling predictable.
**Rationale:** vLLM's tensor parallelism requires exclusive GPU access. Sharing GPUs between TP groups causes NCCL communication failures and unpredictable performance.

### Pattern 3: Embedding Cache Before Vector Search
**What:** Cache document embeddings in Redis before computing FAISS similarity. Avoid re-embedding identical documents.
**When:** Always for RAG. Embedding computation is GPU-expensive; caching saves compute.
**Example:**
```python
async def get_or_create_embedding(text: str) -> np.ndarray:
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    cached = await redis.get(f"embed:{text_hash}")
    if cached:
        return np.frombuffer(cached, dtype=np.float32)
    embedding = embedding_model.encode(text)
    await redis.set(f"embed:{text_hash}", embedding.tobytes(), ex=86400)
    return embedding
```

### Pattern 4: Prefix Caching for System Prompts
**What:** Enable vLLM's `--enable-prefix-caching` to reuse KV cache for shared system prompts across requests.
**When:** Always. Code generation uses long system prompts (instructions, style guides, RAG context) that are identical across many requests.
**Impact:** 2-5x throughput improvement when system prompts are shared.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic vLLM + FastAPI in One Process
**What goes wrong:** Running vLLM's engine directly inside FastAPI (using `LLM()` API) instead of as a separate HTTP server.
**Why bad:** vLLM's engine blocks the event loop, FastAPI can't handle concurrent requests, and you lose vLLM's built-in OpenAI API, metrics, and multi-GPU support.
**Instead:** Run vLLM as a separate process/container (`vllm serve`). FastAPI proxies to it via HTTP.

### Anti-Pattern 2: Loading All Models on All GPUs
**What goes wrong:** Trying to load CodeLlama 70B, Qwen2.5-Coder-32B, and DeepSeek-Coder-V2 simultaneously on the same GPU set.
**Why bad:** 70B model at BF16 = ~140GB. 32B model at BF16 = ~64GB. DeepSeek-Coder-V2 (MoE, 236B total) at BF16 = even more. You'll OOM immediately.
**Instead:** Partition GPUs. Example for 8x H200: GPUs 0-1 for Qwen2.5-Coder-32B, GPUs 2-5 for CodeLlama 70B, GPUs 6-7 for DeepSeek-Coder-V2 (with quantization).

### Anti-Pattern 3: Synchronous RAG in Streaming Path
**What goes wrong:** Blocking the streaming response while waiting for FAISS retrieval.
**Why bad:** Adds 100-500ms latency before first token. Users see a frozen UI.
**Instead:** Pre-fetch RAG context before starting the vLLM request. Or use async retrieval with a timeout fallback.

## Scalability Considerations

| Concern | At 10 users | At 100 users | At 1000+ users |
|---------|-------------|--------------|----------------|
| **GPU allocation** | Single model, 2-4 GPUs | Multi-model, partitioned GPUs | Multiple DGX nodes, model sharding |
| **vLLM instances** | 1 instance | 3 instances (one per model) | Multiple instances per model (data parallel) |
| **KV cache** | Default 90% GPU memory | Tuned `--gpu-memory-utilization` per model | KV cache offloading to CPU (vLLM 0.19.0 feature) |
| **Redis** | Single instance | Redis with persistence | Redis Cluster |
| **FAISS** | In-memory index in FastAPI process | Dedicated FAISS sidecar service | Distributed vector store (Milvus) |
| **Rate limiting** | Simple token bucket in Redis | Per-user quotas with burst allowance | Hierarchical rate limits (user → team → org) |
| **Observability** | Prometheus scrape + manual Grafana checks | Alerting on GPU OOM, latency spikes | Full SLO monitoring, automated scaling triggers |

## Sources

- **vLLM Architecture Overview** — https://docs.vllm.ai/en/v0.19.0/design/arch_overview/ (HIGH — official design docs)
- **vLLM Parallelism and Scaling** — https://docs.vllm.ai/en/v0.19.0/serving/parallelism_scaling/ (HIGH — official docs)
- **Building Production LLM API: FastAPI + vLLM** — https://blog.premai.io/building-a-production-llm-api-server-fastapi-vllm-complete-guide-2026/ (MEDIUM — community guide, Mar 2026)
- **LLM Gateway Pattern** — https://www.iamraghuveer.com/posts/llm-gateway-pattern-centralizing-ai-access/ (MEDIUM — architecture pattern, Mar 2026)
- **vLLM Multi-GPU Deployment 2026** — https://www.spheron.network/blog/vllm-production-deployment-2026 (MEDIUM — deployment guide, Mar 2026)
- **vLLM KV Cache Management** — https://ventusserver.com/vllm-for-large-models/ (MEDIUM — optimization guide, Jan 2026)
