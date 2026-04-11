---
phase: 02-nlp-extraction
plan: 02
subsystem: nlp
tags: [spacy, rapidfuzz, normalization, relations, entity-linking]

# Dependency graph
requires:
  - phase: 01-web-scraper
    provides: Raw data (satellites, sensors, products)
provides:
  - src/nlp/relations.py - Relationship extraction via dependency parsing
  - src/nlp/normalize.py - Entity normalization to canonical forms
affects: [02-nlp-extraction, 03-neo4j-schema]

# Tech tracking
tech-stack:
  added: [spacy, rapidfuzz]
  patterns: [dependency-parsing-relations, fuzzy-matching-normalization]

key-files:
  created: [src/nlp/relations.py, src/nlp/normalize.py]
  modified: [src/nlp/__init__.py]

key-decisions:
  - "Used spaCy dependency parsing for SVO patterns"
  - "Fuzzy threshold 85 balances precision/recall"
  - "Made NLP module defensive to missing GLiNER"

# Metrics
duration: 7min
completed: 2026-04-11
---

# Phase 2 Plan 2: NLP Extraction - Relationships & Normalization Summary

**Relationship extraction using spaCy dependency parsing and entity normalization with fuzzy matching**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-11T09:57:23Z
- **Completed:** 2026-04-11T10:04:47Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented `RelationExtractor` for extracting PROVIDES/USES/LOCATED_AT/MEASURES relationships
- Implemented `EntityNormalizer` with SATELLITES/SENSORS/PRODUCTS mapping tables
- Added fuzzy matching (rapidfuzz) with 85% threshold for typo handling

## Task Commits

1. **Task 1: Relationship extraction** - `2bdbe42` (feat)
2. **Task 2: Entity normalization** - `eb93a37` (feat)
3. **Init fix** - `772ea02` (fix)

_Plan metadata: commit (docs: complete plan)_

## Files Created/Modified
- `src/nlp/relations.py` - Relationship extraction using spaCy dependency parsing
- `src/nlp/normalize.py` - Entity normalization with canonical mapping tables
- `src/nlp/__init__.py` - Made defensive for missing GLiNER

## Decisions Made
- Used spaCy dependency parsing for subject-verb-object patterns
- Set fuzzy threshold at 85 to avoid over-normalization
- Made NLP module defensive to handle missing GLiNER dependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed broken pip environment**
- **Found during:** Task 1 verification
- **Issue:** Python 3.13 had corrupted pip packages, spacy couldn't load
- **Fix:** Used Python 3.11 from AppData\Local\Programs\Python\Python311
- **Files modified:** Environment path
- **Verification:** spaCy model loads, tests pass
- **Committed in:** 2bdbe42

**2. [Rule 2 - Missing Critical] Fixed nlp/__init__.py import failure**
- **Found during:** Verification of relations module  
- **Issue:** __init__.py tried importing non-existent entities module
- **Fix:** Made imports defensive, fallback defaults for missing GLiNER
- **Files modified:** src/nlp/__init__.py
- **Verification:** Relations and normalize modules load correctly
- **Committed in:** 772ea02

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both fixes needed to verify and run NLP code. No scope creep.

## Issues Encountered
- None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Relations and normalization ready for Neo4j schema integration
- Ready for entity linking pipeline (Plan 02-03)

---
*Phase: 02-nlp-extraction*
*Completed: 2026-04-11*