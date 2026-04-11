"""Entity normalization with mapping tables and fuzzy matching for MOSDAC."""

from typing import Any

from rapidfuzz import fuzz


# Canonical entity mapping tables
SATELLITES: dict[str, str] = {
    # Canonical -> Display
    "INSAT-3D": "INSAT-3D",
    "INSAT-3DR": "INSAT-3DR",
    "INSAT-3A": "INSAT-3A",
    "INSAT-3DS": "INSAT-3DS",
    "SCATSAT-1": "SCATSAT-1",
    "KALPANA-1": "Kalpana-1",
    "KALPANA1": "Kalpana-1",
    # Variants
    "INSAT 3D": "INSAT-3D",
    "INSAT-3D": "INSAT-3D",
    "INSAT 3DR": "INSAT-3DR",
    "INSAT-3DR": "INSAT-3DR",
    "INSAT 3A": "INSAT-3A",
    "INSAT-3A": "INSAT-3A",
    "INSAT 3DS": "INSAT-3DS",
    "INSAT-3DS": "INSAT-3DS",
    "SCATSAT 1": "SCATSAT-1",
    "SCATSAT-1": "SCATSAT-1",
    "SCATSAT1": "SCATSAT-1",
    "KALPANA 1": "Kalpana-1",
    "Kalpana 1": "Kalpana-1",
    "kalpana-1": "Kalpana-1",
    "kalpana1": "Kalpana-1",
}

SENSORS: dict[str, str] = {
    # Canonical forms
    "IMAGER": "Imager",
    "SOUNDER": "Sounder",
    "DRT": "DRT",
    "VHIRR": "VHIRR",
    "TIR": "TIR",
    "MWTS": "MWTS",
    "MWHS": "MWHS",
    "ATVR": "ATVR",
    # Variants
    "Imager": "Imager",
    "imager": "Imager",
    "IMAGE R": "Imager",
    "Sounder": "Sounder",
    "sounder": "Sounder",
    "DRT (Dedicated Reasoner for Tropics)": "DRT",
    "Dedicated Reasoner for Tropics": "DRT",
    "VHIRR (Visible and Infrared Hyperspectral Radiometer)": "VHIRR",
    "Visible and Infrared Hyperspectral Radiometer": "VHIRR",
    "TIR (Thermal Infrared Radiometer)": "TIR",
    "Thermal Infrared Radiometer": "TIR",
    "MWTS (Microwave Temperature Sounder)": "MWTS",
    "Microwave Temperature Sounder": "MWTS",
    "MWHS (Microwave Humidity Sounder)": "MWHS",
    "Microwave Humidity Sounder": "MWHS",
    "ATVR (Advanced Tripole Visualization Radiometer)": "ATVR",
    "Advanced Tripole Visualization Radiometer": "ATVR",
}

PRODUCTS: dict[str, str] = {
    # Canonical forms
    "INSAT": "Insat",
    "MYSAT": "Mysat",
    "GIRS": "GiRS",
    "SST": "SST",
    "RAINFALL": "Rainfall",
    "WEATHER": "Weather",
    # Variants
    "Insat": "Insat",
    "insat": "Insat",
    "INSAT METEOROLOGY": "Insat",
    "Mysat": "Mysat",
    "mysat": "Mysat",
    "MYST": "Mysat",
    "GiRS": "GiRS",
    "GIRS": "GiRS",
    "girs": "GiRS",
    "GlobalIRS": "GiRS",
    "Global Indian Remote Sensing": "GiRS",
    "SST": "SST",
    "Sea Surface Temperature": "SST",
    "sea surface temperature": "SST",
    "Rainfall": "Rainfall",
    "rainfall": "Rainfall",
    "precipitation": "Rainfall",
    "Precipitation": "Rainfall",
    "Weather": "Weather",
    "weather": "Weather",
    "METEOROLOGY": "Weather",
    "meteorology": "Weather",
}

# Additional variant mappings (common typos/spacing)
COMMON_VARIANTS: dict[str, str] = {
    "INSAT 3D": "INSAT-3D",
    "INSAT 3DR": "INSAT-3DR",
    "INSAT 3A": "INSAT-3A",
    "INSAT 3DS": "INSAT-3DS",
    "SCATSAT 1": "SCATSAT-1",
    "KALPANA 1": "Kalpana-1",
    "Kalpana 1": "Kalpana-1",
}

# Fuzzy match thresholds
FUZZY_THRESHOLD = 85


class EntityNormalizer:
    """Normalize entity variants to canonical forms."""

    def __init__(self, fuzzy_threshold: int = FUZZY_THRESHOLD) -> None:
        """Initialize entity normalizer.

        Args:
            fuzzy_threshold: Minimum score for fuzzy matching (0-100).
        """
        self.fuzzy_threshold = fuzzy_threshold

        # Maps for exact lookup
        self.satellite_map = SATELLITES.copy()
        self.satellite_map.update(COMMON_VARIANTS)

        self.sensor_map = SENSORS.copy()
        self.product_map = PRODUCTS.copy()

    def normalize(self, text: str, entity_type: str | None = None) -> str | None:
        """Normalize entity text to canonical form.

        Args:
            text: Entity text to normalize.
            entity_type: Optional entity type hint (SATELLITE, SENSOR, PRODUCT).

        Returns:
            Canonical form if match found, None otherwise.
        """
        if not text:
            return None

        text_clean = text.strip()

        # 1. Try exact match (case-insensitive) against known variants
        text_lower = text_clean.lower()

        # Check type-specific maps first
        if entity_type:
            type_map = self._get_type_map(entity_type)
            if type_map:
                # Try exact match
                for variant, canonical in type_map.items():
                    if variant.lower() == text_lower:
                        return canonical
                # Try text as-is
                if text_clean in type_map:
                    return type_map[text_clean]

        # 2. Try across all maps
        for variant, canonical in self.satellite_map.items():
            if variant.lower() == text_lower:
                return canonical

        for variant, canonical in self.sensor_map.items():
            if variant.lower() == text_lower:
                return canonical

        for variant, canonical in self.product_map.items():
            if variant.lower() == text_lower:
                return canonical

        # 3. Try fuzzy matching
        normalized = self._fuzzy_normalize(text_clean, entity_type)
        if normalized:
            return normalized

        return None

    def _get_type_map(self, entity_type: str) -> dict[str, str] | None:
        """Get mapping dict for entity type.

        Args:
            entity_type: Entity type (SATELLITE, SENSOR, PRODUCT).

        Returns:
            Mapping dict or None if unknown type.
        """
        type_upper = entity_type.upper()

        if type_upper in ("SATELLITE", "SATELLITES"):
            return self.satellite_map
        elif type_upper in ("SENSOR", "SENSORS"):
            return self.sensor_map
        elif type_upper in ("PRODUCT", "PRODUCTS"):
            return self.product_map

        return None

    def _fuzzy_normalize(self, text: str, entity_type: str | None = None) -> str | None:
        """Fuzzy match entity to canonical form.

        Args:
            text: Text to normalize.
            entity_type: Optional entity type hint.

        Returns:
            Canonical form if fuzzy match found, None otherwise.
        """
        text_clean = text.strip()

        # Determine which canonicals to check
        if entity_type:
            type_map = self._get_type_map(entity_type)
            canonicals = list(type_map.keys()) if type_map else []
        else:
            canonicals = (
                list(self.satellite_map.keys())
                + list(self.sensor_map.keys())
                + list(self.product_map.keys())
            )

        # Get canonicals (unique values)
        unique_canonicals = (
            set(SATELLITES.values()) | set(SENSORS.values()) | set(PRODUCTS.values())
        )

        best_match = None
        best_score = 0

        for canonical in unique_canonicals:
            # Score with ratio (handles insertions/deletions)
            score = fuzz.ratio(text_clean.lower(), canonical.lower())

            # Also try partial ratio for embedded matches
            partial_score = fuzz.partial_ratio(text_clean.lower(), canonical.lower())
            score = max(score, partial_score)

            if score >= self.fuzzy_threshold and score > best_score:
                best_score = score
                best_match = canonical

        return best_match

    def normalize_batch(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize a batch of entities.

        Args:
            entities: List of entity dicts with 'text' and optional 'label'.

        Returns:
            List with added 'normalized' field.
        """
        results = []

        for entity in entities:
            text = entity.get("text", "")
            label = entity.get("label")

            normalized = self.normalize(text, label)

            result = dict(entity)
            result["normalized"] = normalized

            results.append(result)

        return results


# Convenient singleton for reuse
_normalizer: EntityNormalizer | None = None


def get_normalizer() -> EntityNormalizer:
    """Get or create global EntityNormalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = EntityNormalizer()
    return _normalizer


def normalize_entity(text: str, entity_type: str | None = None) -> str | None:
    """Normalize entity text to canonical form.

    Convenience function using default normalizer.

    Args:
        text: Entity text to normalize.
        entity_type: Optional entity type hint.

    Returns:
        Canonical form if match found, None otherwise.
    """
    normalizer = get_normalizer()
    return normalizer.normalize(text, entity_type)
