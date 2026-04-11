"""Relationship extraction using spaCy dependency parsing for MOSDAC entities."""

from typing import Any

import spacy

from src.nlp.config import SPACY_MODEL, RELATION_TYPES


class RelationExtractor:
    """Extract relationships between entities using spaCy dependency parsing."""

    def __init__(self, model_name: str | None = None) -> None:
        """Initialize the relation extractor with a spaCy model.

        Args:
            model_name: Name of spaCy model to use. Defaults to config value.
        """
        self.model_name = model_name or SPACY_MODEL
        self._nlp = spacy.load(self.model_name)
        self.relation_types = RELATION_TYPES

    def extract_relations(
        self, text: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract relationships between entities in text.

        Args:
            text: Input text to analyze.
            entities: List of extracted entity dicts with 'text' and 'label'.

        Returns:
            List of relation dicts with subject, relation_type, object, confidence.
        """
        if not text or not entities:
            return []

        doc = self._nlp(text)
        relations = []

        # Build set of entity texts for quick lookup
        entity_texts = {e["text"] for e in entities}

        # Find subject-verb-object patterns via dependency parsing
        for token in doc:
            # Check if this token is a verb (root of clause)
            if token.pos_ == "VERB":
                relation_type = self._match_relation_type(token.lemma_)

                if relation_type is None:
                    continue

                # Find subject
                subject = self._find_subject(token, entity_texts)
                # Find object
                obj = self._find_object(token, entity_texts)

                # Only create relation if both subject and object are known entities
                if subject and obj and subject != obj:
                    relations.append(
                        {
                            "subject": subject,
                            "relation_type": relation_type,
                            "object": obj,
                            "confidence": 0.9,
                            "context": token.sent.text.strip(),
                        }
                    )

        return relations

    def _match_relation_type(self, verb_lemma: str) -> str | None:
        """Match verb lemma to a known relation type.

        Args:
            verb_lemma: Lemma of the verb to match.

        Returns:
            Relation type if matched, None otherwise.
        """
        lemma_lower = verb_lemma.lower()

        # Direct matches
        if lemma_lower in self.relation_types:
            return lemma_lower.upper()

        # Synonym mappings
        synonyms = {
            "provide": "PROVIDES",
            "give": "PROVIDES",
            "offer": "PROVIDES",
            "use": "USES",
            "utilize": "USES",
            "employ": "USES",
            "include": "USES",
            "have": "USES",
            "equip": "USES",
            "carry": "USES",
            "contain": "USES",
            "locate": "LOCATED_AT",
            "place": "LOCATED_AT",
            "situate": "LOCATED_AT",
            "orbit": "LOCATED_AT",
            "measure": "MEASURES",
            "record": "MEASURES",
            "monitor": "MEASURES",
            "observe": "MEASURES",
            "detect": "MEASURES",
        }

        return synonyms.get(lemma_lower)

    def _find_subject(self, verb_token: Any, entity_texts: set[str]) -> str | None:
        """Find subject entity connected to verb.

        Args:
            verb_token: Verb token to find subject for.
            entity_texts: Set of known entity texts.

        Returns:
            Subject entity text if found, None otherwise.
        """
        # Look for nsubj dependency
        for child in verb_token.children:
            if child.dep_ in ("nsubj", "nsubjpass"):
                # Walk down to find the actual entity
                entity = self._find_entity_in_span(child, entity_texts)
                if entity:
                    return entity

        # Fallback: look at sentence subjects
        for token in verb_token.sent:
            if token.dep_ in ("nsubj", "nsubjpass"):
                entity = self._find_entity_in_span(token, entity_texts)
                if entity:
                    return entity

        return None

    def _find_object(self, verb_token: Any, entity_texts: set[str]) -> str | None:
        """Find object entity connected to verb.

        Args:
            verb_token: Verb token to find object for.
            entity_texts: Set of known entity texts.

        Returns:
            Object entity text if found, None otherwise.
        """
        # Look for dobj, pobj, attr dependencies
        for child in verb_token.children:
            if child.dep_ in ("dobj", "pobj", "attr"):
                entity = self._find_entity_in_span(child, entity_texts)
                if entity:
                    return entity

        # Fallback: look at prepositional objects
        for child in verb_token.children:
            if child.dep_ == "prep":
                for grandchild in child.children:
                    if grandchild.dep_ == "pobj":
                        entity = self._find_entity_in_span(grandchild, entity_texts)
                        if entity:
                            return entity

        return None

    def _find_entity_in_span(
        self, start_token: Any, entity_texts: set[str]
    ) -> str | None:
        """Find entity text in token span.

        Args:
            start_token: Starting token to search from.
            entity_texts: Set of known entity texts.

        Returns:
            Entity text if found, None otherwise.
        """
        # Check the token itself
        if start_token.text in entity_texts:
            return start_token.text

        # Check compound words (e.g., "INSAT-3D" might be tokenized differently)
        span_tokens = [start_token]
        for child in start_token.children:
            if child.dep_ in ("compound", "amod"):
                span_tokens.append(child)

        # Build span text from tokens
        for token in span_tokens:
            if token.text in entity_texts:
                return token.text

        # Also check the token's subtree tokens (lefts + token + rights)
        subtree_tokens = list(start_token.subtree)
        for token in subtree_tokens:
            if token.text in entity_texts:
                return token.text

        return None


def extract_relations(
    text: str, entities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Extract relationships between entities in text.

    Convenience function using default RelationExtractor.

    Args:
        text: Input text to analyze.
        entities: List of extracted entity dicts with 'text' and 'label'.

    Returns:
        List of relation dicts with subject, relation_type, object, confidence.
    """
    extractor = RelationExtractor()
    return extractor.extract_relations(text, entities)
