# Stack Research

**Domain:** Code Generation API Service on DGX H200 (multi-GPU, private inference)
**Researched:** 2026-04-07
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **vLLM** | 0.19.0 (Apr 2026) | LLM inference engine + OpenAI-compatible API server | Dominant open-source inference engine (76K GitHub stars). Native OpenAI-compatible `/v1/chat/completions`, `/v1/completions`, and `/v1/responses` APIs. PagedAttention + continuous batching for max throughput. Built-in tensor parallelism for multi-GPU DGX H200. Explicit support for DeepSeek-Coder-V2 (MLA attention), Qwen2.5-Coder, and CodeLlama. v0.19.0 adds zero-bubble async scheduling, CPU KV cache offloading, and H200-tuned Triton MoE configs (9.9% E2E improvement). |
| **FastAPI** | 0.130.0+ (Feb 2026) | Custom API orchestration layer | Python's standard for high-performance async APIs. Pydantic v2 native (2-5x validation speed). Use as the *orchestration* layer that routes to vLLM, handles auth, rate limiting, caching, and RAG — not as the inference server itself (vLLM handles inference). |
| **PyTorch** | 2.7.x (CUDA 12.8) | Deep learning framework | Required by vLLM, PEFT, transformers. H200 (Hopper, SM 90) requires CUDA 12+. PyTorch 2.7+ has native H200 support with optimized FlashAttention-3 kernels. |
| **HuggingFace Transformers** | 4.52+ / 5.x | Model loading, tokenization, training glue | Universal model interface. v4.52+ required for DeepSeek-Coder-V2 MLA support. vLLM v0.19.0 has broad transformers v5 compatibility fixes. Use v4.52 for stability; v5 when ecosystem stabilizes. |

### Inference & Model Serving

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **vLLM** (Docker) | `vllm/vllm-openai:latest` (v0.19.0) | GPU inference container | Pre-built Docker image with all CUDA/cuDNN dependencies. Use `vllm serve` with `--tensor-parallel-size` for multi-GPU. For DGX H200 with 141GB per GPU: CodeLlama 70B needs ~4 GPUs (tensor parallel), Qwen2.5-Coder-32B needs ~2 GPUs, DeepSeek-Coder-V2 (MoE, 236B total / 21B active) needs ~4-8 GPUs depending on quantization. |
| **FlashInfer** | 0.2.x (bundled with vLLM) | Attention kernel backend | vLLM's default attention backend on NVIDIA GPUs. FlashInfer MLA is the default for DeepSeek models' Multi-Head Latent Attention. 15-30% throughput improvement over standard FlashAttention for MLA architectures. |

### RAG (Retrieval-Augmented Generation)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **LlamaIndex** | 0.14.9+ (Dec 2025) | RAG orchestration framework | 48K GitHub stars. Best-in-class document ingestion pipeline with 200+ data connectors. Native FAISS integration. Query engine abstraction makes it easy to swap retrievers. Active development (417 commits since v0.14.9). |
| **FAISS** | 1.14.0 (Mar 2026) | Vector similarity search | Meta's library, 40K GitHub stars. GPU-accelerated via NVIDIA cuVS integration (added in v1.10+, enhanced in v1.14). In-memory index means zero external dependencies — ideal for private deployment. Use `faiss.GpuIndexIVFFlat` or `faiss.GpuIndexIVFPQ` for GPU-accelerated search on H200. |
| **SentenceTransformers** | 3.4.x | Embedding model framework | Standard for generating embeddings for RAG. Use `nomic-embed-text-v2` or `bge-large-en-v1.5` for code-aware embeddings. GPU-accelerated encoding on H200. |

### Fine-Tuning

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **PEFT** | 0.18.1 (Jan 2026) | Parameter-efficient fine-tuning | HuggingFace's official PEFT library (21K stars). QLoRA via `bitsandbytes` integration. v0.18.1 adds transformers v5 compatibility and ROCm fixes. Supports LoRA, QLoRA, DoRA, and newer methods (RoAd, DeLoRA). Native mixed-adapter batching for RoAd. |
| **bitsandbytes** | 0.45.x | 4-bit/8-bit quantization | Required for QLoRA. NF4 quantization with double quantization. CUDA 12.x support. Reduces 70B model fine-tuning VRAM from ~140GB to ~40GB — fits on a single H200 GPU. |
| **TRL** (Transformer Reinforcement Learning) | 0.15.x | SFT/DPO training loop | HuggingFace's training library. `SFTTrainer` with PEFT integration is the standard supervised fine-tuning path. Supports dataset streaming, gradient checkpointing, and gradient accumulation for large models. |

### Caching & State

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Redis** | 7.4+ (Valkey 8.x as alternative) | Response caching, rate limiting, session state | In-memory key-value store. Use for: (1) caching identical prompt completions, (2) token bucket rate limiting, (3) request deduplication, (4) conversation session state. Redis 7.4 adds JSON module improvements. Run as a sidecar container — no GPU needed. |

### Observability & Monitoring

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Prometheus** | 3.x | Metrics collection | vLLM exposes `/metrics` endpoint with GPU utilization, KV cache usage, request latency, throughput. Prometheus scrapes these natively. Standard for infrastructure metrics. |
| **Grafana** | 11.x | Dashboard & alerting | Pre-built vLLM dashboards available in community. Visualize GPU memory, TTFT (time-to-first-token), tokens/sec, queue depth. Alert on KV cache saturation (>90%), GPU OOM risk, request latency spikes. |
| **OpenTelemetry** | 1.30+ | Distributed tracing | vLLM v0.19.0 has native tracing support (`vllm/tracing`). FastAPI integrates via `opentelemetry-instrumentation-fastapi`. Trace requests from API gateway → FastAPI → vLLM → response. |

### Containerization & Deployment

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Docker** | 27.x + NVIDIA Container Toolkit | Container runtime | Standard for reproducible deployments. NVIDIA Container Toolkit (v1.17+) provides GPU passthrough to containers. Use `vllm/vllm-openai` base image for inference containers. |
| **NVIDIA Container Toolkit** | 1.17+ | GPU access in containers | Required for Docker containers to access H200 GPUs. Enables `--gpus all` flag. Handles CUDA driver compatibility between host and container. |
| **docker-compose** | 2.30+ | Multi-service orchestration | Define vLLM, FastAPI, Redis, and observability stack as services. Single `docker-compose up` for local dev and staging. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Python** | 3.11 or 3.12 | Required by all ML libraries. 3.12 recommended (5-10% faster). PEFT 0.18+ dropped Python 3.9 support. |
| **uv** | Package manager | 10-100x faster than pip. Resolves dependency conflicts between vLLM, transformers, PEFT, and bitsandbytes. Use `uv pip` for ML dependencies. |
| **ruff** | Linting + formatting | Replaces flake8 + black + isort. 100x faster. Standard in 2025-2026 Python projects. |
| **pytest** | Testing | Standard Python testing. Use `pytest-asyncio` for async FastAPI tests. |
| **httpx** | Async HTTP client | For FastAPI integration tests and calling vLLM API from orchestration layer. |
| **OpenAI Python SDK** | 1.70+ | vLLM's OpenAI-compatible API is designed for this client. Use as the client library for both testing and production calls to vLLM. |

## Installation

```bash
# Create virtual environment with Python 3.12
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows

# Install uv for fast package management
pip install uv

# Core inference (vLLM with OpenAI API)
uv pip install vllm==0.19.0

# API orchestration layer
uv pip install fastapi==0.130.0 uvicorn[standard]==0.34.0 pydantic==2.10.0

# RAG stack
uv pip install llama-index==0.14.9 faiss-gpu==1.14.0 sentence-transformers==3.4.0

# Fine-tuning stack
uv pip install peft==0.18.1 bitsandbytes==0.45.0 trl==0.15.0 transformers==4.52.0

# Caching & async
uv pip install redis==5.2.0 httpx==0.28.0 openai==1.70.0

# Observability
uv pip install prometheus-client==0.21.0 opentelemetry-api==1.30.0 opentelemetry-sdk==1.30.0

# Dev dependencies
uv pip install ruff==0.9.0 pytest==8.3.0 pytest-asyncio==0.25.0

# Docker (system-level, not pip)
# Install NVIDIA Container Toolkit per NVIDIA docs
# docker pull vllm/vllm-openai:latest
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **vLLM** | TGI (Text Generation Inference) | TGI if you need HuggingFace Hub integration and don't need multi-model serving. vLLM has better throughput, broader model support, and more active development (76K vs 13K stars). |
| **vLLM** | Ollama | Ollama only for local dev/prototyping on single GPU. vLLM for production multi-GPU serving — Ollama's llama.cpp backend is 2-5x slower than vLLM's PagedAttention. |
| **vLLM** | TensorRT-LLM | TensorRT-LLM if you need absolute maximum throughput and can tolerate the compilation overhead and narrower model support. vLLM for faster iteration and broader model compatibility. |
| **FastAPI** | Flask | Never for this use case. Flask is synchronous, slower, and lacks async streaming — critical for SSE token streaming from LLMs. |
| **LlamaIndex** | LangChain | LangChain if you need agent/tool-calling orchestration beyond RAG. For pure RAG (document ingestion → retrieval → generation), LlamaIndex has cleaner abstractions and better FAISS integration. |
| **FAISS** | Milvus / Qdrant | Milvus or Qdrant if you need persistent, distributed vector storage with horizontal scaling. FAISS for private single-node deployment — it's in-process, zero external dependencies, and GPU-accelerated via cuVS. |
| **Redis** | Valkey | Valkey (Redis fork, v8.x) if you want a fully open-source alternative post-Redis license change. Functionally identical for caching use case. |
| **PEFT + bitsandbytes** | Unsloth | Unsloth if you want 2x faster fine-tuning on supported architectures (Llama, Mistral, Phi). Unsloth doesn't support DeepSeek-Coder-V2's MLA architecture. Use PEFT for model coverage, Unsloth for speed on supported models. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Pydantic v1** | vLLM v0.19.0 and FastAPI 0.130+ require Pydantic v2. v1 is EOL and causes import conflicts. | Pydantic v2 (bundled with FastAPI 0.100+) |
| **transformers < 4.52** | Missing DeepSeek-Coder-V2 MLA support. PEFT 0.18+ requires 4.52+ for v5 compatibility. | transformers 4.52.0+ |
| **Python 3.9 / 3.10** | PEFT 0.18+ dropped 3.9. 3.10 works but 3.12 is 5-10% faster and has better type inference. | Python 3.12 |
| **TGI for multi-model** | TGI is designed for single-model serving. Switching models requires restarting the server. | vLLM (supports `--enable-lora` for adapter switching, or run multiple vLLM instances) |
| **LangChain for pure RAG** | LangChain's abstraction layers add latency and complexity. For code-gen RAG (retrieve docs → inject context → generate), LlamaIndex's simpler pipeline is faster and easier to debug. | LlamaIndex |
| **CPU-only FAISS** | FAISS on CPU is 10-50x slower than GPU for vector search. You have H200 GPUs — use them. | `faiss-gpu` with cuVS acceleration |
| **Full fine-tuning without QLoRA** | Full fine-tuning a 70B model requires ~140GB VRAM (needs 2+ H200 GPUs just for training). QLoRA achieves 90-95% of the quality at 25% of the memory. | QLoRA via PEFT + bitsandbytes |
| **Docker without NVIDIA Container Toolkit** | Containers won't see GPUs. This is the #1 deployment mistake. | Always install NVIDIA Container Toolkit and use `--gpus all` |
| **vLLM V0 engine** | vLLM is actively deprecating the V0 engine (V0 deprecation started in v0.19.0). V1 engine has better scheduling, memory management, and is the future. | Use V1 engine (default in vLLM 0.19.0+) |

## Stack Patterns by Variant

**If deploying a single model (e.g., Qwen2.5-Coder-32B only):**
- Run vLLM as a standalone container with `--tensor-parallel-size 2`
- FastAPI layer handles auth, rate limiting, and proxies to vLLM
- Simpler architecture, fewer moving parts

**If serving multiple models simultaneously:**
- Run separate vLLM instances per model (one container per model)
- FastAPI acts as a router: `POST /v1/chat` with `model` header selects the backend
- Each vLLM instance gets its own GPU allocation
- Use Redis for cross-model request caching

**If fine-tuning is a priority:**
- Separate training environment from inference environment
- Training: PEFT + TRL + bitsandbytes on dedicated GPU allocation
- Inference: vLLM with merged LoRA adapters (merge before serving for zero overhead)
- Don't run training and inference on the same GPU simultaneously

**If RAG is the primary differentiator:**
- FAISS index loaded in FastAPI process (not in vLLM)
- LlamaIndex handles document chunking, embedding, and retrieval
- Retrieved context injected into system prompt before sending to vLLM
- Cache embedding results in Redis to avoid re-embedding identical documents

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| vLLM 0.19.0 | transformers 4.52+ or 5.x, PyTorch 2.6+, Python 3.10-3.12 | vLLM 0.19.0 has explicit transformers v5 compatibility fixes. PyTorch 2.7+ recommended for H200. |
| PEFT 0.18.1 | transformers 4.52+, bitsandbytes 0.45+, Python 3.10+ | PEFT 0.18+ requires transformers 4.52+. Python 3.9 dropped. |
| LlamaIndex 0.14.9 | Python 3.10+, FAISS 1.10+ | Modular package system — install only needed integrations. |
| FAISS 1.14.0 | CUDA 12.x, Python 3.10-3.12 | Use `faiss-gpu` pip package (not `faiss-cpu`). cuVS integration requires CUDA 12+. |
| FastAPI 0.130.0 | Pydantic 2.10+, Python 3.10+ | Pydantic v2 is mandatory. uvicorn 0.34+ for best async performance. |
| bitsandbytes 0.45.0 | CUDA 12.x, PyTorch 2.5+, Python 3.10+ | NF4 quantization requires CUDA 12.1+. H200 (CUDA 12.8) is fully supported. |

## Sources

- **vLLM v0.19.0 Release Notes** — https://github.com/vllm-project/vllm/releases/tag/v0.19.0 (HIGH confidence — official release, Apr 2026)
- **vLLM OpenAI-Compatible Server Docs** — https://docs.vllm.ai/en/v0.19.0/serving/openai_compatible_server/ (HIGH confidence — official docs)
- **vLLM DeepSeek-V2 Model Support** — https://docs.vllm.ai/en/stable/api/vllm/model_executor/models/deepseek_v2/ (HIGH confidence — official API docs)
- **vLLM Supported Models** — https://docs.vllm.ai/en/latest/models/supported_models/ (HIGH confidence — official docs)
- **FastAPI 0.130.0 Release** — https://github.com/fastapi/fastapi/releases/tag/0.130.0 (HIGH confidence — official release, Feb 2026)
- **PEFT 0.18.1 Release** — https://github.com/huggingface/peft/releases/tag/v0.18.1 (HIGH confidence — official release, Jan 2026)
- **LlamaIndex 0.14.9 Release** — https://github.com/run-llama/llama_index/releases/tag/v0.14.9 (HIGH confidence — official release, Dec 2025)
- **FAISS 1.14.0 Release** — https://github.com/facebookresearch/faiss/releases/tag/v1.14.0 (HIGH confidence — official release, Mar 2026)
- **FAISS + NVIDIA cuVS Integration** — https://developer.nvidia.com/blog/enhancing-gpu-accelerated-vector-search-in-faiss-with-nvidia-cuvs/ (HIGH confidence — NVIDIA official blog, Nov 2025)
- **vLLM Multi-GPU Production Deployment 2026** — https://www.spheron.network/blog/vllm-production-deployment-2026 (MEDIUM confidence — community guide, Mar 2026)
- **Monitoring LLM Inference with Prometheus/Grafana 2026** — https://glukhov.org/observability/monitoring-llm-inference-prometheus-grafana/ (MEDIUM confidence — community guide, Mar 2026)
- **QLoRA Fine-Tuning Guide 2026** — https://oneuptime.com/blog/post/2026-01-30-qlora-fine-tuning/view (MEDIUM confidence — community guide, Jan 2026)
- **Fine-Tuning Infrastructure: LoRA, QLoRA, PEFT at Scale** — https://introl.com/blog/fine-tuning-infrastructure-lora-qlora-peft-scale-guide-2025 (MEDIUM confidence — industry guide, Apr 2026)

---
*Stack research for: Code Generation API Service on DGX H200*
*Researched: 2026-04-07*
