# MOSDAC Project State

## Current Position

Phase: 2 of 7 (NLP Extraction)
Plan: 2 of 3 in current phase
Status: Completed

## Progress

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Web Scraper | Complete | 2/2 |
| 2. NLP Extraction | In Progress | 2/3 |
| 3. Neo4j Schema | Pending | - |
| 4. Data Loader | Pending | - |
| 5. Fine-tune Model | Pending | - |
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

---

*Updated: 2026-04-11*
*Last session: Completed 02-nlp-extraction-02 plan*