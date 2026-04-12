"""Relationship type definitions for Neo4j knowledge graph.

These classes represent the relationship types extracted in Phase 2 (NLP Extraction).
Each class includes properties and methods for Cypher query generation.
"""

from typing import Optional, Dict, Any


class PROVIDES:
    """PROVIDES relationship - Satellite provides Sensor/Product.

    Represents: Satellite → PROVIDES → Sensor/Product
    """

    def __init__(
        self,
        since: Optional[str] = None,
        status: str = "Active",
    ):
        self.since = since
        self.status = status

    def to_cypher(self) -> str:
        """Return relationship type string for Cypher."""
        return "PROVIDES"

    def properties_dict(self) -> Dict[str, Any]:
        """Return properties dict for SET clause."""
        props = {}
        if self.since is not None:
            props["since"] = self.since
        if self.status is not None:
            props["status"] = self.status
        return props

    def __repr__(self) -> str:
        return f"PROVIDES(since={self.since!r}, status={self.status!r})"


class USES:
    """USES relationship - Product uses Sensor.

    Represents: Product → USES → Sensor
    """

    def __init__(
        self,
        since: Optional[str] = None,
    ):
        self.since = since

    def to_cypher(self) -> str:
        """Return relationship type string for Cypher."""
        return "USES"

    def properties_dict(self) -> Dict[str, Any]:
        """Return properties dict for SET clause."""
        props = {}
        if self.since is not None:
            props["since"] = self.since
        return props

    def __repr__(self) -> str:
        return f"USES(since={self.since!r})"


class MEASURES:
    """MEASURES relationship - Sensor measures parameter.

    Represents: Sensor → MEASURES → Parameter (e.g., Temperature)
    """

    def __init__(
        self,
        unit: Optional[str] = None,
        range: Optional[str] = None,
    ):
        self.unit = unit
        self.range = range

    def to_cypher(self) -> str:
        """Return relationship type string for Cypher."""
        return "MEASURES"

    def properties_dict(self) -> Dict[str, Any]:
        """Return properties dict for SET clause."""
        props = {}
        if self.unit is not None:
            props["unit"] = self.unit
        if self.range is not None:
            props["range"] = self.range
        return props

    def __repr__(self) -> str:
        return f"MEASURES(unit={self.unit!r}, range={self.range!r})"


class LOCATED_AT:
    """LOCATED_AT relationship - Document/FAQ located at URL section.

    Represents: Document/FAQ → LOCATED_AT → URL section
    """

    def __init__(
        self,
        section: Optional[str] = None,
    ):
        self.section = section

    def to_cypher(self) -> str:
        """Return relationship type string for Cypher."""
        return "LOCATED_AT"

    def properties_dict(self) -> Dict[str, Any]:
        """Return properties dict for SET clause."""
        props = {}
        if self.section is not None:
            props["section"] = self.section
        return props

    def __repr__(self) -> str:
        return f"LOCATED_AT(section={self.section!r})"


class ANSWERS:
    """ANSWERS relationship - FAQ answers question.

    Represents: FAQ → ANSWERS → Question (implicit)
    """

    def __init__(
        self,
        relevance: float = 1.0,
    ):
        self.relevance = relevance

    def to_cypher(self) -> str:
        """Return relationship type string for Cypher."""
        return "ANSWERS"

    def properties_dict(self) -> Dict[str, Any]:
        """Return properties dict for SET clause."""
        return {"relevance": self.relevance}

    def __repr__(self) -> str:
        return f"ANSWERS(relevance={self.relevance!r})"


# Convenience function for creating relationships from extracted data
def create_provides(data: Dict[str, Any]) -> PROVIDES:
    """Create PROVIDES from extracted relationship data."""
    return PROVIDES(
        since=data.get("since"),
        status=data.get("status", "Active"),
    )


def create_uses(data: Dict[str, Any]) -> USES:
    """Create USES from extracted relationship data."""
    return USES(
        since=data.get("since"),
    )


def create_measures(data: Dict[str, Any]) -> MEASURES:
    """Create MEASURES from extracted relationship data."""
    return MEASURES(
        unit=data.get("unit"),
        range=data.get("range"),
    )


def create_located_at(data: Dict[str, Any]) -> LOCATED_AT:
    """Create LOCATED_AT from extracted relationship data."""
    return LOCATED_AT(
        section=data.get("section"),
    )


def create_answers(data: Dict[str, Any]) -> ANSWERS:
    """Create ANSWERS from extracted relationship data."""
    return ANSWERS(
        relevance=data.get("relevance", 1.0),
    )
