"""MOSDAC NLP Module - Entity extraction and normalization utilities."""

import os
import sys
from typing import TYPE_CHECKING

# NLP module initialization
__version__ = "0.1.0"

# Import main components - handle both package and standalone import scenarios
try:
    from src.nlp.config import ENTITY_LABELS, RELATION_TYPES, GLiNER_MODEL, SPACY_MODEL
except ImportError:
    try:
        from nlp.config import ENTITY_LABELS, RELATION_TYPES, GLiNER_MODEL, SPACY_MODEL
    except ImportError:
        ENTITY_LABELS = ["SATELLITE", "SENSOR", "PRODUCT"]
        RELATION_TYPES = ["PROVIDES", "USES", "LOCATED_AT", "MEASURES"]
        GLiNER_MODEL = "urchade/gliner_medium-v2.1"
        SPACY_MODEL = "en_core_web_sm"

# EntityExtractor may not be available without GLiNER
EntityExtractor = None
try:
    from src.nlp.entities import EntityExtractor
except ImportError:
    try:
        from nlp.entities import EntityExtractor
    except ImportError:
        pass


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
