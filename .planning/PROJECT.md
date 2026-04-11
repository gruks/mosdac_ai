# MOSDAC GraphRAG - Knowledge Graph + Fine-tuned LLM

## What This Is

A weather data knowledge graph system that combines:
1. **Web Scraping** - Data from mosdac.gov.in (satellites, sensors, products)
2. **NLP Entity Extraction** - Extract entities/relationships from raw text
3. **Neo4j Knowledge Graph** - Store structured graph with relationships
4. **Fine-tuned LLM** - Domain-specific code generation for weather data
5. **GraphRAG** - Combine vector search + graph traversal for answers

## Core Value

Weather data Q&A system that understands satellite relationships, products, and applications - delivers accurate, grounded answers using Knowledge Graph + LLM.

## Architecture

```
User Query
   ↓
LLM (intent understanding)
   ↓
Vector DB → relevant documents
   ↓
Graph DB (Neo4j) → relationships
   ↓
Combine context
   ↓
LLM → final answer
```

## Constraints

- **Data Source**: mosdac.gov.in (ISRO weather data)
- **Graph**: Neo4j Desktop (localhost)
- **LLM**: Fine-tuned model for weather data queries
- **RAG**: FAISS for document embeddings + Neo4j for graph context

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Neo4j for Knowledge Graph | Relationships are first-class | TODO |
| GraphRAG Pipeline | Combines vector + graph retrieval | TODO |
| Domain fine-tuning | Weather-specific answers | TODO |

---
*Created: 2026-04-11 for MOSDAC project*