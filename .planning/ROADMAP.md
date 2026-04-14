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
- [x] **Phase 4: Data Loader** — Load scraped data into Neo4j (Complete)

  Plans:
  - [x] 04-01-PLAN.md — Data loader module creation ✓
- [ ] **Phase 5: LLM Client** — REST client for fine-tuned model API (Complete)
- [ ] **Phase 6: GraphRAG Pipeline** — Combine vector + graph retrieval
- [ ] **Phase 7: Q&A Interface** — User interface for queries

## Progress

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Web Scraper | Complete | 2/2 |
| 2. NLP Extraction | Complete | 3/3 |
| 3. Neo4j Schema | Complete | 2/2 |
| 4. Data Loader | Complete | 1/1 |
| 5. LLM Client | Complete | 1/1 ✓ |
| 6. GraphRAG | Pending | - |
| 7. Q&A Interface | Pending | - |