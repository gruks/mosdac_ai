"""Combined NLP pipeline for MOSDAC data extraction."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Handle missing NLU components gracefully - load with defensive imports
EntityExtractor = None
EntityNormalizer = None
RelationExtractor = None


def _load_components():
    """Load NLP components with defensive import strategy."""
    global EntityExtractor, EntityNormalizer, RelationExtractor

    # Entity extractor (GLiNER)
    try:
        from src.nlp.entities import EntityExtractor as _EE

        EntityExtractor = _EE
    except ImportError:
        try:
            from nlp.entities import EntityExtractor as _EE

            EntityExtractor = _EE
        except ImportError:
            logger.warning("EntityExtractor not available - install gliner")

    # Entity normalizer (rapidfuzz)
    try:
        from src.nlp.normalize import EntityNormalizer as _EN

        EntityNormalizer = _EN
    except ImportError:
        try:
            from nlp.normalize import EntityNormalizer as _EN

            EntityNormalizer = _EN
        except ImportError:
            logger.warning("EntityNormalizer not available - install rapidfuzz")

    # Relation extractor (spaCy)
    try:
        from src.nlp.relations import RelationExtractor as _RE

        RelationExtractor = _RE
    except ImportError:
        try:
            from nlp.relations import RelationExtractor as _RE

            RelationExtractor = _RE
        except ImportError:
            logger.warning("RelationExtractor not available - install spacy")

    # Report status
    if EntityExtractor and EntityNormalizer and RelationExtractor:
        logger.info("All NLP components loaded successfully")
    else:
        missing = []
        if not EntityExtractor:
            missing.append("EntityExtractor")
        if not EntityNormalizer:
            missing.append("EntityNormalizer")
        if not RelationExtractor:
            missing.append("RelationExtractor")
        logger.warning(f"NLP components not loaded: {', '.join(missing)}")


# Load components on module import
_load_components()


class MOSDACPipeline:
    """Unified pipeline for processing MOSDAC data through all NLP stages.

    Integrates:
    - Entity extraction (GLiNER)
    - Entity normalization (canonical forms + fuzzy matching)
    - Relationship extraction (spaCy dependency parsing)

    Output format compatible with Neo4j schema.
    """

    def __init__(self) -> None:
        """Initialize pipeline with all components."""
        if (
            EntityExtractor is None
            or EntityNormalizer is None
            or RelationExtractor is None
        ):
            _load_components()  # Try loading if not yet loaded

        self.entity_extractor = EntityExtractor() if EntityExtractor else None
        self.normalizer = EntityNormalizer() if EntityNormalizer else None
        self.relation_extractor = RelationExtractor() if RelationExtractor else None

    @property
    def is_ready(self) -> bool:
        """Check if all components are available."""
        return all([self.entity_extractor, self.normalizer, self.relation_extractor])

    def process_text(self, text: str) -> dict[str, Any]:
        """Process a single text through the full NLP pipeline.

        Pipeline stages:
        1. Extract entities (satellites, sensors, products)
        2. Normalize entities to canonical forms
        3. Extract relationships between normalized entities

        Args:
            text: Input text to process

        Returns:
            Dict with:
            - entities: List of extracted entities with normalized forms
            - relations: List of extracted relationships
            - normalized: Dict mapping original to canonical forms
        """
        if not text or not text.strip():
            return {"entities": [], "relations": [], "normalized": {}}

        try:
            # Stage 1: Extract entities
            raw_entities = self.entity_extractor.extract_all(text)

            # Stage 2: Normalize entities
            normalized_entities = self.normalizer.normalize_batch(raw_entities)

            # Build normalized mapping
            normalized_map = {}
            for entity in normalized_entities:
                original = entity.get("text", "")
                canonical = entity.get("normalized")
                if canonical and original:
                    normalized_map[original] = canonical

            # Get unique normalized entities for relation extraction
            unique_normalized = []
            seen_texts = set()
            for entity in normalized_entities:
                text = entity.get("normalized") or entity.get("text", "")
                if text and text not in seen_texts:
                    unique_normalized.append(
                        {"text": text, "label": entity.get("label", "")}
                    )
                    seen_texts.add(text)

            # Stage 3: Extract relations between normalized entities
            relations = self.relation_extractor.extract_relations(
                text, unique_normalized
            )

            return {
                "entities": normalized_entities,
                "relations": relations,
                "normalized": normalized_map,
            }

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {"entities": [], "relations": [], "normalized": {}}

    def process_file(self, filepath: str | Path) -> dict[str, Any]:
        """Process a single JSON file from data/raw/.

        Args:
            filepath: Path to JSON file in data/raw/

        Returns:
            Dict with processed entities and relations from file
        """
        filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return {
                "file": str(filepath),
                "entities": [],
                "relations": [],
                "error": "File not found",
            }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both list and dict formats
            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                logger.warning(f"Unexpected data format in {filepath}")
                return {"file": str(filepath), "entities": [], "relations": []}

            all_entities = []
            all_relations = []

            # Process each item - use 'name' or 'text' field
            for item in items:
                # Extract text to process
                text = (
                    item.get("name") or item.get("text") or item.get("description", "")
                )

                if text:
                    result = self.process_text(text)
                    # Add source info to each entity
                    for entity in result.get("entities", []):
                        entity["source_file"] = filepath.name
                        entity["confidence"] = entity.get("confidence", 0.9)
                    all_entities.extend(result.get("entities", []))
                    all_relations.extend(result.get("relations", []))

            return {
                "file": filepath.name,
                "entities": all_entities,
                "relations": all_relations,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            return {
                "file": str(filepath),
                "entities": [],
                "relations": [],
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            return {
                "file": str(filepath),
                "entities": [],
                "relations": [],
                "error": str(e),
            }


def process_all_scraped_data() -> dict[str, Any]:
    """Process all JSON files in data/raw/ and save to data/nlp/.

    Creates:
    - data/nlp/entities.json: All extracted and normalized entities
    - data/nlp/relations.json: All extracted relationships
    - data/nlp/combined.json: Full output with metadata

    Returns:
        Dict with processing summary
    """
    # Define paths
    raw_dir = Path("data/raw")
    nlp_dir = Path("data/nlp")

    # Create output directory
    nlp_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON files in data/raw/
    json_files = sorted(raw_dir.glob("*.json"))

    if not json_files:
        logger.warning("No JSON files found in data/raw/")
        return {"files_processed": 0, "entities": 0, "relations": 0}

    # Initialize pipeline
    pipeline = MOSDACPipeline()

    # Track all results
    all_entities = []
    all_relations = []
    files_processed = 0

    # Process each file
    for json_file in json_files:
        logger.info(f"Processing {json_file.name}...")
        result = pipeline.process_file(json_file)

        if result.get("entities"):
            # Add file source to entities
            for entity in result["entities"]:
                entity["source_file"] = json_file.name

            all_entities.extend(result["entities"])
            files_processed += 1

        if result.get("relations"):
            # Add file source to relations
            for relation in result["relations"]:
                relation["source_file"] = json_file.name

            all_relations.extend(result["relations"])

    # Deduplicate entities by text+label+source
    seen = set()
    unique_entities = []
    for entity in all_entities:
        key = (
            entity.get("text", ""),
            entity.get("label", ""),
            entity.get("source_file", ""),
        )
        if key not in seen:
            seen.add(key)
            unique_entities.append(entity)

    # Deduplicate relations by subject+object+type
    seen_relations = set()
    unique_relations = []
    for rel in all_relations:
        key = (
            rel.get("subject", ""),
            rel.get("object", ""),
            rel.get("relation_type", ""),
        )
        if key not in seen_relations:
            seen_relations.add(key)
            unique_relations.append(rel)

    # Save entities
    entities_path = nlp_dir / "entities.json"
    with open(entities_path, "w", encoding="utf-8") as f:
        json.dump(unique_entities, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(unique_entities)} entities to {entities_path}")

    # Save relations
    relations_path = nlp_dir / "relations.json"
    with open(relations_path, "w", encoding="utf-8") as f:
        json.dump(unique_relations, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(unique_relations)} relations to {relations_path}")

    # Save combined output
    combined = {
        "metadata": {
            "files_processed": files_processed,
            "total_entities": len(unique_entities),
            "total_relations": len(unique_relations),
            "source_files": [f.name for f in json_files],
        },
        "entities": unique_entities,
        "relations": unique_relations,
    }

    combined_path = nlp_dir / "combined.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved combined output to {combined_path}")

    return {
        "files_processed": files_processed,
        "entities": len(unique_entities),
        "relations": len(unique_relations),
        "output_dir": str(nlp_dir),
    }


# Module-level convenience functions
def process_file(filepath: str | Path) -> dict[str, Any]:
    """Process a single file through the pipeline."""
    pipeline = MOSDACPipeline()
    return pipeline.process_file(filepath)


def process_text(text: str) -> dict[str, Any]:
    """Process a single text through the pipeline."""
    pipeline = MOSDACPipeline()
    return pipeline.process_text(text)
