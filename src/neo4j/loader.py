"""Data loader for bulk importing scraped JSON into Neo4j knowledge graph."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.neo4j.client import Neo4jClient

logger = logging.getLogger(__name__)


class DataLoader:
    """Bulk data loader for importing scraped JSON into Neo4j.

    Loads卫星 (satellites), products, documents, and FAQs from JSON files
    into the knowledge graph using MERGE for duplicate prevention.

    Example:
        client = Neo4jClient(password="password")
        loader = DataLoader(client)
        counts = loader.load_all("data/raw")
        print(f"Loaded {counts}")
    """

    def __init__(self, client: Neo4jClient):
        """Initialize data loader with Neo4j client.

        Args:
            client: Neo4jClient instance for database operations
        """
        self.client = client
        logger.info("DataLoader initialized")

    def load_satellites(self, path: str) -> int:
        """Load satellites from JSON file into Neo4j.

        Args:
            path: Path to satellites.json file

        Returns:
            Count of nodes created/updated
        """
        with open(path, "r", encoding="utf-8") as f:
            satellites = json.load(f)

        count = 0
        for sat in satellites:
            # Use MERGE to handle duplicates
            query = """
            MERGE (s:Satellite {name: $name})
            SET s.url = $url,
                s.source = $source,
                s.scraped_at = $scraped_at
            RETURN s
            """
            params = {
                "name": sat.get("name"),
                "url": sat.get("url"),
                "source": sat.get("source"),
                "scraped_at": sat.get("scraped_at"),
            }
            result = self.client.execute_write(query, params)
            if result:
                count += 1

        logger.info(f"Loaded {count} satellites")
        return count

    def load_products(self, path: str) -> int:
        """Load products from JSON file into Neo4j.

        Args:
            path: Path to products.json file

        Returns:
            Count of nodes created/updated
        """
        with open(path, "r", encoding="utf-8") as f:
            products = json.load(f)

        count = 0
        for product in products:
            query = """
            MERGE (p:Product {name: $name})
            SET p.url = $url,
                p.category = $category,
                p.scraped_at = $scraped_at
            RETURN p
            """
            params = {
                "name": product.get("name"),
                "url": product.get("url"),
                "category": product.get("category"),
                "scraped_at": product.get("scraped_at"),
            }
            result = self.client.execute_write(query, params)
            if result:
                count += 1

        logger.info(f"Loaded {count} products")
        return count

    def load_documents(self, path: str) -> int:
        """Load documents from JSON file into Neo4j.

        Args:
            path: Path to documents.json file

        Returns:
            Count of nodes created/updated
        """
        with open(path, "r", encoding="utf-8") as f:
            documents = json.load(f)

        count = 0
        for doc in documents:
            # Use doc_id as unique identifier
            doc_id = doc.get("doc_id") or doc.get("name", "").replace(" ", "_").lower()
            query = """
            MERGE (d:Document {doc_id: $doc_id})
            SET d.name = $name,
                d.url = $url,
                d.category = $category,
                d.type = $type,
                d.scraped_at = $scraped_at
            RETURN d
            """
            params = {
                "doc_id": doc_id,
                "name": doc.get("name"),
                "url": doc.get("url"),
                "category": doc.get("category"),
                "type": doc.get("type"),
                "scraped_at": doc.get("scraped_at"),
            }
            result = self.client.execute_write(query, params)
            if result:
                count += 1

        logger.info(f"Loaded {count} documents")
        return count

    def load_faqs(self, path: str) -> int:
        """Load FAQs from JSON file into Neo4j.

        Args:
            path: Path to faqs.json file

        Returns:
            Count of nodes created/updated
        """
        with open(path, "r", encoding="utf-8") as f:
            faqs = json.load(f)

        count = 0
        for faq in faqs:
            # Use faq_id as unique identifier
            faq_id = faq.get("faq_id") or str(faqs.index(faq))
            query = """
            MERGE (f:FAQ {faq_id: $faq_id})
            SET f.question = $question,
                f.answer = $answer,
                f.category = $category,
                f.scraped_at = $scraped_at
            RETURN f
            """
            params = {
                "faq_id": faq_id,
                "question": faq.get("question"),
                "answer": faq.get("answer"),
                "category": faq.get("category"),
                "scraped_at": faq.get("scraped_at"),
            }
            result = self.client.execute_write(query, params)
            if result:
                count += 1

        logger.info(f"Loaded {count} FAQs")
        return count

    def load_all(self, data_dir: str) -> Dict[str, int]:
        """Batch load all data files from directory.

        Loads satellites.json, products.json, documents.json, and faqs.json
        from the specified directory.

        Args:
            data_dir: Directory containing JSON data files

        Returns:
            Dict with counts for each data type:
            {'satellites': N, 'products': N, 'documents': N, 'faqs': N}
        """
        data_path = Path(data_dir)
        counts = {}

        satellites_path = data_path / "satellites.json"
        if satellites_path.exists():
            counts["satellites"] = self.load_satellites(str(satellites_path))

        products_path = data_path / "products.json"
        if products_path.exists():
            counts["products"] = self.load_products(str(products_path))

        documents_path = data_path / "documents.json"
        if documents_path.exists():
            counts["documents"] = self.load_documents(str(documents_path))

        faqs_path = data_path / "faqs.json"
        if faqs_path.exists():
            counts["faqs"] = self.load_faqs(str(faqs_path))

        logger.info(f"Batch load complete: {counts}")
        return counts
