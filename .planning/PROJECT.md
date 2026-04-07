# Code Generation API Service

## What This Is

A private code generation API service running on DGX H200 infrastructure that provides an OpenAI-compatible API for code completion, generation, and code intelligence features. Essentially a self-hosted GitHub Copilot backend.

## Core Value

Deliver high-quality, context-aware code generation through an OpenAI-compatible API that any existing tool can plug into without modification.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] OpenAI-compatible API endpoints (/v1/completions, /v1/chat/completions)
- [ ] Token streaming via SSE
- [ ] Support for code generation models (DeepSeek-Coder-V2, Qwen2.5-Coder-32B, CodeLlama 70B)
- [ ] QLoRA fine-tuning capability for custom codebases
- [ ] High-throughput inference serving with continuous batching
- [ ] Rate limiting and prompt caching
- [ ] Tree-sitter integration for AST-aware code context
- [ ] RAG over private codebase for repository-specific completions
- [ ] Fill-in-the-middle (FIM) support for IDE-style autocomplete
- [ ] Evaluation pipeline with HumanEval and MBPP benchmarks

### Out of Scope

- Web UI / frontend — API-only service
- Multi-tenant SaaS — single instance on dedicated hardware
- Real-time collaborative editing — focused on generation, not collaboration

## Context

- Hardware: DGX H200 with 141GB HBM3e per GPU, multi-GPU setup available
- Base model options: DeepSeek-Coder-V2 (236B with tensor parallelism), Qwen2.5-Coder-32B, CodeLlama 70B
- Stack: vLLM for inference, FastAPI for API layer, Redis for caching, LlamaIndex + FAISS for RAG
- Containerized deployment as single API endpoint

## Constraints

- **Hardware**: DGX H200 infrastructure — leverage NVIDIA-native tooling (NeMo, TensorRT-LLM)
- **Memory**: 141GB HBM3e per GPU — model selection must fit within constraints or use tensor parallelism
- **Compatibility**: OpenAI-compatible API — must work with existing VS Code extensions and clients

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| vLLM for inference serving | PagedAttention + continuous batching for high throughput | — Pending |
| OpenAI-compatible API | Zero integration friction with existing tools | — Pending |
| QLoRA via PEFT | Efficient fine-tuning without full retraining | — Pending |
| AWQ 4-bit quantization | Halve memory footprint with minimal quality loss | — Pending |

---
*Last updated: 2026-04-07 after initialization*
