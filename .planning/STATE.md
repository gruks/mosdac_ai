# MOSDAC Project State

## Current Position

Phase: 6 of 7 (GraphRAG Pipeline)
Status: Ready

## Progress

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Web Scraper | Complete | 2/2 |
| 2. NLP Extraction | Complete | 3/3 |
| 3. Neo4j Schema | Complete | 2/2 |
| 4. Data Loader | Complete | 1/1 |
| 5. Fine-tune Model | Complete | 1/1 |
| 6. GraphRAG | Pending | - |
| 7. Q&A Interface | Pending | - |

---

## Decisions

- Used os.getenv instead of pydantic-settings for Python 3.13 compatibility
- Used attribute-style config (CAPS) for cleaner access in config.py
- Fixed JSON double-nesting by flattening nested lists in _save_json
- Removed hardcoded fallback data from scraper (empty list returns)
- Enabled Selenium for all dynamic content scraping
- Used GLiNER zero-shot NER for domain-specific entity extraction
- Used spaCy dependency parsing for relationship extraction
- Used rapidfuzz for fuzzy entity matching (85% threshold)
- Made NLP module defensive to handle missing GLiNER
- Used defensive imports for pipeline components
- Added logging configuration for debugging
- Fixed numpy 2.x DLL issue with numpy 1.26.4
- **Phase 3: Created Neo4j schema (client, nodes, relationships) for knowledge graph**
- **Phase 3 Plan 2: Added schema setup with constraints and indexes**
- **Phase 4 Plan 1: Created Neo4j DataLoader for bulk importing scraped JSON**
- **Phase 5 Plan 1: Created LLM client for REST API with Bearer token auth**

---

*Updated: 2026-04-14*
*Last session: Completed 05-01 plan (LLM Client)*