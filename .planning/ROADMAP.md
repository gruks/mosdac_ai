# Roadmap: Code Generation API Service

## Overview

This roadmap takes the service from zero infrastructure to a fully operational, benchmarked code generation API. Phase 1 gets a single model serving via vLLM. Phase 2 wraps it in a production API gateway with auth and multi-model routing. Phase 3 adds RAG for repository-aware completions. Phase 4 layers caching and GPU optimization. Phase 5 establishes evaluation pipelines so quality is measurable, not guessed.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Inference** — Serve code completions via vLLM with OpenAI-compatible API
- [ ] **Phase 1: Core Inference (RTX 1650)** — Serve code completions via Ollama with Qwen2.5-Coder-1.5B (adapted for 4GB VRAM)
- [ ] **Phase 2: API Gateway & Multi-Model** — FastAPI orchestration with auth, rate limiting, and model routing
- [ ] **Phase 3: RAG Pipeline** — Code-aware document ingestion, embedding, and context retrieval
- [ ] **Phase 4: Caching & Optimization** — Redis response caching, prefix caching, and GPU memory tuning
- [ ] **Phase 5: Evaluation** — HumanEval and MBPP benchmark pipelines with pass@k tracking

## Phase Details

### Phase 1: Core Inference (RTX 1650 Adaptation)
**Goal**: A developer can send a code completion request to Ollama and receive a streamed response from Qwen2.5-Coder-1.5B
**Depends on**: Nothing (first phase)
**Requirements**: INF-01, INF-02, INF-03, INF-04, INF-05
**Success Criteria** (what must be TRUE):
  1. Developer can POST to `/v1/chat/completions` and receive code completions
  2. Response streams tokens in real-time when `stream: true` is set
  3. Response includes accurate prompt + completion token counts in `usage` object
  4. `max_tokens` parameter correctly limits response length
  5. `/health` endpoint returns model status and Ollama availability
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Ollama setup with Qwen2.5-Coder-1.5B, Modelfile with 4096 context, config + pull script
- [x] 01-02-PLAN.md — FastAPI proxy with auth, streaming, health endpoint on port 8000
- [x] 01-03-PLAN.md — Smoke tests and verification scripts for all INF requirements

### Phase 2: API Gateway & Multi-Model
**Goal**: Clients authenticate with API keys and can route requests to different models with rate limiting and predictable error handling
**Depends on**: Phase 1
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06
**Success Criteria** (what must be TRUE):
  1. Requests without valid Bearer token are rejected with 401
  2. Requests exceeding rate limit receive 429 with retry-after header
  3. Client can select model via `model` parameter and get routed to correct vLLM instance
  4. Both Qwen2.5-Coder-32B and CodeLlama 70B respond to authenticated requests
  5. All error responses match OpenAI error response schema
  6. Long-running requests timeout gracefully with predictable error response
**Plans**: 3 plans
**Status**: ✓ Complete (2026-04-08)

Plans:
- [x] 02-01-PLAN.md — Foundation: project structure, config, Redis pool, logging
- [x] 02-02-PLAN.md — Auth + Rate limiting: HTTPBearer auth, slowapi+Redis rate limiting
- [x] 02-03-PLAN.md — Proxy + Routing: vLLM proxy, model registry, SSE streaming, error handling

### Phase 3: RAG Pipeline
**Goal**: Completions are enriched with relevant code snippets from the private codebase
**Depends on**: Phase 2
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04
**Success Criteria** (what must be TRUE):
  1. Code files can be ingested and split at function/class boundaries (not arbitrary text splits)
  2. FAISS vector index stores and retrieves code embeddings
  3. Completions include relevant code snippets from the codebase injected into the prompt
  4. Embeddings are cached and not recomputed on repeated ingestion of the same code
**Plans**: 3 plans
**Status**: ✓ Complete (2026-04-10)

Plans:
- [x] 03-01-PLAN.md — Semantic code chunking at function/class boundaries
- [x] 03-02-PLAN.md — FAISS vector index with embedding caching
- [x] 03-03-PLAN.md — RAG pipeline integration with completions API

### Phase 4: Caching & Optimization
**Goal**: Repeated and similar requests return faster through caching at multiple levels
**Depends on**: Phase 3
**Requirements**: CACHE-01, CACHE-02, CACHE-03
**Success Criteria** (what must be TRUE):
  1. Identical requests return cached responses from Redis without hitting the model
  2. Requests with shared system prompts benefit from vLLM prefix caching (faster subsequent requests)
  3. GPU memory utilization stays within 85-90% under sustained load
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Redis exact-match response caching
- [x] 04-02-PLAN.md — Ollama keep_alive + GPU memory tuning

### Phase 5: Evaluation
**Goal**: Model quality is measured and tracked with standardized benchmarks after every change
**Depends on**: Phase 1
**Requirements**: EVAL-01, EVAL-02, EVAL-03
**Success Criteria** (what must be TRUE):
  1. HumanEval benchmark runs end-to-end and reports pass@k score
  2. MBPP benchmark runs end-to-end and reports pass@k score
  3. pass@k metrics are automatically recorded after every model or adapter change
**Plans**: TBD

Plans:
- [ ] 05-01: HumanEval benchmark pipeline
- [ ] 05-02: MBPP benchmark pipeline
- [ ] 05-03: pass@k metric tracking and reporting

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

Note: Phase 5 (Evaluation) depends only on Phase 1 (a running model), so it can be executed in parallel with Phases 2-4 if desired.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Inference | 0/3 | Not started | - |
| 2. API Gateway & Multi-Model | 3/3 | Complete | 2026-04-08 |
| 3. RAG Pipeline | 3/3 | Complete | 2026-04-10 |
| 4. Caching & Optimization | 0/2 | Not started | - |
| 5. Evaluation | 0/3 | Not started | - |
