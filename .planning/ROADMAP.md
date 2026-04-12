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

  Plans:
  - [ ] 02-01-PLAN.md — NLP module setup + GLiNER entity extraction
  - [ ] 02-02-PLAN.md — Relationship extraction + entity normalization
  - [ ] 02-03-PLAN.md — Unified pipeline + process scraped data
- [ ] **Phase 3: Neo4j Schema** — Define graph schema and constraints

  Plans:
  - [ ] 03-01-PLAN.md — Neo4j client + node/relationship types
  - [ ] 03-02-PLAN.md — Constraints + indexes
- [ ] **Phase 4: Data Loader** — Load scraped data into Neo4j
- [ ] **Phase 5: Fine-tuned Model** — Fine-tune LLM for weather data
- [ ] **Phase 6: GraphRAG Pipeline** — Combine vector + graph retrieval
- [ ] **Phase 7: Q&A Interface** — User interface for queries

## Progress

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Web Scraper | gap_closure | 2 plans (01-01 complete, 01-02 gap closure) |
| 2. NLP Extraction | in_progress | 3 plans (02-01 to 02-03) |
| 3. Neo4j Schema | planned | 2 plans (03-01 to 03-02) |
| 4. Data Loader | - | - |
| 5. Fine-tune Model | - | - |
| 6. GraphRAG | - | - |
| 7. Q&A Interface | - | - |