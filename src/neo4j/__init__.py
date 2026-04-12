"""Neo4j knowledge graph client module."""

from src.neo4j.client import Neo4jClient
from src.neo4j.loader import DataLoader
from src.neo4j.nodes import Satellite, Sensor, Product, Document, FAQ
from src.neo4j.relationships import PROVIDES, USES, MEASURES, LOCATED_AT, ANSWERS
from src.neo4j.schema import SchemaSetup

__all__ = [
    "Neo4jClient",
    "DataLoader",
    "Satellite",
    "Sensor",
    "Product",
    "Document",
    "FAQ",
    "PROVIDES",
    "USES",
    "MEASURES",
    "LOCATED_AT",
    "ANSWERS",
    "SchemaSetup",
]

# Example usage:
#   from src.neo4j import Neo4jClient, DataLoader
#
#   client = Neo4jClient(password="your-password")
#   loader = DataLoader(client)
#   counts = loader.load_all("data/raw")
#   # {'satellites': 10, 'products': 9, 'documents': N, 'faqs': N}
#   print(f"Loaded {counts}")
#   client.close()
