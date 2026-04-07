# Research Summary: Code Generation API Service

**Domain:** Private multi-model LLM inference API for code generation on DGX H200
**Researched:** 2026-04-07
**Overall confidence:** HIGH

## Executive Summary

The standard 2025-2026 stack for a code generation API service is well-established and mature. **vLLM v0.19.0** (released April 2026) is the undisputed inference engine — it provides native OpenAI-compatible APIs, PagedAttention memory management, continuous batching, and explicit support for all three target models (DeepSeek-Coder-V2 with MLA attention, Qwen2.5-Coder-32B, CodeLlama 70B). The ecosystem has converged on a clear separation: vLLM handles inference, FastAPI handles orchestration (auth, routing, caching, RAG), and Redis provides state management.

The DGX H200's 141GB HBM3e per GPU (8 GPUs = 1.1TB total with NVLink) is well-suited for this workload. The key architectural decision is **GPU partitioning**: each model gets dedicated GPUs with tensor parallelism, never shared. CodeLlama 70B needs TP=4 (~140GB BF16 weights), Qwen2.5-Coder-32B needs TP=2 (~64GB), and DeepSeek-Coder-V2 (MoE, 236B total / 21B active) needs TP=4-8 depending on quantization.

For RAG, the standard pattern is LlamaIndex (orchestration) + FAISS (vector search, GPU-accelerated via cuVS) + SentenceTransformers (embeddings). This is an in-process stack with zero external database dependencies — ideal for private deployment. For fine-tuning, PEFT 0.18.1 + bitsandbytes (QLoRA) + TRL is the standard, achieving 90-95% of full fine-tuning quality at 25% of the memory cost.

The most critical risk is **GPU memory management**: miscalculating KV cache requirements leads to OOM cascades that take down entire model instances. The second biggest risk is **DeepSeek-Coder-V2's MLA architecture**, which has different memory characteristics than standard attention and requires careful context length tuning.

## Key Findings

**Stack:** vLLM 0.19.0 + FastAPI 0.130 + Redis 7.4 + LlamaIndex 0.14.9 + FAISS 1.14.0 + PEFT 0.18.1 — all verified as current releases with official sources.

**Architecture:** Thin FastAPI gateway (auth, routing, RAG, caching) proxies to separate vLLM instances per model. GPU partitioning with tensor parallelism. No shared GPUs between models.

**Critical pitfall:** GPU memory miscalculation → OOM cascades. Model weights are only ~50% of memory usage; KV cache, activations, CUDA graphs, and NCCL buffers consume the rest.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Core Inference Foundation** — Get one model serving via vLLM with OpenAI-compatible API
   - Addresses: OpenAI-compatible API, streaming, health checks, token counting
   - Avoids: Multi-model complexity, RAG, fine-tuning — focus on getting inference right first
   - Key decision: Start with Qwen2.5-Coder-32B (simplest: TP=2, fits on 2 GPUs, fastest to validate)

2. **Phase 2: API Gateway & Multi-Model** — Add FastAPI orchestration layer with auth, rate limiting, and model routing
   - Addresses: API key auth, rate limiting, model selection, multi-model routing, error handling
   - Avoids: RAG pipeline — add routing before adding context retrieval
   - Key decision: One vLLM instance per model, dedicated GPU allocation per instance

3. **Phase 3: RAG Pipeline** — Add code-aware document ingestion, embedding, and retrieval
   - Addresses: RAG with codebase context, FAISS vector index, embedding caching, code-aware chunking
   - Avoids: Semantic caching (start with exact-match first)
   - Key decision: Code-aware chunking (split at function/class boundaries, not arbitrary text splits)

4. **Phase 4: Response Caching & Optimization** — Add Redis caching, prefix caching, and performance tuning
   - Addresses: Response caching, prefix caching, KV cache tuning, observability
   - Avoids: Fine-tuning — optimize inference before investing in model customization
   - Key decision: Enable `--enable-prefix-caching` in vLLM for shared system prompt reuse

5. **Phase 5: Fine-Tuning Infrastructure** — Add QLoRA training pipeline and LoRA adapter management
   - Addresses: PEFT + bitsandbytes fine-tuning, LoRA adapter deployment, model quality evaluation
   - Avoids: Training from scratch — only parameter-efficient fine-tuning
   - Key decision: Separate training environment from inference. Merge adapters before deploying to vLLM.

6. **Phase 6: Production Hardening** — Observability, monitoring, alerting, and scaling
   - Addresses: Prometheus metrics, Grafana dashboards, alerting, load testing, disaster recovery
   - Key decision: Monitor KV cache utilization as the primary health metric

**Phase ordering rationale:**
- Inference must work before orchestration makes sense (Phase 1 → Phase 2)
- Routing must exist before RAG context can be model-aware (Phase 2 → Phase 3)
- Caching builds on RAG (cached responses include RAG context) (Phase 3 → Phase 4)
- Fine-tuning requires a stable inference baseline to evaluate adapter quality (Phase 4 → Phase 5)
- Production hardening is last because you need real usage data to tune alerts and SLOs (Phase 5 → Phase 6)

**Research flags for phases:**
- Phase 1: Standard vLLM setup, unlikely to need deep research. vLLM docs are comprehensive.
- Phase 2: Standard API gateway patterns. Well-documented in 2026 literature.
- Phase 3: **Likely needs deeper research** — code-aware chunking strategies, embedding model selection for code, FAISS GPU index tuning. This is where domain expertise matters most.
- Phase 4: Standard caching patterns. vLLM prefix caching is well-documented.
- Phase 5: **Likely needs deeper research** — QLoRA hyperparameter tuning for code models, DeepSeek-Coder-V2 MoE fine-tuning specifics, adapter quality evaluation metrics.
- Phase 6: Standard observability stack. vLLM exposes Prometheus metrics natively.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against official GitHub releases (vLLM 0.19.0, FastAPI 0.130, PEFT 0.18.1, FAISS 1.14.0, LlamaIndex 0.14.9). |
| Features | HIGH | Feature list derived from vLLM official API docs, 2026 LLM gateway pattern literature, and standard API service requirements. |
| Architecture | HIGH | Architecture pattern confirmed by multiple 2026 sources (FastAPI + vLLM proxy pattern is the standard). GPU partitioning strategy verified against vLLM tensor parallelism docs. |
| Pitfalls | MEDIUM-HIGH | OOM and KV cache issues verified against official vLLM GitHub issues. MLA memory characteristics inferred from DeepSeek paper and vLLM implementation. Some pitfalls based on community reports rather than official documentation. |

## Gaps to Address

- **DeepSeek-Coder-V2 exact GPU requirements**: The MoE architecture (236B total, 21B active) has complex memory characteristics. Exact TP size and GPU count needs empirical testing on H200 hardware.
- **Code-aware embedding model selection**: Which embedding model performs best for code retrieval (nomic-embed-text-v2, bge-large-en-v1.5, or code-specific models like CodeBERT)? Needs benchmarking against the target codebase.
- **LoRA adapter quality evaluation**: How to measure whether a fine-tuned adapter actually improves code generation quality? Needs a code-specific evaluation benchmark (HumanEval, MBPP, or custom).
- **NVLink topology verification**: DGX H200 should have full NVLink, but container/VM configuration could affect this. Needs verification on the actual deployment environment.
- **FAISS index size estimation**: How large will the FAISS index be for a typical codebase? Depends on codebase size, chunking strategy, and embedding dimension. Needs empirical measurement.
