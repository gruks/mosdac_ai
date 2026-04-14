"""MOSDAC NLP Module - Entity extraction and normalization utilities."""

import os
import sys
from typing import TYPE_CHECKING

# NLP module initialization
__version__ = "0.1.0"

# Import config directly - avoid triggering package imports
config_code = """
import os

ENTITY_LABELS = ["SATELLITE", "SENSOR", "PRODUCT"]
RELATION_TYPES = ["PROVIDES", "USES", "LOCATED_AT", "MEASURES"]
GLiNER_MODEL = os.getenv("GLINER_MODEL", "urchade/gliner_medium-v2.1")
SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")
"""

# Execute config code in a separate namespace
_config_ns = {}
try:
    exec(config_code, _config_ns)
    ENTITY_LABELS = _config_ns.get("ENTITY_LABELS", ["SATELLITE", "SENSOR", "PRODUCT"])
    RELATION_TYPES = _config_ns.get(
        "RELATION_TYPES", ["PROVIDES", "USES", "LOCATED_AT", "MEASURES"]
    )
    GLiNER_MODEL = _config_ns.get("GLiNER_MODEL", "urchade/gliner_medium-v2.1")
    SPACY_MODEL = _config_ns.get("SPACY_MODEL", "en_core_web_sm")
except Exception:
    ENTITY_LABELS = ["SATELLITE", "SENSOR", "PRODUCT"]
    RELATION_TYPES = ["PROVIDES", "USES", "LOCATED_AT", "MEASURES"]
    GLiNER_MODEL = "urchade/gliner_medium-v2.1"
    SPACY_MODEL = "en_core_web_sm"

# EntityExtractor - lazy load with try/except
EntityExtractor = None


def _get_entity_extractor():
    """Get EntityExtractor class with lazy loading."""
    global EntityExtractor
    if EntityExtractor is None:
        try:
            # Direct file import to avoid __init__.py triggering
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "entities", "src/nlp/entities.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            EntityExtractor = module.EntityExtractor
        except Exception:
            pass
    return EntityExtractor


class MOSDACNLPModule:
    """Main NLP module for MOSDAC entity extraction."""

    def __init__(self):
        """Initialize the NLP module with entity extractor."""
        self.entity_extractor = EntityExtractor() if EntityExtractor else None
        self.entity_labels = ENTITY_LABELS
        self.relation_types = RELATION_TYPES

    def extract_all(self, text: str):
        """Extract all entity types from text."""
        if self.entity_extractor:
            return self.entity_extractor.extract_all(text)
        return []

    def extract_satellites(self, text: str):
        """Extract satellite entities from text."""
        if self.entity_extractor:
            return self.entity_extractor.extract_satellites(text)
        return []

    def extract_sensors(self, text: str):
        """Extract sensor entities from text."""
        if self.entity_extractor:
            return self.entity_extractor.extract_sensors(text)
        return []

    def extract_products(self, text: str):
        """Extract product entities from text."""
        if self.entity_extractor:
            return self.entity_extractor.extract_products(text)
        return []


# Module-level extractor instance
_extractor = None


def get_extractor():
    """Get or create the global EntityExtractor instance."""
    global _extractor
    if _extractor is None and EntityExtractor:
        _extractor = EntityExtractor()
    return _extractor


# Exports
__all__ = [
    "MOSDACNLPModule",
    "EntityExtractor",
    "ENTITY_LABELS",
    "RELATION_TYPES",
    "GLiNER_MODEL",
    "SPACY_MODEL",
    "get_extractor",
]
