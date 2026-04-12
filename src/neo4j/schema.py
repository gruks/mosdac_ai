"""Neo4j schema setup for constraints and indexes."""

import logging
from typing import List, Dict, Any
from src.neo4j.client import Neo4jClient

logger = logging.getLogger(__name__)


class SchemaSetup:
    """Schema setup for Neo4j database - creates constraints and indexes.

    Ensures data integrity (unique constraints) and query performance (indexes).
    Uses IF NOT EXISTS for idempotent runs.
    """

    CONSTRAINTS = [
        # Unique constraints (SCHEMA-03)
        "CREATE CONSTRAINT satellite_name_unique IF NOT EXISTS FOR (s:Satellite) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT sensor_id_unique IF NOT EXISTS FOR (s:Sensor) REQUIRE s.sensor_id IS UNIQUE",
        "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
        "CREATE CONSTRAINT document_url_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.url IS UNIQUE",
        "CREATE CONSTRAINT faq_id_unique IF NOT EXISTS FOR (f:FAQ) REQUIRE f.faq_id IS UNIQUE",
    ]

    INDEXES = [
        # Query performance indexes (SCHEMA-04)
        "CREATE INDEX satellite_type_idx IF NOT EXISTS FOR (s:Satellite) ON (s.type)",
        "CREATE INDEX satellite_status_idx IF NOT EXISTS FOR (s:Satellite) ON (s.status)",
        "CREATE INDEX sensor_type_idx IF NOT EXISTS FOR (s:Sensor) ON (s.type)",
        "CREATE INDEX product_category_idx IF NOT EXISTS FOR (p:Product) ON (p.category)",
        "CREATE INDEX document_type_idx IF NOT EXISTS FOR (d:Document) ON (d.type)",
        "CREATE INDEX faq_category_idx IF NOT EXISTS FOR (f:FAQ) ON (f.category)",
    ]

    def __init__(self, client: Neo4jClient):
        """Initialize schema setup with Neo4j client.

        Args:
            client: Neo4jClient instance
        """
        self._client = client

    def create_constraints(self) -> List[str]:
        """Create all unique constraints.

        Returns:
            List of constraint names that were created (or already existed)
        """
        created = []
        for constraint in self.CONSTRAINTS:
            try:
                self._client.execute_write(constraint)
                # Extract constraint name from query
                name = constraint.split("CONSTRAINT ")[1].split(" IF")[0]
                created.append(name)
                logger.info(f"Created constraint: {name}")
            except Exception as e:
                # Handle "already exists" gracefully
                logger.debug(f"Constraint creation: {e}")
                # Still add to created list if it already exists
                name = constraint.split("CONSTRAINT ")[1].split(" IF")[0]
                created.append(name)
        return created

    def create_indexes(self) -> List[str]:
        """Create all indexes for query performance.

        Returns:
            List of index names that were created (or already existed)
        """
        created = []
        for index in self.INDEXES:
            try:
                self._client.execute_write(index)
                # Extract index name from query
                name = index.split("INDEX ")[1].split(" IF")[0]
                created.append(name)
                logger.info(f"Created index: {name}")
            except Exception as e:
                # Handle "already exists" gracefully
                logger.debug(f"Index creation: {e}")
                # Still add to created list if it already exists
                name = index.split("INDEX ")[1].split(" IF")[0]
                created.append(name)
        return created

    def setup(self) -> Dict[str, Any]:
        """Run complete schema setup (constraints and indexes).

        Returns:
            Dict with 'constraints' and 'indexes' lists
        """
        logger.info("Starting schema setup...")
        constraints = self.create_constraints()
        indexes = self.create_indexes()

        summary = {
            "constraints": constraints,
            "indexes": indexes,
            "total_constraints": len(constraints),
            "total_indexes": len(indexes),
        }

        logger.info(
            f"Schema setup complete: {len(constraints)} constraints, {len(indexes)} indexes"
        )
        return summary

    def verify(self) -> Dict[str, List[str]]:
        """Verify existing constraints and indexes in database.

        Returns:
            Dict with 'constraints' and 'indexes' lists from database
        """
        constraints_query = "SHOW CONSTRAINTS"
        indexes_query = "SHOW INDEXES"

        constraints_result = self._client.execute_read(constraints_query)
        indexes_result = self._client.execute_read(indexes_query)

        return {
            "constraints": [c.get("name", "unknown") for c in constraints_result],
            "indexes": [i.get("name", "unknown") for i in indexes_result],
        }
