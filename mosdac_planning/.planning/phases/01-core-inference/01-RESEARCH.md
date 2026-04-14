# Phase 1: Core Inference - Research

**Researched:** 2026-04-07
**Domain:** vLLM inference serving, OpenAI-compatible API, GPU memory management, FastAPI gateway
**Confidence:** HIGH

## Summary

vLLM 0.19.0 (released 2026-04-03) is the current stable release and provides a production-ready OpenAI-compatible server out of the box. The `vllm serve` command natively exposes `/v1/chat/completions` with SSE streaming, token counting in `usage` objects, `max_tokens` enforcement, and a `/metrics` Prometheus endpoint. The V1 engine is now the default and only supported engine (V0 deprecated).

For Phase 1, the simplest path is: run `vllm serve` directly with Qwen2.5-Coder-32B using `--tensor-parallel-size 2`, and add a thin FastAPI gateway only for the `/health` endpoint (which vLLM does not provide natively in the form specified — it provides `/health` as a basic liveness check but not with GPU utilization metrics). GPU memory tuning via `--gpu-memory-utilization` is critical for the 32B model on dual GPUs.

**Primary recommendation:** Use `vllm serve` as the inference engine directly; add a lightweight FastAPI sidecar for the custom `/health` endpoint with GPU utilization metrics. No need to wrap vLLM's OpenAI server — it already implements all required inference features natively.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vLLM | 0.19.0 | LLM inference engine with OpenAI-compatible API | Latest stable (released 2026-04-03), V1 engine default, native SSE streaming, token counting, PagedAttention, continuous batching |
| Qwen2.5-Coder-32B-Instruct | Latest (HF) | Code generation model | 32.8B params, 34K context, native chat template, well-supported in vLLM |
| FastAPI | >=0.115.0 | Thin API gateway for /health endpoint | Async-native, standard for Python API layers, lightweight |
| PyNVML / pynvml | >=12.0 | GPU utilization metrics | Standard NVIDIA GPU monitoring library for Python |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openai (Python SDK) | >=1.60 | Client for testing vLLM server | Validating the server works with standard OpenAI client |
| prometheus-client | Bundled with vLLM | Metrics endpoint | vLLM ships this; use for /metrics scraping |
| uvicorn | Bundled with vLLM | ASGI server | vLLM's built-in server uses uvicorn |
| torch | 2.6+ (per vLLM 0.19.0) | Deep learning backend | Required by vLLM; CUDA version must match GPU drivers |
| transformers | >=5.5.0 (per vLLM 0.19.0) | Tokenizer and model config | vLLM 0.19.0 adds Transformers v5 compatibility |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `vllm serve` directly | FastAPI wrapping vLLM as library | More control but significantly more complexity; unnecessary for Phase 1 validation |
| pynvml for GPU metrics | DCGM exporter, nvidia-smi subprocess | DCGM requires additional daemon; nvidia-smi subprocess is slower but simpler fallback |

**Installation:**
```bash
# vLLM with CUDA support
pip install vllm==0.19.0

# FastAPI gateway (thin sidecar)
pip install fastapi uvicorn pynvml

# Client for testing
pip install openai
```

## Architecture Patterns

### Recommended Project Structure
```
inference/
├── docker/
│   └── Dockerfile.vllm          # vLLM server container
├── gateway/
│   ├── main.py                  # FastAPI app with /health endpoint
│   ├── health.py                # GPU utilization + model status logic
│   └── requirements.txt         # Gateway dependencies
├── config/
│   └── vllm-config.yaml         # vLLM server arguments as YAML
└── scripts/
    ├── start-vllm.sh            # Launch vLLM with correct flags
    └── test-inference.py        # Smoke test script
```

### Pattern 1: Direct vLLM Serve (Recommended for Phase 1)
**What:** Run `vllm serve` as a standalone process; it natively provides `/v1/chat/completions`, streaming, token counting, and `max_tokens` enforcement.
**When to use:** Phase 1 validation — no gateway wrapping needed for core inference features.
**Example:**
```bash
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096 \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto
```
Source: [vLLM docs - OpenAI-Compatible Server](https://docs.vllm.ai/en/v0.18.0/serving/openai_compatible_server/)

### Pattern 2: FastAPI Health Sidecar
**What:** A separate lightweight FastAPI process that proxies to vLLM and adds GPU utilization metrics.
**When to use:** When `/health` needs GPU metrics that vLLM's built-in `/health` does not provide.
**Example:**
```python
from fastapi import FastAPI
import pynvml

app = FastAPI()

@app.get("/health")
async def health():
    pynvml.nvmlInit()
    gpu_metrics = []
    for i in range(pynvml.nvmlDeviceGetCount()):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_metrics.append({
            "gpu_id": i,
            "utilization": util.gpu,
            "memory_used_mb": mem.used // (1024**2),
            "memory_total_mb": mem.total // (1024**2),
            "memory_utilization": round(mem.used / mem.total * 100, 1),
        })
    pynvml.nvmlShutdown()
    return {
        "status": "healthy",
        "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "tensor_parallel_size": 2,
        "gpus": gpu_metrics,
    }
```

### Pattern 3: vLLM as Library Inside FastAPI
**What:** Import `vllm.AsyncLLMEngine` and `vllm.SamplingParams` inside a FastAPI app; manually implement OpenAI-compatible endpoints.
**When to use:** When deep customization of request/response format, auth, or routing is needed. **NOT recommended for Phase 1** — overkill for validation.
**Example:**
```python
from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams

engine = AsyncLLMEngine.from_engine_args(
    AsyncEngineArgs(
        model="Qwen/Qwen2.5-Coder-32B-Instruct",
        tensor_parallel_size=2,
        gpu_memory_utilization=0.90,
    )
)

async def generate(prompt: str, max_tokens: int):
    sampling_params = SamplingParams(max_tokens=max_tokens)
    async for output in engine.generate(prompt, sampling_params):
        yield output.outputs[0].text
```
Source: [vLLM docs - Async Engine](https://docs.vllm.ai/en/v0.18.0/)

### Anti-Patterns to Avoid
- **Forking vLLM's server code:** Maintaining a fork creates merge conflicts on every update. Use vLLM as-is and add a sidecar for custom endpoints.
- **Synchronous vLLM calls in FastAPI:** Blocks the event loop, preventing concurrent request handling. Always use `AsyncLLMEngine` if wrapping.
- **Hardcoding `--gpu-memory-utilization` without testing:** The optimal value depends on specific GPU model and workload. Must be tuned empirically.
- **Skipping chat template configuration:** Qwen2.5-Coder-32B-Instruct has a built-in chat template in its tokenizer config. Ensure `--trust-remote-code` is set if loading from HF.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI-compatible API | Custom endpoint mimicking OpenAI format | `vllm serve` built-in server | Already implements Completions API, Chat API, SSE streaming, token counting, `max_tokens`, error handling |
| Token counting | Manual tokenizer-based counting | vLLM `usage` object in response | vLLM returns `prompt_tokens`, `completion_tokens`, `total_tokens` accurately in every response |
| SSE streaming | Custom SSE implementation | vLLM's native `stream: true` support | Handles connection management, chunk formatting, `[DONE]` termination |
| KV cache management | Custom memory management | vLLM PagedAttention + `--gpu-memory-utilization` | PagedAttention prevents fragmentation; gpu-memory-utilization controls allocation |
| Prometheus metrics | Custom metrics collection | vLLM's built-in `/metrics` endpoint | Exposes `vllm:num_requests_running`, `vllm:kv_cache_usage_perc`, `vllm:prompt_tokens_total`, `vllm:generation_tokens_total`, TTFT, latency histograms |

**Key insight:** vLLM 0.19.0's built-in server already satisfies requirements INF-01 through INF-04 natively. The only custom work needed is the `/health` endpoint with GPU utilization (INF-05).

## Common Pitfalls

### Pitfall 1: GPU Memory OOM from Incorrect `--gpu-memory-utilization`
**What goes wrong:** Setting `--gpu-memory-utilization` too high causes CUDA OOM at startup or during heavy load. Setting it too low wastes VRAM and reduces throughput.
**Why it happens:** vLLM allocates 90% of VRAM by default for model + KV cache, reserving 10% for CUDA graphs and runtime overhead. On some GPUs (e.g., H100), this reserved portion can be ~8GB unused.
**How to avoid:** Start at 0.90 (default). Gradually increase to 0.95 if stable. If OOM occurs, decrease by 0.05 increments. Test with realistic prompt lengths.
**Warning signs:** `torch.cuda.OutOfMemoryError` at startup, or crashes during high-concurrency load with long prompts.

### Pitfall 2: Tensor Parallelism Communication Overhead
**What goes wrong:** TP=2 introduces NCCL communication overhead between GPUs. If GPUs are on different PCIe switches or NUMA nodes, performance degrades significantly.
**Why it happens:** Tensor parallelism requires all-reduce operations at every layer. Cross-PCIe-switch communication is much slower than NVLink.
**How to avoid:** Ensure both GPUs are on the same NVLink domain. Use `nvidia-smi topo -m` to verify topology. Set `NCCL_P2P_DISABLE=0` and `NCCL_IB_DISABLE=1` if using NVLink.
**Warning signs:** Low GPU utilization on one GPU, high latency compared to single-GPU baseline.

### Pitfall 3: KV Cache Fragmentation with Long Contexts
**What goes wrong:** With `--max-model-len` set high, the KV cache can fill up quickly, causing requests to queue even when GPU compute is available.
**Why it happens:** vLLM allocates KV cache blocks at startup based on `--max-model-len`. Longer max lengths = fewer total blocks = lower concurrent request capacity.
**How to avoid:** Set `--max-model-len` to the realistic maximum needed (4096 for code completion, not 32K). Monitor `vllm:kv_cache_usage_perc` metric.
**Warning signs:** `vllm:kv_cache_usage_perc` consistently near 1.0, requests queuing despite low GPU compute utilization.

### Pitfall 4: Missing Chat Template for Chat Completions
**What goes wrong:** Using `/v1/chat/completions` without a proper chat template causes errors or malformed output.
**Why it happens:** The Chat API requires a Jinja2 chat template in the tokenizer config. Some base models don't include one.
**How to avoid:** Qwen2.5-Coder-32B-**Instruct** includes a chat template. Use the Instruct variant, not the base model. Verify with `--trust-remote-code` flag.
**Warning signs:** 400 errors on `/v1/chat/completions`, or model output containing raw template tokens like `<|im_start|>`.

### Pitfall 5: Proxy Buffering Breaking SSE Streaming
**What goes wrong:** When placing nginx, CloudFlare, or other proxies in front of vLLM, streaming responses get buffered and delivered all at once.
**Why it happens:** Reverse proxies buffer HTTP responses by default.
**How to avoid:** Set `X-Accel-Buffering: no` header. In nginx: `proxy_buffering off;`.
**Warning signs:** Client receives complete response after full generation time instead of incremental tokens.

### Pitfall 6: vLLM V0 vs V1 Engine Confusion
**What goes wrong:** Documentation and tutorials reference V0 engine flags that are deprecated in vLLM 0.19.0.
**Why it happens:** vLLM 0.19.0 deprecates V0 engine entirely. Flags like `--disable-frontend-multiprocessing`, `--swap-space`, and `--calculate-kv-scales` are deprecated.
**How to avoid:** Use only V1-compatible flags. Check [vLLM 0.19.0 release notes](https://github.com/vllm-project/vllm/releases/tag/v0.19.0) for deprecated features.
**Warning signs:** Deprecation warnings in logs, or flags silently ignored.

## Code Examples

Verified patterns from official sources:

### Starting vLLM with Qwen2.5-Coder-32B (TP=2)
```bash
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096 \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --trust-remote-code
```
Source: [vLLM docs - Serving](https://docs.vllm.ai/en/v0.18.0/serving/openai_compatible_server/)

### Chat Completion with Streaming (Python client)
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",  # or set via --api-key
)

# Non-streaming
completion = client.chat.completions.create(
    model="Qwen/Qwen2.5-Coder-32B-Instruct",
    messages=[
        {"role": "system", "content": "You are a code completion assistant."},
        {"role": "user", "content": "Write a Python function to sort a list"},
    ],
    max_tokens=512,
    temperature=0.7,
)
print(completion.choices[0].message.content)
print(f"Usage: {completion.usage}")  # prompt_tokens, completion_tokens, total_tokens

# Streaming
stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-Coder-32B-Instruct",
    messages=[
        {"role": "user", "content": "def fibonacci(n):"},
    ],
    max_tokens=256,
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```
Source: [vLLM examples - openai_chat_completion_client.py](https://github.com/vllm-project/vllm/blob/main/examples/basic/online_serving/openai_chat_completion_client.py)

### Using YAML Config File
```yaml
# vllm-config.yaml
model: Qwen/Qwen2.5-Coder-32B-Instruct
tensor_parallel_size: 2
gpu_memory_utilization: 0.90
max_model_len: 4096
host: "0.0.0.0"
port: 8000
dtype: "auto"
trust_remote_code: true
```
```bash
vllm serve --config vllm-config.yaml
```
Source: [vLLM docs - Configuration file](https://docs.vllm.ai/en/v0.18.0/configuration/serve_args/#configuration-file)

### Accessing vLLM Prometheus Metrics
```bash
# vLLM exposes metrics at /metrics by default
curl http://localhost:8000/metrics

# Key metrics:
# vllm:num_requests_running - active requests
# vllm:kv_cache_usage_perc - KV cache utilization (0-1)
# vllm:prompt_tokens_total - total prompt tokens processed
# vllm:generation_tokens_total - total generated tokens
# vllm:time_to_first_token_seconds - TTFT histogram
# vllm:inter_token_latency_seconds - inter-token latency
# vllm:e2e_request_latency_seconds - end-to-end latency
```
Source: [vLLM docs - Metrics](https://docs.vllm.ai/en/v0.18.0/design/metrics/)

### GPU Utilization via pynvml
```python
import pynvml

def get_gpu_utilization():
    pynvml.nvmlInit()
    gpus = []
    for i in range(pynvml.nvmlDeviceGetCount()):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpus.append({
            "gpu_id": i,
            "name": pynvml.nvmlDeviceGetName(handle),
            "compute_utilization": util.gpu,
            "memory_utilization_pct": round(mem.used / mem.total * 100, 1),
            "memory_used_mb": mem.used // (1024**2),
            "memory_total_mb": mem.total // (1024**2),
        })
    pynvml.nvmlShutdown()
    return gpus
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| vLLM V0 engine | vLLM V1 engine (default) | vLLM 0.18+ | Better performance, V0 deprecated in 0.19.0 |
| Manual KV cache swap to CPU | CPU KV cache offloading with pluggable policy | vLLM 0.19.0 | More efficient memory management |
| aioprometheus for metrics | prometheus_client + prometheus_fastapi_instrumentator | vLLM 0.14+ | Standard Prometheus integration |
| Single API server process | Frontend multiprocessing (`--api-server-count`) | vLLM 0.17+ | Better HTTP throughput |
| `--swap-space` flag | Removed in V1; replaced by prefix caching | vLLM 0.18+ | Simpler config, better performance |

**Deprecated/outdated:**
- `--swap-space`: Removed in V1 engine. Use prefix caching instead.
- `--disable-frontend-multiprocessing`: Deprecated in vLLM 0.19.0.
- `--calculate-kv-scales`: Deprecated in vLLM 0.19.0.
- `vllm:avg_prompt_throughput_toks_per_s`: Deprecated; use `vllm:prompt_tokens_total` counter.
- `vllm:num_requests_swapped` / `vllm:cpu_cache_usage_perc`: No longer relevant in V1.

## Open Questions

1. **Optimal `--gpu-memory-utilization` for Qwen2.5-Coder-32B on specific GPU hardware**
   - What we know: Default 0.90 works for most setups. Can increase to 0.95 for more KV cache.
   - What's unclear: Exact value depends on GPU model (A100 80GB vs A6000 48GB vs H100 80GB) and `--max-model-len`.
   - Recommendation: Start at 0.90, test with realistic workloads, increase incrementally if stable.

2. **Whether FastAPI gateway should run in same process or separate process**
   - What we know: Separate process is cleaner separation; same process reduces latency.
   - What's unclear: Performance impact of proxying vs. direct vLLM access.
   - Recommendation: For Phase 1, run as separate process. Evaluate co-location in later phases.

3. **Whether to use Docker or bare-metal for deployment**
   - What we know: vLLM provides official Docker images (`vllm/vllm-openai`).
   - What's unclear: User's infrastructure preferences.
   - Recommendation: Support both. Docker for reproducibility, bare-metal for maximum performance.

4. **Model variant: base vs Instruct**
   - What we know: Qwen2.5-Coder-32B-Instruct has chat template; base model does not.
   - What's unclear: Whether code completion (non-chat) needs the Instruct variant.
   - Recommendation: Use Instruct variant — it supports both chat and raw completion modes.

## Sources

### Primary (HIGH confidence)
- [vLLM 0.19.0 Release Notes](https://github.com/vllm-project/vllm/releases/tag/v0.19.0) - Full feature list, deprecations, bugfixes
- [vLLM OpenAI-Compatible Server Docs (v0.18.0)](https://docs.vllm.ai/en/v0.18.0/serving/openai_compatible_server/) - API parameters, chat template, extra params
- [vLLM Serve Arguments Docs](https://docs.vllm.ai/en/v0.18.0/configuration/serve_args/) - CLI arguments, YAML config
- [vLLM Metrics Design](https://docs.vllm.ai/en/v0.18.0/design/metrics/) - Prometheus metrics, Grafana dashboard, metric definitions
- [vLLM PyPI](https://pypi.org/project/vllm/) - Version 0.19.0, Python >=3.10 <3.14
- [Qwen2.5-Coder-32B-Instruct on HuggingFace](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) - Model card, chat template

### Secondary (MEDIUM confidence)
- [Red Hat Developer - vLLM Performance Tuning (March 2026)](https://developers.redhat.com/articles/2026/03/03/practical-strategies-vllm-performance-tuning) - GPU memory tuning, KV cache quantization, concurrency limits
- [Prem AI Blog - FastAPI + vLLM Production Guide (March 2026)](https://blog.premai.io/building-a-production-llm-api-server-fastapi-vllm-complete-guide-2026/) - FastAPI gateway patterns, SSE streaming, rate limiting, health checks
- [Ventus Server - vLLM GPU Memory Optimization (Jan 2026)](https://ventusserver.com/vllm-gpu-memory-optimization-guide/) - GPU memory best practices
- [OneUptime - vLLM OpenAI Compatible API (Jan 2026)](https://oneuptime.com/blog/post/2026-01-28-vllm-openai-compatible-api/view) - Deployment guide

### Tertiary (LOW confidence)
- [Reddit - Serving Qwen2.5-32B AWQ on single RTX 3090](https://www.reddit.com/r/LocalLLaMA/comments/1hm3e5t/how_to_serve_vllm_qwen2532b_awq_on_a_single_rtx/) - Community experience, needs verification
- [Medium - 7 LLM Backends with FastAPI + vLLM (Sep 2025)](https://medium.com/@ThinkingLoop/7-llm-backends-that-actually-work-fastapi-vllm-0621c394e876) - Unverified patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - vLLM 0.19.0 is confirmed latest stable; all libraries verified against official docs
- Architecture: HIGH - Direct `vllm serve` pattern is the documented standard; FastAPI sidecar for /health is standard pattern
- Pitfalls: HIGH - GPU memory, TP overhead, KV cache, and chat template pitfalls verified against official docs and Red Hat guide
- Streaming/token counting: HIGH - Confirmed native support in vLLM OpenAI server docs

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (30 days — vLLM release cadence is ~monthly, but core APIs are stable)