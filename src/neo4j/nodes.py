"""Node type definitions for Neo4j knowledge graph.

These classes represent the entity types extracted in Phase 2 (NLP Extraction).
Each class includes properties matching the extracted entities and
to_dict() methods for Cypher parameter conversion.
"""

from typing import Optional, Dict, Any, List


class Satellite:
    """Satellite node type.

    Represents satellites like INSAT-3D, Kalpana, etc.
    """

    def __init__(
        self,
        name: str,
        type: str = "Geostationary",
        launch_date: Optional[str] = None,
        orbit_type: str = "GEO",
        status: str = "Operational",
        operator: Optional[str] = None,
    ):
        self.name = name
        self.type = type
        self.launch_date = launch_date
        self.orbit_type = orbit_type
        self.status = status
        self.operator = operator

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Cypher parameters."""
        return {
            "name": self.name,
            "type": self.type,
            "launch_date": self.launch_date,
            "orbit_type": self.orbit_type,
            "status": self.status,
            "operator": self.operator,
        }

    def __repr__(self) -> str:
        return f"Satellite(name={self.name!r})"


class Sensor:
    """Sensor node type.

    Represents sensors like Imager, Sounder that are onboard satellites.
    """

    def __init__(
        self,
        sensor_id: str,
        name: str = "Imager",
        type: str = "Multi-spectral",
        channels: Optional[int] = None,
        resolution: Optional[str] = None,
    ):
        self.sensor_id = sensor_id
        self.name = name
        self.type = type
        self.channels = channels
        self.resolution = resolution

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Cypher parameters."""
        return {
            "sensor_id": self.sensor_id,
            "name": self.name,
            "type": self.type,
            "channels": self.channels,
            "resolution": self.resolution,
        }

    def __repr__(self) -> str:
        return f"Sensor(sensor_id={self.sensor_id!r}, name={self.name!r})"


class Product:
    """Product node type.

    Represents data products like Cloud Products, Temperature Data.
    """

    def __init__(
        self,
        product_id: str,
        name: str,
        category: Optional[str] = None,
        format: Optional[str] = None,
        resolution: Optional[str] = None,
    ):
        self.product_id = product_id
        self.name = name
        self.category = category
        self.format = format
        self.resolution = resolution

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Cypher parameters."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "format": self.format,
            "resolution": self.resolution,
        }

    def __repr__(self) -> str:
        return f"Product(product_id={self.product_id!r}, name={self.name!r})"


class Document:
    """Document node type.

    Represents technical documents, manuals, and FAQs.
    """

    def __init__(
        self,
        doc_id: str,
        title: str,
        url: Optional[str] = None,
        type: str = "Technical Document",
        source: str = "MOSDAC",
    ):
        self.doc_id = doc_id
        self.title = title
        self.url = url
        self.type = type
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Cypher parameters."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "url": self.url,
            "type": self.type,
            "source": self.source,
        }

    def __repr__(self) -> str:
        return f"Document(doc_id={self.doc_id!r}, title={self.title!r})"


class FAQ:
    """FAQ node type.

    Represents frequently asked questions and answers from documentation.
    """

    def __init__(
        self,
        faq_id: str,
        question: str,
        answer: str,
        category: Optional[str] = None,
    ):
        self.faq_id = faq_id
        self.question = question
        self.answer = answer
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Cypher parameters."""
        return {
            "faq_id": self.faq_id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
        }

    def __repr__(self) -> str:
        return f"FAQ(faq_id={self.faq_id!r})"


# Convenience function for creating nodes from extracted data
def create_satellite(data: Dict[str, Any]) -> Satellite:
    """Create Satellite from extracted entity data."""
    return Satellite(
        name=data.get("name", ""),
        type=data.get("type"),
        launch_date=data.get("launch_date"),
        orbit_type=data.get("orbit_type"),
        status=data.get("status", "Operational"),
        operator=data.get("operator"),
    )


def create_sensor(data: Dict[str, Any]) -> Sensor:
    """Create Sensor from extracted entity data."""
    return Sensor(
        sensor_id=data.get("sensor_id", ""),
        name=data.get("name", "Imager"),
        type=data.get("type"),
        channels=data.get("channels"),
        resolution=data.get("resolution"),
    )


def create_product(data: Dict[str, Any]) -> Product:
    """Create Product from extracted entity data."""
    return Product(
        product_id=data.get("product_id", ""),
        name=data.get("name", ""),
        category=data.get("category"),
        format=data.get("format"),
        resolution=data.get("resolution"),
    )


def create_document(data: Dict[str, Any]) -> Document:
    """Create Document from extracted entity data."""
    return Document(
        doc_id=data.get("doc_id", ""),
        title=data.get("title", ""),
        url=data.get("url"),
        type=data.get("type", "Technical Document"),
        source=data.get("source", "MOSDAC"),
    )


def create_faq(data: Dict[str, Any]) -> FAQ:
    """Create FAQ from extracted entity data."""
    return FAQ(
        faq_id=data.get("faq_id", ""),
        question=data.get("question", ""),
        answer=data.get("answer", ""),
        category=data.get("category"),
    )
