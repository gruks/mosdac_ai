# Requirements: Code Generation API Service

**Defined:** 2026-04-07
**Core Value:** Deliver high-quality, context-aware code generation through an OpenAI-compatible API that any existing tool can plug into without modification.

## v1 Requirements

### Core Inference

- [ ] **INF-01**: Service serves code completions via vLLM with OpenAI-compatible `/v1/chat/completions` endpoint
- [ ] **INF-02**: Streaming responses via SSE with `stream: true` parameter
- [ ] **INF-03**: Token counting (prompt + completion) returned in response `usage` object
- [ ] **INF-04**: Max token limits enforced via `max_tokens` parameter
- [ ] **INF-05**: Health check endpoint `/health` returning model status and GPU utilization
- [ ] **INF-06**: Qwen2.5-Coder-32B model served with tensor parallelism (TP=2)

### API Gateway

- [ ] **API-01**: API key authentication via Bearer token
- [ ] **API-02**: Rate limiting per API key using Redis token bucket
- [ ] **API-03**: Request timeout handling with predictable client behavior
- [ ] **API-04**: Error responses in OpenAI-compatible format
- [ ] **API-05**: Model selection via `model` parameter in request body
- [ ] **API-06**: Multi-model routing (Qwen2.5-Coder-32B and CodeLlama 70B)

### RAG Pipeline

- [ ] **RAG-01**: Code-aware document ingestion splitting at function/class boundaries
- [ ] **RAG-02**: FAISS vector index for codebase context retrieval
- [ ] **RAG-03**: Relevant code snippets injected into prompts for context-aware generation
- [ ] **RAG-04**: Embedding caching to avoid recomputation

### Caching & Optimization

- [ ] **CACHE-01**: Exact-match response caching via Redis
- [ ] **CACHE-02**: Prefix caching enabled in vLLM for shared system prompt reuse
- [ ] **CACHE-03**: KV cache tuning with `--gpu-memory-utilization 0.85-0.90`

### Evaluation

- [ ] **EVAL-01**: HumanEval benchmark pipeline for code generation quality
- [ ] **EVAL-02**: MBPP benchmark pipeline for code generation quality
- [ ] **EVAL-03**: pass@k metric tracking after every model/adapter change

## v2 Requirements

### Fine-Tuning Infrastructure

- **FT-01**: QLoRA fine-tuning pipeline via PEFT + bitsandbytes
- **FT-02**: LoRA adapter deployment to vLLM
- **FT-03**: LoRA adapter hot-swapping without model restart
- **FT-04**: Model quality evaluation after fine-tuning

### Advanced Features

- **ADV-01**: Semantic response caching via embedding similarity
- **ADV-02**: Structured output (JSON schema) for specific code formats
- **ADV-03**: Conversation/session management for multi-turn interactions
- **ADV-04**: Code-specific system prompt templates
- **ADV-05**: Batch API endpoint for offline processing
- **ADV-06**: Usage analytics dashboard (Prometheus + Grafana)

### Production Hardening

- **PROD-01**: Prometheus metrics export
- **PROD-02**: Grafana dashboards for GPU utilization, latency, error rates
- **PROD-03**: Alerting on KV cache utilization thresholds
- **PROD-04**: Load testing and scaling documentation
- **PROD-05**: Disaster recovery procedures

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom API protocol | Every tool expects OpenAI format; would eliminate drop-in compatibility |
| Training/fine-tuning in API service | Training and inference have different resource profiles; causes OOM and operational issues |
| Building custom vector database | FAISS is battle-tested, in-process, GPU-accelerated, zero external dependencies |
| Real-time code execution/sandbox | Security nightmare; separate product with different risk profile |
| GUI/web interface | API-only service; UI would be separate frontend consuming the API |
| LangChain as core integration | Adds latency and debugging complexity; LlamaIndex is cleaner for code-gen RAG |
| Model training from scratch | Foundation model training costs millions; fine-tuning is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INF-01 | Phase 1 | Pending |
| INF-02 | Phase 1 | Pending |
| INF-03 | Phase 1 | Pending |
| INF-04 | Phase 1 | Pending |
| INF-05 | Phase 1 | Pending |
| INF-06 | Phase 1 | Pending |
| API-01 | Phase 2 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 2 | Pending |
| API-04 | Phase 2 | Pending |
| API-05 | Phase 2 | Pending |
| API-06 | Phase 2 | Pending |
| RAG-01 | Phase 3 | Pending |
| RAG-02 | Phase 3 | Pending |
| RAG-03 | Phase 3 | Pending |
| RAG-04 | Phase 3 | Pending |
| CACHE-01 | Phase 4 | Pending |
| CACHE-02 | Phase 4 | Pending |
| CACHE-03 | Phase 4 | Pending |
| EVAL-01 | Phase 5 | Pending |
| EVAL-02 | Phase 5 | Pending |
| EVAL-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after research synthesis*
