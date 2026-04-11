"""GLiNER-based entity extraction for MOSDAC data."""

from typing import List, Dict, Any, Optional

from gliner import GLiNER

from src.nlp.config import (
    ENTITY_LABELS,
    GLiNER_MODEL,
    ENTITY_THRESHOLD,
    MAX_TEXT_LENGTH,
)


class EntityExtractor:
    """Extract satellite, sensor, and product entities from text using GLiNER."""

    def __init__(self, model_name: str | None = None, threshold: float | None = None):
        """Initialize the entity extractor with GLiNER model.

        Args:
            model_name: GLiNER model to use (defaults to config value)
            threshold: Confidence threshold for entity extraction
        """
        self.model_name = model_name or GLiNER_MODEL
        self.threshold = threshold or ENTITY_THRESHOLD
        self._model: GLiNER | None = None

    @property
    def model(self) -> GLiNER:
        """Lazy-load the GLiNER model."""
        if self._model is None:
            try:
                self._model = GLiNER.from_pretrained(self.model_name)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load GLiNER model '{self.model_name}': {e}"
                )
        return self._model

    def _truncate_text(self, text: str) -> str:
        """Truncate text to maximum length."""
        if len(text) > MAX_TEXT_LENGTH:
            return text[:MAX_TEXT_LENGTH]
        return text

    def _parse_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Parse entity dict to ensure consistent format."""
        return {
            "text": entity.get("word", entity.get("text", "")),
            "label": entity.get("label", ""),
            "start": entity.get("start", 0),
            "end": entity.get("end", 0),
        }

    def _filter_by_label(
        self, entities: List[Dict[str, Any]], label: str
    ) -> List[Dict[str, Any]]:
        """Filter entities by label."""
        return [e for e in entities if e.get("label") == label]

    def extract_all(self, text: str) -> List[Dict[str, Any]]:
        """Extract all entity types from text.

        Args:
            text: Input text to extract entities from

        Returns:
            List of extracted entities with text, label, start, end
        """
        if not text or not text.strip():
            return []

        try:
            text = self._truncate_text(text)
            entities = self.model.predict_entities(
                text, ENTITY_LABELS, threshold=self.threshold
            )
            return [self._parse_entity(e) for e in entities]
        except Exception:
            # Handle model failure gracefully - return empty list
            return []

    def extract_satellites(self, text: str) -> List[Dict[str, Any]]:
        """Extract satellite entities from text.

        Args:
            text: Input text to extract satellite entities from

        Returns:
            List of satellite entities (INSAT-3D, SCATSAT-1, etc.)
        """
        all_entities = self.extract_all(text)
        return self._filter_by_label(all_entities, "SATELLITE")

    def extract_sensors(self, text: str) -> List[Dict[str, Any]]:
        """Extract sensor entities from text.

        Args:
            text: Input text to extract sensor entities from

        Returns:
            List of sensor entities (Imager, Sounder, etc.)
        """
        all_entities = self.extract_all(text)
        return self._filter_by_label(all_entities, "SENSOR")

    def extract_products(self, text: str) -> List[Dict[str, Any]]:
        """Extract product entities from text.

        Args:
            text: Input text to extract product entities from

        Returns:
            List of product entities (weather data products)
        """
        all_entities = self.extract_all(text)
        return self._filter_by_label(all_entities, "PRODUCT")

    def extract_by_type(self, text: str, entity_type: str) -> List[Dict[str, Any]]:
        """Extract entities of a specific type.

        Args:
            text: Input text to extract entities from
            entity_type: Specific entity type to extract (SATELLITE, SENSOR, PRODUCT)

        Returns:
            List of entities matching the specified type
        """
        if entity_type not in ENTITY_LABELS:
            return []

        all_entities = self.extract_all(text)
        return self._filter_by_label(all_entities, entity_type)


# Module-level convenience functions
def extract_entities(text: str) -> List[Dict[str, Any]]:
    """Extract all entities from text.

    Args:
        text: Input text to extract entities from

    Returns:
        List of extracted entities
    """
    extractor = EntityExtractor()
    return extractor.extract_all(text)


def extract_satellites(text: str) -> List[Dict[str, Any]]:
    """Extract satellite entities from text."""
    extractor = EntityExtractor()
    return extractor.extract_satellites(text)


def extract_sensors(text: str) -> List[Dict[str, Any]]:
    """Extract sensor entities from text."""
    extractor = EntityExtractor()
    return extractor.extract_sensors(text)


def extract_products(text: str) -> List[Dict[str, Any]]:
    """Extract product entities from text."""
    extractor = EntityExtractor()
    return extractor.extract_products(text)
