# Roadmap: MOSDAC GraphRAG

## Overview

Weather data knowledge graph system combining:
- Web scraping from mosdac.gov.in
- NLP entity extraction
- Neo4j knowledge graph
- Fine-tuned LLM for weather queries
- GraphRAG (vector + graph retrieval)

## Key Architecture

```
User Query → LLM Intent → Vector DB → Graph DB → Combine → LLM Answer
```

## Phases

- [ ] **Phase 1: Web Scraper** — Scrape data from mosdac.gov.in
- [ ] **Phase 2: NLP Entity Extraction** — Extract entities/relationships from text
- [ ] **Phase 3: Neo4j Schema** — Define graph schema and constraints
- [ ] **Phase 4: Data Loader** — Load scraped data into Neo4j
- [ ] **Phase 5: Fine-tuned Model** — Fine-tune LLM for weather data
- [ ] **Phase 6: GraphRAG Pipeline** — Combine vector + graph retrieval
- [ ] **Phase 7: Q&A Interface** — User interface for queries

## Progress

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Web Scraper | gap_closure | 2 plans (01-01 complete, 01-02 gap closure) |
| 2. NLP Extraction | - | - |
| 3. Neo4j Schema | - | - |
| 4. Data Loader | - | - |
| 5. Fine-tune Model | - | - |
| 6. GraphRAG | - | - |
| 7. Q&A Interface | - | - |