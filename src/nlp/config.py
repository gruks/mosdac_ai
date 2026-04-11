"""NLP configuration for MOSDAC entity extraction."""

import os

# Entity labels for MOSDAC domain
ENTITY_LABELS = ["SATELLITE", "SENSOR", "PRODUCT"]

# Relation types between entities
RELATION_TYPES = ["PROVIDES", "USES", "LOCATED_AT", "MEASURES"]

# GLiNER model configuration
GLiNER_MODEL = os.getenv("GLINER_MODEL", "urchade/gliner_medium-v2.1")

# spaCy model configuration
SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")

# Entity threshold for extraction confidence
ENTITY_THRESHOLD = float(os.getenv("ENTITY_THRESHOLD", "0.3"))

# Maximum text length for entity extraction
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "512"))
