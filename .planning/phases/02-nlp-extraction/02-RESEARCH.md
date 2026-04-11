# Phase 02: NLP Entity Extraction - Research

**Researched:** 2026-04-11
**Domain:** Named Entity Recognition, Relationship Extraction, Entity Normalization
**Confidence:** MEDIUM-HIGH

## Summary

This phase implements NLP entity extraction from scraped MOSDAC data to identify satellites, sensors, products, and their relationships. The recommended approach uses **GLiNER** (or GLiNER2) for zero-shot entity extraction, which allows defining custom entity types (SATELLITE, SENSOR, PRODUCT) without training data. This is ideal for the specialized meteorology/satellite domain where pre-trained models won't recognize domain-specific entities like INSAT-3D or SCATSAT-1. For relationship extraction, a rule-based approach using dependency parsing (via spaCy) is practical since the domain has finite, predictable relationship patterns. Entity normalization can use fuzzy matching with dedupe or custom mapping tables.

**Primary recommendation:** Use GLiNER for zero-shot NER with custom entity labels: SATELLITE, SENSOR, PRODUCT. Use spaCy dependency parsing for relationship extraction. Implement normalization via mapping tables and fuzzy matching.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| gliner | 0.2.x | Zero-shot NER for custom entity types | Extracts any entity type without training - perfect for domain-specific satellites/sensors |
| spacy | 3.x | NLP pipeline, dependency parsing | Industry standard, fast, production-ready |
| torch | 2.x | Transformer inference backend | Required for GLiNER model inference |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dedupe | 3.x | Fuzzy matching, entity resolution | When entity variants require clustering |
| rapidfuzz | 3.x | Fast fuzzy string matching | For simple entity normalization |
| networkx | 3.x | Graph data structure | For relationship triples storage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GLiNER | spaCy pretrained models | spaCy only recognizes standard entities (PERSON, ORG), misses domain-specific |
| GLiNER | Hugging Face pipelines | More flexible but less performant for zero-shot |
| GLiNER2 | GLiNER | GLiNER2 adds relation extraction but is newer (Nov 2025), less tested |

**Installation:**
```bash
pip install gliner spacy torch dedupe rapidfuzz networkx
python -m spacy download en_core_web_sm
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── nlp/
│   ├── __init__.py
│   ├── config.py          # Entity labels, relation types
│   ├── entities.py       # Entity extraction using GLiNER
│   ├── relations.py      # Relationship extraction
│   ├── normalize.py      # Entity normalization
│   └── pipeline.py       # Combined extraction pipeline
```

### Pattern 1: GLiNER Zero-Shot Entity Extraction
**What:** Use GLiNER with custom entity labels to extract domain-specific entities without training
**When to use:** Domain has entities not in standard NER datasets (satellites, sensors, products)
**Example:**
```python
from gliner import GLiNER

# Load model once at startup
model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")

# Define entity labels for MOSDAC domain
labels = ["SATELLITE", "SENSOR", "PRODUCT", "ORGANIZATION"]

# Extract entities from text
text = "INSAT-3D is a weather satellite equipped with Imager and Sounder sensors."
entities = model.predict_entities(text, labels)

# Result: [{'text': 'INSAT-3D', 'label': 'SATELLITE', 'start': 0, 'end': 8}, ...]
```

### Pattern 2: spaCy Relationship Extraction
**What:** Use dependency parsing to extract subject-verb-object triples for relationship extraction
**When to use:** Relationships follow predictable patterns (PROVIDES, USES, LOCATED_AT)
**Example:**
```python
import spacy
nlp = spacy.load("en_core_web_sm")

def extract_relations(doc):
    """Extract relation triples from spaCy doc."""
    relations = []
    for token in doc:
        # Find subject-verb-object patterns
        if token.dep_ in ("nsubj", "nsubjpass") and token.head.pos_ == "VERB":
            subject = token.text
            verb = token.head.text
            for child in token.head.children:
                if child.dep_ in ("dobj", "pobj"):
                    relations.append((subject, verb, child.text))
    return relations
```

### Pattern 3: Entity Normalization with Mapping Tables
**What:** Use predefined mapping + fuzzy matching for entity variants
**When to use:** Known entity variants (e.g., "INSAT 3D" → "INSAT-3D")
**Example:**
```python
from rapidfuzz import fuzz
from typing import Optional

# Known canonical names
CANONICAL_NAMES = {
    "satellites": {
        "INSAT-3D": ["insat-3d", "INSAT 3D", "INSAT3D", "insat3d"],
        "INSAT-3DR": ["insat-3dr", "INSAT 3DR"],
        "SCATSAT-1": ["scatsat-1", "SCATSAT 1"],
    },
    "sensors": {
        "Imager": ["Imager", "IMAGER", "imager"],
        "Sounder": ["Sounder", "SOUNDER", "sounder"],
    }
}

def normalize_entity(text: str, entity_type: str) -> Optional[str]:
    """Normalize entity to canonical form."""
    text_lower = text.lower().strip()
    canonical_map = CANONICAL_NAMES.get(entity_type, {})
    for canonical, variants in canonical_map.items():
        # Exact match
        if text_lower in [v.lower() for v in variants]:
            return canonical
        # Fuzzy match for typos
        for variant in variants:
            if fuzz.ratio(text_lower, variant.lower()) > 90:
                return canonical
    return None
```

### Anti-Patterns to Avoid
- **Training custom spaCy model:** Requires labeled data, maintenance overhead. Use GLiNER zero-shot instead.
- **Using LLM for extraction:** Overkill for structured domain, expensive, slow. Use GLiNER for CPU-efficient extraction.
- **No entity normalization:** Leads to duplicates like "INSAT-3D" and "insat3d" as separate entities.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unknown entity types | Train custom NER model | GLiNER zero-shot | No training data needed, works with any entity type |
| Relationship extraction | Fine-tune transformer | spaCy dependency parsing | Predictable patterns in domain, no labeling needed |
| Fuzzy matching | Write Levenshtein from scratch | rapidfuzz | Optimized implementation, handles edge cases |
| Entity resolution | Build custom clustering | dedupe library | Handles blocking, training for best matches |

**Key insight:** The meteorology domain has finite, predictable entities. GLiNER zero-shot handles new entity types without retraining. spaCy dependency parsing works for predictable relationship patterns without labeled data.

## Common Pitfalls

### Pitfall 1: Entity Type Mismatch
**What goes wrong:** GLiNER returns entities with wrong labels (PRODUCT labeled as SATELLITE)
**Why it happens:** Ambiguous entities (e.g., "Data" could be product or concept)
**How to avoid:** Post-process with domain rules, validate entity text against known lists
**Warning signs:** Check entity text against known satellite/sensor/product lists

### Pitfall 2: Relationship Span Breaking
**What goes wrong:** Relationships span across multiple sentences not captured
**Why it happens:** Dependency parsing limited to single-sentence processing
**How to avoid:** Group entities by document/section before relation extraction
**Warning signs:** Relationship count drops significantly for multi-sentence paragraphs

### Pitfall 3: Normalization Over-Normalization
**What goes wrong:** Legitimate different entities merged (e.g., INSAT-3D and INSAT-3DR treated as same)
**Why it happens:** Fuzzy threshold too high, mapping table too aggressive
**How to avoid:** Use case-sensitive matching for known canonical forms
**Warning signs:** Entity count drops after normalization

### Pitfall 4: GPU Memory
**What goes wrong:** Transformer model OOM on limited GPU
**Why it happens:** GLiNER loads full transformer (400M params)
**How to avoid:** Use smaller model variant (gliner_small instead of gliner_large)
**Warning signs:** CUDA out of memory errors

## Code Examples

### Combined Entity + Relationship Extraction Pipeline
```python
"""Full NLP extraction pipeline."""
from gliner import GLiNER
import spacy
from typing import List, Dict, Any

class MOSDACExtractor:
    """Extract entities and relationships from MOSDAC text."""
    
    ENTITY_LABELS = ["SATELLITE", "SENSOR", "PRODUCT", "ORGANIZATION"]
    RELATION_TYPES = ["PROVIDES", "USES", "LOCATED_AT", "MEASURES"]
    
    def __init__(self):
        # GLiNER for entities
        self.gliner = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        # spaCy for parsing
        self.spacy = spacy.load("en_core_web_sm")
    
    def extract(self, text: str) -> Dict[str, Any]:
        """Extract entities and relationships."""
        # 1. Extract entities
        entities = self.gliner.predict_entities(text, self.ENTITY_LABELS)
        
        # 2. Extract relationships using dependency parsing
        doc = self.spacy(text)
        relations = self._extract_relations(doc, entities)
        
        return {"entities": entities, "relations": relations}
    
    def _extract_relations(self, doc, entities):
        """Extract relationships between entities."""
        relations = []
        for token in doc:
            if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                if token.head.lemma_.lower() in self.RELATION_TYPES:
                    for child in token.head.children:
                        if child.dep_ == "dobj":
                            relations.append({
                                "subject": token.text,
                                "relation": token.head.lemma_,
                                "object": child.text
                            })
        return relations

# Usage
extractor = MOSDACExtractor()
result = extractor.extract(
    "INSAT-3D provides Imager and Sounder sensors for weather monitoring."
)
# Returns: {entities: [...], relations: [...]}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| spaCy pretrained NER | GLiNER zero-shot | 2024 | Can now extract custom entities without training |
| Separate NER + RE pipelines | GLiNER2 unified | Nov 2025 | Single model does NER + RE + classification |
| LLM extraction | GLiNER CPU-efficient | 2024 | No GPU required, faster, cheaper |

**Deprecated/outdated:**
- **spaCy-only NER:** Can't handle domain-specific entities like INSAT-3D without custom training
- **Training custom models:** Requires labeled data, ongoing maintenance
- **ChatGPT/API extraction:** Expensive, slow, not suitable for batch processing

## Open Questions

1. **Model size selection**
   - What we know: GLiNER available in small (250M), medium (350M), large (400M) parameters
   - What's unclear: Whether medium provides enough accuracy on domain text
   - Recommendation: Start with medium, downgrade to small if OOM issues

2. **Relationship pattern coverage**
   - What we know: Domain relationships (PROVIDES, USES) seem consistent
   - What's unclear: How many relation types actually appear in scraped data
   - Recommendation: Analyze sample data first, expand pattern list as needed

3. **Entity canonical forms**
   - What we know: Need normalization for INSAT variants
   - What's unclear: Complete list of canonical satellite names
   - Recommendation: Build mapping table incrementally from extraction results

## Sources

### Primary (HIGH confidence)
- GLiNER GitHub (https://github.com/urchade/GLiNER) - Library documentation, examples
- spaCy v3 documentation (https://spacy.io/api/entityrecognizer) - NER component API

### Secondary (MEDIUM confidence)
- "How to Build a Named Entity Recognition Pipeline with spaCy and Transformers" (agentbus.sh, Feb 2026) - Architecture comparison
- "GLiNER2: Extracting Structured Information from Text" (Towards Data Science, Jan 2026) - GLiNER2 evaluation
- spaCy relation extraction blog (explosion.ai, Mar 2025) - Relationship patterns

### Tertiary (LOW confidence)
- Python NER libraries comparison (LinkedIn, Aug 2025) - General landscape

## Metadata

**Confidence breakdown:**
- Standard Stack: MEDIUM - Verified GLiNER works for zero-shot, but specific model versions need validation
- Architecture: HIGH - Pattern-based approach well-documented
- Pitfalls: MEDIUM - Domain-specific issues may emerge during implementation

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days - stable domain)