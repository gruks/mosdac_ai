# Phase 1 (RTX 1650 Adaptation): Core Inference — Research

**Researched:** 2026-04-07
**Domain:** Ollama, GGUF quantization, small code models, FastAPI wrapper, local RAG
**Confidence:** HIGH

## Summary

An RTX 1650 with 4GB VRAM cannot run the originally planned Qwen2.5-Coder-32B or vLLM. Instead, use **Ollama** with **Qwen2.5-Coder-1.5B** in **Q4_K_M GGUF quantization** (~1GB VRAM). Ollama natively provides an OpenAI-compatible API at `localhost:11434/v1/`, which means the API layer you build is identical to the production version — only the inference backend changes.

The architecture is: **Ollama (inference) → FastAPI wrapper (auth, logging, rate limiting, RAG) → Client**. This is the same pattern as `vLLM → FastAPI → Client` in the DGX version, just with a different inference engine.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Ollama | Latest (0.5+) | Local LLM inference engine | Handles GGUF models, GPU offloading, OpenAI-compatible API out of the box |
| Qwen2.5-Coder-1.5B-Instruct | Ollama tag `qwen2.5-coder:1.5b` | Code generation model | Best quality-to-size ratio for 4GB VRAM; ~1GB VRAM at Q4 quantization |
| FastAPI | >=0.115.0 | API gateway | Wraps Ollama with auth, rate limiting, logging, RAG, custom endpoints |
| httpx | >=0.27.0 | Async HTTP client | For proxying requests to Ollama's API |
| ChromaDB | >=0.5.0 | Local vector store for RAG | Embeddings + retrieval without external dependencies |
| LlamaIndex | >=0.12.0 | RAG orchestration | Code-aware document splitting, Ollama integration |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| python-dotenv | Environment variable management | Loading config from .env files |
| pydantic | Request/response validation | Structured API contracts |
| slowapi | Rate limiting | Redis-backed or in-memory rate limiting |
| itsdangerous | API key generation/validation | Simple auth without database |
| sentence-transformers | Embedding model | For RAG (all-MiniLM-L6-v2 runs on CPU, ~80MB) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Ollama | llama.cpp directly, LM Studio | More control but Ollama has built-in OpenAI API and model management |
| Qwen2.5-Coder-1.5B | DeepSeek-Coder-1.3B, Phi-3-mini | Qwen2.5-Coder has better code quality per benchmark |
| ChromaDB | FAISS, Qdrant | ChromaDB is simpler for local dev; FAISS is lighter but harder to set up |

**Installation:**
```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5-coder:1.5b

# Python dependencies
pip install fastapi uvicorn httpx python-dotenv pydantic
pip install chromadb llama-index llama-index-llms-ollama llama-index-embeddings-huggingface
pip install slowapi itsdangerous
```

## Architecture Patterns

### Recommended Project Structure
```
api/
├── main.py                  # FastAPI app entry point
├── config.py                # Settings (model name, Ollama URL, API keys)
├── auth.py                  # API key validation middleware
├── proxy.py                 # vLLM/Ollama proxy with SSE streaming
├── health.py                # Health endpoint with model status
├── rag/
│   ├── ingest.py            # Code file ingestion and splitting
│   ├── retriever.py         # ChromaDB retrieval
│   └── prompt_builder.py    # Context injection into prompts
├── models/
│   ├── request.py           # Pydantic request models
│   └── response.py          # Pydantic response models
└── requirements.txt
```

### Pattern 1: Ollama as Inference Backend
**What:** Run Ollama as a background service; it natively provides `/v1/chat/completions` with streaming, token counting, and `max_tokens` enforcement.
**When to use:** RTX 1650 development — Ollama handles GPU offloading automatically.
**Example:**
```bash
# Start Ollama (runs as service on Windows)
ollama serve

# Pull the model
ollama pull qwen2.5-coder:1.5b

# Test it works
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:1.5b",
    "messages": [{"role": "user", "content": "def fibonacci(n):"}],
    "max_tokens": 128
  }'
```
Source: [Ollama OpenAI Compatibility Docs](https://docs.ollama.com/api/openai-compatibility)

### Pattern 2: FastAPI Proxy to Ollama
**What:** FastAPI app that proxies requests to Ollama's OpenAI-compatible API, adding auth, logging, rate limiting.
**When to use:** Always — this is your production API layer.
**Example:**
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI()
OLLAMA_URL = "http://localhost:11434/v1"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    body["model"] = "qwen2.5-coder:1.5b"  # Force model server-side

    async with httpx.AsyncClient() as client:
        if body.get("stream"):
            # Proxy SSE streaming
            async with client.stream(
                "POST", f"{OLLAMA_URL}/chat/completions", json=body
            ) as response:
                async for chunk in response.aiter_text():
                    yield chunk
        else:
            # Proxy standard request
            resp = await client.post(f"{OLLAMA_URL}/chat/completions", json=body)
            return resp.json()
```

### Pattern 3: Local RAG with ChromaDB + LlamaIndex
**What:** Ingest code files, split at function/class boundaries, store embeddings in ChromaDB, retrieve relevant context for completions.
**When to use:** Phase 3 — but can prototype in Phase 1.
**Example:**
```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# Embedding model (runs on CPU, ~80MB)
embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# LLM via Ollama
llm = Ollama(model="qwen2.5-coder:1.5b", base_url="http://localhost:11434")

# ChromaDB (persistent, local)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("codebase")
vector_store = ChromaVectorStore(chroma_collection=collection)

# Ingest code files
documents = SimpleDirectoryReader("./my-codebase").load_data()
index = VectorStoreIndex.from_documents(
    documents,
    embed_model=embed_model,
    vector_store=vector_store,
)

# Query
query_engine = index.as_query_engine(llm=llm)
response = query_engine.query("How does authentication work?")
```
Source: [LlamaIndex Local RAG with Chroma + Ollama](https://developers.llamaindex.ai/python/examples/cookbooks/local_rag_with_chroma_and_ollama/)

### Anti-Patterns to Avoid
- **Running vLLM on RTX 1650:** vLLM requires CUDA compute capability 7.0+ and significant VRAM. GTX 1650 is compute capability 7.5 but only 4GB — vLLM will OOM immediately.
- **Using 7B+ models locally:** Even Q4 quantized, 7B models need ~4-5GB VRAM. Your 1650 has 4GB — too tight. Stick to 1.5B-3B.
- **Hand-rolling OpenAI API compatibility:** Ollama already provides this. Proxy it, don't reimplement it.
- **Running embeddings on GPU:** With 4GB VRAM, run embeddings on CPU. all-MiniLM-L6-v2 is fast enough on CPU (~100ms per doc).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI-compatible API | Custom endpoint mimicking OpenAI format | Ollama's built-in `/v1/chat/completions` | Already implements Chat API, SSE streaming, token counting, `max_tokens` |
| Model inference | llama.cpp integration from scratch | Ollama | Handles GGUF loading, GPU offloading, chat templates, model management |
| Code file splitting | Custom regex-based splitting | LlamaIndex `CodeSplitter` | Handles function/class boundaries, language-aware parsing |
| Embedding storage | Custom vector math | ChromaDB | Persistent, local, zero-config vector store |
| API key auth | Custom token generation | `itsdangerous` or simple HMAC | Standard, secure, no database needed |

**Key insight:** Ollama's OpenAI-compatible API means your FastAPI wrapper is identical whether the backend is Ollama (RTX 1650) or vLLM (DGX H200). Only the `OLLAMA_URL` vs `VLLM_URL` changes.

## Common Pitfalls

### Pitfall 1: OOM from Model Too Large
**What goes wrong:** Pulling a 7B+ model causes Ollama to fail or fall back to CPU-only (very slow).
**Why it happens:** Q4 quantized 7B needs ~4-5GB VRAM. RTX 1650 has 4GB, but Windows desktop compositor uses ~0.5-1GB.
**How to avoid:** Use `qwen2.5-coder:1.5b` (Q4, ~1GB VRAM). Leave 2-3GB for Windows and other processes.
**Warning signs:** Ollama logs show "offloading to CPU" or generation speed drops below 1 token/sec.

### Pitfall 2: Slow Inference Speed
**What goes wrong:** 1.5B model generates 2-6 tokens/second — too slow for interactive use.
**Why it happens:** RTX 1650 has only 896 CUDA cores, 4GB GDDR5 (not GDDR6X).
**How to avoid:** Accept this for development. It's fine for building/testing the API. Use cloud resources (Colab) for quality testing.
**Warning signs:** Response takes 30+ seconds for 128 tokens.

### Pitfall 3: Windows GPU Memory Fragmentation
**What goes wrong:** Ollama can't allocate contiguous VRAM due to Windows DWM (Desktop Window Manager).
**Why it happens:** Windows reserves GPU memory for display output.
**How to avoid:** Close browser tabs, disable hardware acceleration in apps, run Ollama as admin if needed.
**Warning signs:** Ollama reports "partial offload" or "GPU memory insufficient" despite 4GB available.

### Pitfall 4: Embedding Model VRAM Conflict
**What goes wrong:** Running embedding model on GPU while Ollama is using GPU causes OOM.
**Why it happens:** Both compete for 4GB VRAM.
**How to avoid:** Force embeddings to CPU: `device="cpu"` in sentence-transformers. all-MiniLM-L6-v2 is fast on CPU.
**Warning signs:** CUDA OOM errors when RAG ingestion runs alongside Ollama.

### Pitfall 5: Context Window Too Large
**What goes wrong:** Setting context window to 32K causes OOM even with 1.5B model.
**Why it happens:** KV cache grows linearly with context length.
**How to avoid:** Set `num_ctx` to 4096 in Ollama Modelfile. Sufficient for code completion.
**Warning signs:** Generation fails mid-stream with "context length exceeded" or OOM.

## Code Examples

### Ollama Setup for RTX 1650
```bash
# Install Ollama from https://ollama.com/download/windows
# Pull 1.5B code model
ollama pull qwen2.5-coder:1.5b

# Create custom Modelfile with context window limit
echo "FROM qwen2.5-coder:1.5b
PARAMETER num_ctx 4096" > Modelfile

ollama create mosdac-coder -f Modelfile
ollama run mosdac-coder "def hello_world():"
```

### FastAPI Proxy with Streaming
```python
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
import httpx
import os

app = FastAPI()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
API_KEY = os.getenv("API_KEY", "dev-key-123")

async def verify_api_key(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, _: None = Depends(verify_api_key)):
    body = await request.json()
    body["model"] = "mosdac-coder"  # Force our model

    async with httpx.AsyncClient(timeout=120.0) as client:
        if body.get("stream"):
            async with client.stream(
                "POST", f"{OLLAMA_URL}/chat/completions", json=body
            ) as ollama_resp:
                async for chunk in ollama_resp.aiter_text():
                    yield chunk
        else:
            resp = await client.post(f"{OLLAMA_URL}/chat/completions", json=body)
            return resp.json()

@app.get("/health")
async def health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OLLAMA_URL}/models")
        models = resp.json().get("data", [])
        return {
            "status": "healthy",
            "model": "mosdac-coder",
            "available_models": [m["id"] for m in models],
        }
```

### RAG Ingestion for Code Files
```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import CodeSplitter
import chromadb

# CPU-only embedding model
Settings.embed_model = HuggingFaceEmbedding(
    model_name="all-MiniLM-L6-v2",
    device="cpu"
)

# ChromaDB setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("codebase")
vector_store = ChromaVectorStore(chroma_collection=collection)

# Code-aware splitting
splitter = CodeSplitter(
    language="python",
    chunk_lines=40,
    chunk_lines_overlap=10,
)

# Ingest
documents = SimpleDirectoryReader("./src").load_data()
nodes = splitter.get_nodes_from_documents(documents)
index = VectorStoreIndex(nodes, vector_store=vector_store)

print(f"Ingested {len(nodes)} code chunks")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual llama.cpp integration | Ollama as managed service | 2024+ | Zero config, built-in OpenAI API |
| FAISS for local vectors | ChromaDB | 2024+ | Persistent, simpler API, no manual serialization |
| Custom code splitting | LlamaIndex CodeSplitter | 2024+ | Language-aware, function/class boundaries |
| GPU embeddings | CPU embeddings (MiniLM) | 2024+ | No VRAM conflict, fast enough for local |

## Hardware-Specific Notes for RTX 1650

| Parameter | Value | Reason |
|-----------|-------|--------|
| Model | Qwen2.5-Coder-1.5B (Q4_K_M) | ~1GB VRAM, leaves 3GB for Windows |
| Context window | 4096 tokens | Fits in remaining VRAM after model load |
| GPU offload | All layers on GPU | 1.5B Q4 fits entirely in 4GB |
| Embeddings | CPU (all-MiniLM-L6-v2) | Avoids VRAM conflict with Ollama |
| Expected speed | 2-6 tokens/sec | Acceptable for development/testing |
| System RAM | 16GB recommended | Ollama uses RAM as overflow |

## Fine-Tuning Strategy (Cloud)

**Don't fine-tune on RTX 1650.** Use:
- **Google Colab (Free):** T4 GPU, 15GB VRAM, QLoRA 4-bit training
- **Kaggle Notebooks:** 2x T4, 30 hrs/week free
- **Process:** Train with QLoRA + bitsandbytes → export GGUF → pull to local Ollama

## Open Questions

1. **Whether 1.5B model quality is sufficient for production**
   - What we know: Good for basic code completion, struggles with complex architecture
   - What's unclear: Specific quality metrics for your use case
   - Recommendation: Build the API layer now, swap to larger model when DGX available

2. **Whether ChromaDB or FAISS is better for local dev**
   - What we know: ChromaDB is easier to set up; FAISS is lighter
   - What's unclear: Performance difference at scale
   - Recommendation: Start with ChromaDB, switch to FAISS if needed

## Sources

### Primary (HIGH confidence)
- [Ollama OpenAI Compatibility](https://docs.ollama.com/api/openai-compatibility) - Official API docs
- [Qwen2.5-Coder-1.5B on Ollama](https://ollama.com/library/qwen2.5-coder:1.5b) - Model page
- [LlamaIndex Local RAG with Chroma + Ollama](https://developers.llamaindex.ai/python/examples/cookbooks/local_rag_with_chroma_and_ollama/) - Official cookbook

### Secondary (MEDIUM confidence)
- [How to wrap Ollama API in FastAPI](https://medium.com/@vicgupta/how-to-wrap-the-ollama-api-in-a-fastapi-application-using-python-51ed2caa74bf) - Community patterns
- [Ollama + FastAPI on DEV.to](https://dev.to/shailendra_khade_df763b45/ollama-fastapi-api-building-my-ai-api-using-ollama-and-fastapi-on-a-linux-vm-5a40) - Tutorial patterns

### Tertiary (LOW confidence)
- Community Reddit threads on RTX 1650 performance — anecdotal, needs verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Ollama + Qwen2.5-Coder-1.5B is confirmed working on 4GB VRAM
- Architecture: HIGH - Proxy pattern is standard; Ollama provides OpenAI API natively
- Pitfalls: HIGH - VRAM constraints well-documented for 4GB GPUs
- RAG: MEDIUM - ChromaDB + LlamaIndex patterns verified but not tested on RTX 1650 specifically

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (Ollama release cadence is ~monthly)
