# MOSDAC AI

A weather data knowledge graph system that combines web scraping, NLP entity extraction, Neo4j knowledge graph, and RAG (Retrieval-Augmented Generation) to provide accurate, grounded answers about ISRO/MOSDAC satellite data, sensors, and products.

## What This Is

MOSDAC AI is an intelligent Q&A system for weather data from [mosdac.gov.in](https://mosdac.gov.in) (ISRO's Meteorological and Oceanographic Satellite Data Archival Centre). It combines:

1. **Web Scraping** - Extract data from MOSDAC website (satellites, sensors, products, FAQs, documents)
2. **NLP Entity Extraction** - Use GLiNER for zero-shot entity recognition and spaCy for relationship extraction
3. **Neo4j Knowledge Graph** - Store structured graph with entities and their relationships
4. **LLM Client** - REST client for domain-specific code generation
5. **GraphRAG Pipeline** - Combine FAISS vector search + Neo4j graph traversal for context-aware answers

## Architecture

```
User Query
    ↓
LLM (intent understanding)
    ↓
FAISS Vector DB → relevant documents
    ↓
Neo4j Graph DB → relationships
    ↓
Combine context
    ↓
LLM → final answer
```

## Project Structure

```
mosdac_ai/
├── api/                        # FastAPI server (OpenAI-compatible API)
│   ├── main.py                 # FastAPI application
│   ├── proxy.py                # Ollama proxy endpoints
│   ├── health.py               # Health checks
│   ├── auth.py                 # API key authentication
│   └── config/settings.py      # Configuration
├── src/
│   ├── scraper/                # Web scraping module
│   │   ├── mosdac.py          # MOSDAC scraper implementation
│   │   └── config.py          # Scraper configuration
│   ├── nlp/                    # NLP processing module
│   │   ├── entities.py        # GLiNER entity extraction
│   │   ├── relations.py       # spaCy relationship extraction
│   │   ├── normalize.py       # Entity normalization (fuzzy matching)
│   │   ├── pipeline.py       # Unified NLP pipeline
│   │   └── config.py          # NLP configuration
│   ├── neo4j/                 # Neo4j knowledge graph module
│   │   ├── client.py         # Neo4j driver wrapper
│   │   ├── nodes.py          # Node type definitions
│   │   ├── relationships.py   # Relationship type definitions
│   │   ├── schema.py         # Schema setup (constraints, indexes)
│   │   └── loader.py         # Data loader for bulk imports
│   ├── rag/                   # RAG (Retrieval-Augmented Generation)
│   │   ├── index.py          # FAISS vector index
│   │   ├── ingest.py         # Code chunking
│   │   ├── cache.py          # Embedding cache
│   │   └── pipeline.py       # RAG pipeline with injection defense
│   ├── llm/                   # LLM client
│   │   └── client.py         # REST client for fine-tuned model
│   ├── gateway/               # Alternative API gateway
│   │   ├── main.py           # Gateway FastAPI app
│   │   ├── auth.py           # API key auth
│   │   ├── rate_limiter.py  # Rate limiting
│   │   └── proxy.py         # Proxy to LLM
│   └── core/                 # Core utilities
│       ├── logging.py        # Logging configuration
│       └── redis.py         # Redis integration
├── .planning/                 # Project planning (GSD methodology)
│   ├── PROJECT.md            # Project definition
│   ├── ROADMAP.md            # Phase roadmap
│   ├── STATE.md              # Current project state
│   └── phases/               # Phase plans and summaries
├── pyproject.toml            # Python project configuration
└── README.md                 # This file
```

## Features Implemented

### ✅ Phase 1: Web Scraper
- Scrapes satellites, sensors, products, FAQs, documents from mosdac.gov.in
- Uses BeautifulSoup + Selenium for dynamic content
- Rate limiting and retry logic
- Saves data as JSON files

### ✅ Phase 2: NLP Entity Extraction
- GLiNER zero-shot NER for domain-specific entities (SATELLITE, SENSOR, PRODUCT)
- spaCy dependency parsing for relationship extraction
- Entity normalization with fuzzy matching (rapidfuzz)
- Unified pipeline for processing all scraped data

### ✅ Phase 3: Neo4j Schema
- Node types: Satellite, Sensor, Product, Document, FAQ
- Relationship types: PROVIDES, USES, MEASURES, LOCATED_AT, ANSWERS
- Constraints and indexes for performance

### ✅ Phase 4: Data Loader
- Bulk import of scraped JSON data into Neo4j
- Creates nodes and relationships from NLP output

### 🔄 Phase 5: LLM Client (In Progress)
- REST client for fine-tuned model API
- Authentication and health checks

### ⏳ Phase 6: GraphRAG Pipeline
- FAISS vector index for document embeddings
- Combined retrieval from vector + graph

### ⏳ Phase 7: Q&A Interface
- FastAPI server with OpenAI-compatible endpoints
- RAG-enriched prompt generation

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mosdac_ai.git
cd mosdac_ai

# Install dependencies
pip install -e .

# Install RAG dependencies (optional)
pip install -e ".[rag]"

# Install dev dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
```

## Configuration

Edit `.env` with your settings:

```bash
# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# LLM API (for Phase 5+)
LLM_API_KEY=your_api_key
LLM_API_URL=http://localhost:8000/v1

# Scraper Settings
MOSDAC_BASE_URL=https://mosdac.gov.in
OUTPUT_DIR=data/raw

# API Server
API_KEY=dev-key-123
PORT=8000
```

## Usage

### 1. Run Web Scraper

```python
from src.scraper.mosdac import MOSDACScraper

with MOSDACScraper() as scraper:
    outputs = scraper.scrape_all()
    # Saves: satellites.json, sensors.json, products.json, faqs.json, documents.json
```

### 2. Run NLP Pipeline

```python
from src.nlp.pipeline import MOSDACPipeline, process_all_scraped_data

# Process all scraped data
result = process_all_scraped_data()
# Output: data/nlp/entities.json, relations.json, combined.json
```

### 3. Load Data into Neo4j

```python
from src.neo4j.loader import DataLoader
from src.neo4j.client import Neo4jClient

client = Neo4jClient()
loader = DataLoader(client)

# Load entities
loader.load_entities("data/nlp/entities.json")

# Load relationships
loader.load_relations("data/nlp/relations.json")
```

### 4. Start API Server

```bash
# From project root
python -m api.main

# Or with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/v1/chat/completions` | POST | Chat completion (RAG-enabled) |
| `/v1/completions` | POST | Text completion |
| `/v1/models` | GET | List available models |

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "What satellites does MOSDAC use?"}],
    "stream": false
  }'
```

Using OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dev-key-123"
)

response = client.chat.completions.create(
    model="llama3",
    messages=[{"role": "user", "content": "What is INSAT-3D used for?"}]
)
print(response.choices[0].message.content)
```

## Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Development

```bash
# Run tests
pytest

# Lint code
ruff check .

# Format code
ruff format .
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web Scraping | BeautifulSoup, Selenium |
| NLP | GLiNER, spaCy, rapidfuzz |
| Knowledge Graph | Neo4j |
| Vector Search | FAISS, sentence-transformers |
| API Server | FastAPI, Uvicorn |
| Gateway | Rate limiting (slowapi), Redis |
| LLM Integration | Ollama (local) / REST API |

## Progress

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Web Scraper | ✅ Complete | 2/2 |
| 2. NLP Extraction | ✅ Complete | 3/3 |
| 3. Neo4j Schema | ✅ Complete | 2/2 |
| 4. Data Loader | ✅ Complete | 1/1 |
| 5. LLM Client | 🔄 In Progress | 1 plan |
| 6. GraphRAG | ⏳ Pending | - |
| 7. Q&A Interface | ⏳ Pending | - |

## Requirements

- Python 3.11+
- Neo4j Desktop (for knowledge graph)
- [Ollama](https://ollama.com/) (optional, for local LLM)

## License

MIT License

---

*For detailed phase plans and progress, see `.planning/ROADMAP.md`*