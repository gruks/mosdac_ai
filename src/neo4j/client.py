"""Neo4j client wrapper with connection management."""

import os
import logging
from typing import Optional, Any, Dict, List

try:
    from neo4j import GraphDatabase, Driver
except ImportError:
    raise ImportError("neo4j package is required. Install with: pip install neo4j")

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j driver wrapper with connection management.

    Provides connection handling and transaction execution for Neo4j database.
    Uses environment variables for configuration (per project patterns).
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI (default: bolt://localhost:7687)
            user: Neo4j username (default: neo4j)
            password: Neo4j password (required)
        """
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD")

        self._driver: Optional[Driver] = None

        if self._password:
            try:
                self._driver = GraphDatabase.driver(
                    self._uri, auth=(self._user, self._password)
                )
                logger.info(f"Neo4j driver created for {self._uri}")
            except Exception as e:
                logger.error(f"Failed to create Neo4j driver: {e}")
                self._driver = None
        else:
            logger.warning("NEO4J_PASSWORD not set - driver not created")

    def close(self) -> None:
        """Close the driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    def verify_connectivity(self) -> bool:
        """Test connection to Neo4j database.

        Returns:
            True if connection successful, False otherwise
        """
        if self._driver is None:
            logger.warning("No driver - cannot verify connectivity")
            return False

        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j connectivity verified")
            return True
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False

    def execute_write(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a write transaction.

        Args:
            query: Cypher query string
            params: Query parameters dict

        Returns:
            List of result records
        """
        if self._driver is None:
            logger.error("No driver - cannot execute write")
            return []

        params = params or {}
        try:
            with self._driver.session() as session:
                result = session.run(query, params)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Write transaction failed: {e}")
            return []

    def execute_read(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read transaction.

        Args:
            query: Cypher query string
            params: Query parameters dict

        Returns:
            List of result records
        """
        if self._driver is None:
            logger.error("No driver - cannot execute read")
            return []

        params = params or {}
        try:
            with self._driver.session() as session:
                result = session.run(query, params)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Read transaction failed: {e}")
            return []

    def create_node(self, label: str, properties: Dict[str, Any]) -> bool:
        """Create a node with given label and properties.

        Args:
            label: Node label (e.g., 'Satellite', 'Sensor')
            properties: Node properties dict

        Returns:
            True if successful, False otherwise
        """
        # Sanitize property keys for Cypher
        safe_props = {k: v for k, v in properties.items() if v is not None}
        prop_keys = ", ".join(f"{k}: ${k}" for k in safe_props.keys())
        query = f"CREATE (n:{label} {{{prop_keys}}}) RETURN n"

        result = self.execute_write(query, safe_props)
        return len(result) > 0

    def find_node(
        self, label: str, property_key: str, property_value: Any
    ) -> Optional[Dict[str, Any]]:
        """Find a node by property value.

        Args:
            label: Node label
            property_key: Property to search by
            property_value: Value to match

        Returns:
            Node properties dict or None if not found
        """
        query = f"MATCH (n:{label} {{{property_key}: $value}}) RETURN n"
        result = self.execute_read(query, {"value": property_value})

        if result and "n" in result[0]:
            return result[0]["n"]
        return None

    def get_or_create_node(
        self, label: str, properties: Dict[str, Any], primary_key: str
    ) -> Dict[str, Any]:
        """Get existing node or create new if not exists.

        Args:
            label: Node label
            properties: Node properties
            primary_key: Property to use as unique identifier

        Returns:
            Node properties dict
        """
        primary_value = properties.get(primary_key)
        if primary_value:
            existing = self.find_node(label, primary_key, primary_value)
            if existing:
                return existing

        self.create_node(label, properties)
        return properties

    def create_relationship(
        self,
        from_label: str,
        from_key: str,
        from_value: Any,
        rel_type: str,
        to_label: str,
        to_key: str,
        to_value: Any,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between two nodes.

        Args:
            from_label: Source node label
            from_key: Source node primary key property
            from_value: Source node primary key value
            rel_type: Relationship type (e.g., 'PROVIDES', 'USES')
            to_label: Target node label
            to_key: Target node primary key property
            to_value: Target node primary key value
            properties: Relationship properties

        Returns:
            True if successful, False otherwise
        """
        properties = properties or {}
        query = f"""
        MATCH (a:{from_label} {{{from_key}: $from_value}})
        MATCH (b:{to_label} {{{to_key}: $to_value}})
        CREATE (a)-[r:{rel_type} $props]->(b)
        RETURN r
        """
        params = {
            "from_value": from_value,
            "to_value": to_value,
            "props": properties,
        }
        result = self.execute_write(query, params)
        return len(result) > 0

    @property
    def is_connected(self) -> bool:
        """Check if driver is connected.

        Returns:
            True if driver exists, False otherwise
        """
        return self._driver is not None
