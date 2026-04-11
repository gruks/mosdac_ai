"""MOSDAC NLP Module - Entity extraction and normalization utilities."""

import os
import sys
from typing import TYPE_CHECKING

# NLP module initialization
__version__ = "0.1.0"

# Import main components - handle both package and standalone import scenarios
try:
    from src.nlp.entities import EntityExtractor
    from src.nlp.config import ENTITY_LABELS, RELATION_TYPES, GLiNER_MODEL, SPACY_MODEL
except ImportError:
    # Fallback for when running as standalone script
    from nlp.entities import EntityExtractor
    from nlp.config import ENTITY_LABELS, RELATION_TYPES, GLiNER_MODEL, SPACY_MODEL


class MOSDACNLPModule:
    """Main NLP module for MOSDAC entity extraction."""

    def __init__(self):
        """Initialize the NLP module with entity extractor."""
        self.entity_extractor = EntityExtractor()
        self.entity_labels = ENTITY_LABELS
        self.relation_types = RELATION_TYPES

    def extract_all(self, text: str):
        """Extract all entity types from text."""
        return self.entity_extractor.extract_all(text)

    def extract_satellites(self, text: str):
        """Extract satellite entities from text."""
        return self.entity_extractor.extract_satellites(text)

    def extract_sensors(self, text: str):
        """Extract sensor entities from text."""
        return self.entity_extractor.extract_sensors(text)

    def extract_products(self, text: str):
        """Extract product entities from text."""
        return self.entity_extractor.extract_products(text)


# Module-level extractor instance
_extractor: EntityExtractor | None = None


def get_extractor() -> EntityExtractor:
    """Get or create the global EntityExtractor instance."""
    global _extractor
    if _extractor is None:
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
