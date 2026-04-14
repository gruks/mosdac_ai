# Feature Landscape

**Domain:** Code Generation API Service (private, multi-model, DGX H200)
**Researched:** 2026-04-07

## Table Stakes

Features users expect from a code generation API. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **OpenAI-compatible `/v1/chat/completions`** | Every LLM client library speaks this protocol. Non-negotiable for drop-in compatibility. | Low (vLLM provides natively) | vLLM v0.19.0 supports this out of the box with Chat API, Completions API, and Responses API. |
| **Streaming responses (SSE)** | Code generation produces long outputs. Users need to see tokens as they arrive, not wait for full completion. | Low (vLLM provides natively) | Server-sent events via `stream: true` parameter. Standard in all OpenAI-compatible servers. |
| **Model selection via `model` parameter** | Multi-model service must let callers choose which model to use. | Low | Route by model name in request body. vLLM handles per-model instances. |
| **API key authentication** | Private service needs access control. Even internal services need auth to prevent abuse. | Low | Bearer token auth. Can be simple token-based (no OAuth needed for private deployment). |
| **Rate limiting** | Prevents any single user from monopolizing GPU resources. Essential for multi-user environments. | Medium | Token bucket via Redis. Per-user or per-API-key limits. |
| **Request timeout handling** | LLM requests can hang. Clients need predictable timeout behavior. | Low | FastAPI timeout middleware + vLLM's built-in request timeout. |
| **Error responses in OpenAI format** | Clients expect structured error objects, not raw stack traces. | Low | vLLM returns OpenAI-compatible error format. FastAPI layer should wrap non-vLLM errors similarly. |
| **Health check endpoint** | Infrastructure needs to know if the service is alive. | Low | `/health` returning 200 with model status, GPU utilization. |
| **Token counting (prompt + completion)** | Users need to track usage. Billing, quotas, and debugging all depend on token counts. | Low (vLLM provides natively) | Included in every response's `usage` object. |
| **Max token limits** | Prevent runaway generation that wastes GPU resources. | Low | `max_tokens` parameter enforced by vLLM. |

## Differentiators

Features that set this service apart. Not expected, but highly valued for code generation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **RAG with codebase context** | Inject relevant code snippets, API docs, and patterns into prompts. Makes generated code match the project's conventions. | Medium | LlamaIndex + FAISS pipeline. Index code repos, documentation, and internal style guides. |
| **Multi-model routing** | Auto-route requests: quick tasks to Qwen2.5-Coder-32B, complex reasoning to CodeLlama 70B, MoE tasks to DeepSeek-Coder-V2. Cost/performance optimization. | Medium | FastAPI router layer inspects request complexity or uses explicit model hints. |
| **Response caching (semantic)** | Cache identical or semantically similar prompts. Saves GPU compute for repeated queries (common in code generation). | Medium | Redis with embedding-based similarity matching. FAISS for semantic lookup. |
| **LoRA adapter hot-swapping** | Load domain-specific LoRA adapters without restarting the model. Switch between "web dev", "data science", "systems programming" adapters on demand. | High | vLLM supports `--enable-lora` with `--lora-modules`. Adapters loaded at runtime. |
| **Structured output (JSON schema)** | Force code generation into specific formats (e.g., function signatures, test cases, API specs). | Low-Medium | vLLM supports `response_format: {"type": "json_schema"}` with guided decoding. |
| **Conversation/session management** | Maintain context across multiple turns for interactive code assistance. | Medium | Redis-backed session store. FastAPI manages session lifecycle. |
| **Code-specific system prompts** | Pre-configured system prompts optimized for different code generation tasks (refactoring, debugging, test generation). | Low | Template system in FastAPI layer. |
| **Prompt prefix caching** | vLLM's automatic prefix caching reuses KV cache for shared system prompts across requests. | Low (vLLM provides natively) | Enable with `--enable-prefix-caching`. Dramatic speedup for repeated system prompts. |
| **Usage analytics dashboard** | Track which models are used, token consumption, latency trends, error rates. | Medium | Prometheus metrics + Grafana dashboards. |
| **Batch API endpoint** | Submit multiple code generation requests at once for offline processing. | Low-Medium | vLLM v0.19.0 added `/v1/chat/completions/batch` natively. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Custom API protocol** | Nobody will use it. Every tool, IDE plugin, and script expects OpenAI format. | Stick to OpenAI-compatible API. Extend via `extra_body` parameters. |
| **Training/fine-tuning in the API service** | Training and inference have fundamentally different resource profiles. Mixing them causes OOM, scheduling conflicts, and operational nightmares. | Separate training pipeline. Use PEFT+TRL in a dedicated training environment, merge adapters, then deploy to inference. |
| **Building your own vector database** | FAISS, Milvus, Qdrant exist and are battle-tested. Building one is a massive time sink. | Use FAISS for private single-node. It's in-process, GPU-accelerated, and zero external dependencies. |
| **Real-time code execution/sandbox** | Security nightmare. Code execution in generated code is a separate product with its own risk profile. | Out of scope. If needed later, use a dedicated sandbox service (e.g., E2B, isolated containers). |
| **GUI/web interface** | This is an API service. A web UI is a separate product that distracts from the core API. | If needed, build as a separate frontend that consumes the API. |
| **LangChain integration as a core feature** | LangChain adds abstraction layers that increase latency and debugging complexity. For code-gen RAG, direct LlamaIndex is cleaner. | Use LlamaIndex for RAG. Keep the API layer thin. |
| **Model training from scratch** | You're building an inference service, not a model lab. Training foundation models costs millions. | Fine-tune existing models with QLoRA. Use PEFT for adapter training. |

## Feature Dependencies

```
OpenAI-compatible API → Model selection (routing requires the API layer)
Model selection → Multi-model routing (routing logic depends on having multiple models)
RAG with codebase context → FAISS vector index (RAG needs the index to exist)
RAG with codebase context → Embedding model (RAG needs embeddings for documents)
Response caching → Redis (caching needs the store)
Semantic caching → FAISS + Embedding model (semantic matching needs both)
LoRA hot-swapping → vLLM with --enable-lora (requires vLLM configured for LoRA)
Conversation management → Redis (session state needs persistent store)
Usage analytics → Prometheus + Grafana (metrics pipeline)
Structured output → vLLM guided decoding (requires vLLM 0.19.0+)
Batch API → vLLM batch endpoint (requires vLLM 0.19.0+)
```

## MVP Recommendation

Prioritize:
1. **OpenAI-compatible API** (vLLM native) — The foundation. Without this, nothing else matters.
2. **API key authentication + rate limiting** — Protect GPU resources from day one.
3. **Multi-model routing** (Qwen2.5-Coder-32B + CodeLlama 70B) — The core differentiator: right model for the right task.
4. **RAG with codebase context** — Makes generated code project-aware, not generic.
5. **Response caching** — Immediate ROI on GPU compute for repeated queries.

Defer:
- **LoRA hot-swapping**: Requires adapter training pipeline first. Add after fine-tuning infrastructure is built.
- **Batch API endpoint**: Useful but not critical for interactive code generation. Add when users request bulk processing.
- **Semantic caching**: Start with exact-match caching. Add semantic similarity once you have usage data to justify the complexity.
- **Usage analytics dashboard**: Prometheus metrics are enough initially. Build Grafana dashboards after the first month of usage data.

## Sources

- **vLLM OpenAI-Compatible Server** — https://docs.vllm.ai/en/v0.19.0/serving/openai_compatible_server/ (HIGH — official docs)
- **Building Production LLM API Server: FastAPI + vLLM** — https://blog.premai.io/building-a-production-llm-api-server-fastapi-vllm-complete-guide-2026/ (MEDIUM — community guide, Mar 2026)
- **LLM Gateway Pattern** — https://www.iamraghuveer.com/posts/llm-gateway-pattern-centralizing-ai-access/ (MEDIUM — architecture pattern, Mar 2026)
- **Model Routing in Production LLM Systems** — https://medium.com/@udayansawant/model-routing-in-production-llm-systems-be39e3650379 (MEDIUM — pattern guide, Apr 2026)
- **LLM API Gateway Patterns for Multi-Model Orchestration** — https://reintech.io/blog/llm-api-gateway-patterns-multi-model-orchestration (MEDIUM — Dec 2025)
- **API Gateway for LLMs: Rate Limiting, Cost Caps, Model Fallback** — https://markaicode.com/api-gateway-rate-limiting-fallback-models/ (MEDIUM — Mar 2026)
