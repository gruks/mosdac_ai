# Domain Pitfalls

**Domain:** Code Generation API Service on DGX H200 (multi-GPU, private inference)
**Researched:** 2026-04-07

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: GPU Memory Miscalculation → OOM Cascades
**What goes wrong:** Underestimating total GPU memory requirements leads to CUDA OOM errors that crash the entire vLLM instance, taking down all requests routed to that model.
**Why it happens:** Model weights are only part of the memory equation. You must account for:
- Model weights (BF16: 2 bytes × parameters)
- KV cache (grows linearly with context length × batch size)
- Activation memory (grows with batch size and sequence length)
- CUDA graph memory (vLLM pre-allocates for performance)
- NCCL communication buffers (for tensor parallelism)

For CodeLlama 70B at BF16: weights alone = ~140GB. With KV cache and activations on a 141GB H200, you need at minimum 4 GPUs (TP=4) with `--gpu-memory-utilization 0.90`.

**Consequences:** Service outage for all users of that model. In multi-model setups, one model's OOM can starve others if GPUs are shared.
**Prevention:**
- Use `vllm bench` to profile memory before production deployment
- Set `--gpu-memory-utilization 0.85-0.90` (leave headroom for KV cache spikes)
- Monitor KV cache utilization via Prometheus; alert at >85%
- For 70B models on H200: minimum TP=4, recommended TP=4 with quantization
**Detection:** Prometheus metric `vllm:gpu_cache_usage_perc` approaching 1.0. `gpu_memory_utilization` errors in vLLM logs.

### Pitfall 2: Tensor Parallelism Across NVLink vs PCIe Boundaries
**What goes wrong:** Configuring tensor parallelism across GPUs that aren't connected via NVLink causes 5-10x performance degradation due to PCIe bandwidth bottleneck.
**Why it happens:** DGX H200 has full NVLink connectivity between all 8 GPUs, but if you're running in a VM or container with GPU isolation that doesn't preserve NVLink topology, vLLM may fall back to PCIe.
**Consequences:** Throughput drops from hundreds of tokens/sec to tens. Latency spikes. Users abandon the service.
**Prevention:**
- Verify NVLink topology with `nvidia-smi topo -m` before deployment
- Use `--tensor-parallel-size` with GPUs on the same NVLink domain
- In Docker: use `--gpus all` (not `--gpus '"device=0,1"'`) to preserve topology
- Test with `vllm bench throughput` after deployment
**Detection:** `nvidia-smi nvlink -s` shows zero link utilization during inference. Throughput benchmarks far below expected.

### Pitfall 3: DeepSeek-Coder-V2 MLA Memory Explosion
**What goes wrong:** DeepSeek-Coder-V2's Multi-Head Latent Attention (MLA) has different KV cache characteristics than standard attention. The compressed KV cache can still explode with long contexts, causing unexpected OOM.
**Why it happens:** MLA uses low-rank compression for KV cache, but the compression ratio depends on the configured `qk_rope_head_dim` and `kv_lora_rank`. With long code contexts (16K+ tokens), the KV cache can still exceed available memory even with MLA.
**Consequences:** OOM during long code generation tasks — exactly when you need the model most.
**Prevention:**
- Use `--max-model-len` to cap context length based on available KV cache
- Enable `--enable-prefix-caching` to reduce redundant KV cache for shared system prompts
- For DeepSeek-Coder-V2 on H200: TP=4 minimum, TP=8 recommended for full model
- Use FlashInfer MLA backend (vLLM default for DeepSeek models)
**Detection:** vLLM logs show KV cache allocation failures. Requests with long prompts fail while short ones succeed.

### Pitfall 4: vLLM V0 Engine Deprecation Breakage
**What goes wrong:** vLLM is actively deprecating the V0 engine (started in v0.19.0). Code written against V0 internals will break.
**Why it happens:** vLLM's V1 engine has different scheduling, memory management, and API surface. Any code that imports from `vllm.engine` directly (not via the HTTP API) will break.
**Consequences:** After upgrading vLLM, custom integrations silently break or crash.
**Prevention:**
- Use vLLM's HTTP API only (never import vLLM internals)
- Pin vLLM version in production: `vllm==0.19.0`
- Test upgrades in staging before production
- Follow vLLM release notes for deprecation warnings
**Detection:** Import errors after vLLM upgrade. `DeprecationWarning` logs mentioning V0 engine.

## Moderate Pitfalls

### Pitfall 5: FAISS Index Not Persisted Across Restarts
**What goes wrong:** FAISS in-memory indexes are lost on process restart. RAG stops working until the index is rebuilt.
**Prevention:** Save FAISS index to disk with `faiss.write_index()`. Load on startup. For GPU indexes, transfer to CPU first: `faiss.index_gpu_to_cpu()`.

### Pitfall 6: Redis Connection Pool Exhaustion Under Load
**What goes wrong:** Under high concurrent load, Redis connection pool runs out, causing request failures.
**Prevention:** Configure `redis.ConnectionPool(max_connections=50)` or higher based on expected concurrency. Use `redis.asyncio` for async FastAPI. Monitor Redis connection count.

### Pitfall 7: Embedding Model Bottleneck in RAG Pipeline
**What goes wrong:** Using a CPU-based embedding model becomes the bottleneck for RAG, adding seconds to every request.
**Prevention:** Run embedding model on GPU (H200 has plenty of spare capacity). Use `sentence-transformers` with `device="cuda"`. Cache embeddings aggressively in Redis.

### Pitfall 8: bitsandbytes CUDA Version Mismatch
**What goes wrong:** `bitsandbytes` compiled for a different CUDA version than your runtime causes import errors or silent performance degradation.
**Prevention:** Install `bitsandbytes` with matching CUDA: `pip install bitsandbytes==0.45.0` on CUDA 12.x. Use the same base image for training and inference containers. Verify with `python -c "import bitsandbytes; print(bitsandbytes.__version__)"`.

### Pitfall 9: LlamaIndex Document Chunking Breaks Code Semantics
**What goes wrong:** Default text chunking splits code in the middle of functions, classes, or imports, producing useless RAG context.
**Prevention:** Use code-aware chunking: split at function/class boundaries, keep imports with their code blocks. LlamaIndex supports custom `TextSplitter` implementations. Use `CodeSplitter` or implement one that respects AST boundaries.

### Pitfall 10: Prometheus Metrics Cardinality Explosion
**What goes wrong:** Including request IDs, user IDs, or prompt hashes in Prometheus labels causes metric cardinality explosion, crashing Prometheus.
**Prevention:** Never use high-cardinality values as Prometheus labels. Use histograms for latency distributions, counters for request totals. Store per-request details in a separate logging system (ELK, Loki).

## Minor Pitfalls

### Pitfall 11: vLLM `--max-num-seqs` Too Low
**What goes wrong:** Default `--max-num-seqs` limits concurrent requests. Under load, requests queue instead of being processed.
**Prevention:** Set `--max-num-seqs` based on your GPU memory and expected concurrency. Start with 256 and tune based on KV cache utilization.

### Pitfall 12: FastAPI `uvloop` Not Enabled
**What goes wrong:** Running FastAPI without uvloop loses 20-30% throughput on async operations.
**Prevention:** Install `uvicorn[standard]` (includes uvloop). Start with `uvicorn app:app --loop uvloop`.

### Pitfall 13: Docker Image Layer Bloat
**What goes wrong:** Docker images for ML services easily exceed 20GB. Slow pulls, slow deployments, wasted disk.
**Prevention:** Use `vllm/vllm-openai` as base image (pre-built with CUDA dependencies). Multi-stage builds for FastAPI layer. `.dockerignore` to exclude model weights from build context.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Initial vLLM setup** | Wrong tensor parallelism size for model → OOM or wasted GPUs | Profile each model's memory with `vllm bench` before choosing TP size. Use the GPU allocation table in STACK.md. |
| **Multi-model routing** | Routing to a model that's still loading → 503 errors | Implement health checks per vLLM instance. Router should only route to healthy instances. |
| **RAG pipeline** | FAISS index build takes hours on large codebases | Build index incrementally. Cache embeddings. Use IVF index for faster build on large datasets. |
| **Fine-tuning setup** | QLoRA training OOM on 70B model even with 4-bit quantization | Use gradient accumulation, gradient checkpointing, and `max_seq_length` limits. Start with smaller models first. |
| **Production deployment** | Container GPU passthrough fails silently | Always test with `docker run --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi` before deploying your image. |
| **Scaling up** | Adding more users without adjusting `--max-num-seqs` → queued requests | Monitor queue depth via Prometheus. Scale `--max-num-seqs` or add data-parallel vLLM instances. |
| **vLLM upgrades** | Breaking changes in model loading or API format | Pin versions in production. Test upgrades in staging with all three models before rolling out. |
| **LoRA deployment** | LoRA adapter incompatible with base model version → silent quality degradation | Always verify LoRA adapter was trained on the exact same base model checkpoint. Test output quality after loading. |

## Sources

- **vLLM OOM Discussion** — https://github.com/vllm-project/vllm/discussions/309 (HIGH — official GitHub discussion)
- **vLLM KV Cache Memory Bug** — https://github.com/vllm-project/vllm/issues/34076 (HIGH — official issue, Feb 2026)
- **vLLM KV Cache Regression** — https://github.com/vllm-project/vllm/issues/37951 (HIGH — official issue, Mar 2026)
- **vLLM Multi-GPU Optimization Guide** — https://www.databasemart.com/blog/vllm-distributed-inference-optimization-guide (MEDIUM — optimization guide)
- **vLLM Tensor Parallelism Guide** — https://ventusserver.com/parallelism-on-multi-gpu-setup/ (MEDIUM — deployment guide, Jan 2026)
- **vLLM KV Cache Handling** — https://ventusserver.com/vllm-for-large-models/ (MEDIUM — optimization guide, Jan 2026)
- **DeepSeek-R1 Stable Setup on DGX** — https://forums.developer.nvidia.com/t/gb10-vllm-deepseek-r1-32b-stable-setup-on-blackwell-full-protocol-after-4-days-of-failures/363533 (MEDIUM — NVIDIA forum, Mar 2026)
- **AI-Generated Code OWASP Top 10** — https://www.growexx.com/blog/ai-generated-code-owasp-top-10/ (MEDIUM — security guide, Apr 2026)
