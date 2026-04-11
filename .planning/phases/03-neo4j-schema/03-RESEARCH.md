# Phase 03: Neo4j Schema - Research

**Researched:** 2026-04-11
**Domain:** Neo4j Graph Database, Schema Definition, Cypher Query Language
**Confidence:** HIGH

## Summary

This phase defines the graph schema and constraints for storing MOSDAC weather satellite knowledge graph data. The recommended approach uses **Neo4j 5.x** with the official Python driver (`neo4j` 5.x). Schema is defined via Cypher commands for constraints (unique node properties) and indexes (query performance). For bulk initial data loading, use `neo4j-admin database import`. For incremental updates, use Python driver with batched transactions via `UNWIND`.

**Primary recommendation:** Use Neo4j 5.x with Python driver 5.x. Define constraints first, then indexes. Use `neo4j-admin import` for initial load, Python driver batch inserts for ongoing data.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| neo4j | 5.x | Python driver for Neo4j | Official driver, Bolt protocol, transaction management |
| Cypher | Neo4j 5.x | Query language | Native graph queries, schema definitions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| neo4j-admin | 5.x | CLI import tool | Initial bulk data load (offline) |
| apoc | 5.x | Procedures library | Advanced graph operations, data transformation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| neo4j Python driver | py2neo | py2neo is older, less maintained |
| neo4j-admin import | LOAD CSV | LOAD CSV is slower for millions of rows |
| Official driver | HTTP API | Driver handles connection pooling, transactions |

**Installation:**
```bash
pip install neo4j
# For CLI import tool - installed with Neo4j server
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── schema/
│   ├── __init__.py
│   ├── nodes.py          # Node type definitions
│   ├── relationships.py  # Relationship type definitions
│   ├── constraints.py    # CREATE CONSTRAINT statements
│   └── indexes.py        # CREATE INDEX statements
├── neo4j/
│   ├── __init__.py
│   ├── client.py         # Driver wrapper, session management
│   └── queries.py        # Cypher query templates
└── import/
    ├── csv_export.py     # Export NLP output to CSV
    └── batch_loader.py  # Batch insert using driver
```

### Pattern 1: Neo4j Python Driver Connection
**What:** Establish connection using official neo4j driver
**When to use:** Any Python interaction with Neo4j
**Example:**
```python
# Source: Neo4j Python Driver Manual (https://neo4j.com/docs/python-manual/5/)
from neo4j import GraphDatabase

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def execute_write(self, query: str, parameters: dict = None):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(
                lambda tx: tx.run(query, parameters or {})
            )
            return result

# Usage
client = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
client.execute_write("CREATE (n:Satellite {name: $name})", {"name": "INSAT-3D"})
```

### Pattern 2: Create Unique Constraints (SCHEMA-03)
**What:** Ensure no duplicate nodes of same type with same identifier
**When to use:** Enforce uniqueness on node properties (e.g., satellite name)
**Example:**
```cypher
-- Source: Neo4j Cypher Manual (https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/)
-- Unique constraint on Satellite.name
CREATE CONSTRAINT satellite_name_unique
FOR (s:Satellite) REQUIRE s.name IS UNIQUE;

-- Unique constraint on Sensor.sensor_id
CREATE CONSTRAINT sensor_id_unique
FOR (s:Sensor) REQUIRE s.sensor_id IS UNIQUE;

-- Unique constraint on Product.product_id
CREATE CONSTRAINT product_id_unique
FOR (p:Product) REQUIRE p.product_id IS UNIQUE;

-- Unique constraint on Document.url
CREATE CONSTRAINT document_url_unique
FOR (d:Document) REQUIRE d.url IS UNIQUE;

-- Use IF NOT EXISTS for idempotent creation
CREATE CONSTRAINT satellite_name_unique IF NOT EXISTS
FOR (s:Satellite) REQUIRE s.name IS UNIQUE;
```

### Pattern 3: Create Indexes (SCHEMA-04)
**What:** Create indexes for query performance on frequently filtered properties
**When to use:** Properties used in WHERE, MATCH, ORDER BY clauses
**Example:**
```cypher
-- Source: Neo4j Cypher Manual (https://neo4j.com/docs/cypher-manual/5/indexes/create-indexes/)
-- Index on Satellite.type for filtering
CREATE INDEX satellite_type_index
FOR (s:Satellite) ON (s.type);

-- Index on Product.category for filtering
CREATE INDEX product_category_index
FOR (p:Product) ON (p.category);

-- Index on Document.title for text search
CREATE INDEX document_title_index
FOR (d:Document) ON (d.title);

-- Composite index for common query patterns
CREATE INDEX satellite_launch_index
FOR (s:Satellite) ON (s.name, s.launch_year);
```

### Pattern 4: Node Type Definitions (SCHEMA-01)
**What:** Define the node types for MOSDAC knowledge graph
**When to use:** When modeling the graph schema
**Example:**
```cypher
-- Node types based on Phase 2 entity extraction

-- SATELLITE: INSAT-3D, Kalpana, SCATSAT-1, etc.
CREATE (s:Satellite {
    name: "INSAT-3D",
    type: "Geostationary",
    launch_date: "2013-07-26",
    orbit_type: "GEO",
    status: "Operational",
    operator: "ISRO"
});

-- SENSOR: Imager, Sounder, etc.
CREATE (s:Sensor {
    sensor_id: "imager_1",
    name: "Imager",
    type: "Multi-spectral",
    channels: 6,
    resolution: "1km"
});

-- PRODUCT: Cloud products, Temperature data, etc.
CREATE (p:Product {
    product_id: "cloud_product_1",
    name: "Cloud Products",
    category: "Meteorological",
    format: "HDF",
    resolution: "1km"
});

-- DOCUMENT: Technical documents, manuals
CREATE (d:Document {
    doc_id: "doc_001",
    title: "INSAT-3D Data Products Guide",
    url: "https://mosdac.gov.in/doc/insat3d-products",
    type: "Technical Document",
    source: "MOSDAC"
});

-- FAQ: Frequently asked questions
CREATE (f:FAQ {
    faq_id: "faq_001",
    question: "How to download INSAT-3D data?",
    answer: "Visit MOSDAC portal...",
    category: "Data Access"
});
```

### Pattern 5: Relationship Type Definitions (SCHEMA-02)
**What:** Define relationship types between nodes
**When to use:** When creating connections between entities
**Example:**
```cypher
-- Source: Phase 2 NLP extraction relationships

-- Satellite PROVIDES Product
CREATE (s:Satellite {name: "INSAT-3D"})-[r:PROVIDES]->(p:Product {name: "Cloud Products"})
SET r.since = "2013-07-26", r.status = "Active";

-- Satellite USES Sensor
CREATE (s:Satellite {name: "INSAT-3D"})-[r:USES]->(sensor:Sensor {name: "Imager"})
SET r.since = "2013-07-26";

-- Product MEASURES something
CREATE (p:Product {name: "Temperature Data"})-[r:MEASURES]->(m:Measurement {name: "Sea Surface Temperature"})
SET r.unit = "Kelvin", r.range = "180K to 350K";

-- Document LOCATED_AT url
CREATE (d:Document {title: "User Guide"})-[r:LOCATED_AT]->(loc:Location {url: "https://mosdac.gov.in/guide"});

-- FAQ ANSWERS question
CREATE (f:FAQ {question: "How to access?"})-[r:ANSWERS]->(q:Question {text: "How to access data?"});
```

### Pattern 6: Batch Insert with UNWIND
**What:** Efficiently insert large amounts of data using UNWIND
**When to use:** Loading extracted entities from Phase 2
**Example:**
```python
# Source: Neo4j Python Driver patterns
def batch_insert_nodes(client: Neo4jClient, nodes: list[dict]):
    """Insert multiple nodes in a single transaction."""
    query = """
    UNWIND $nodes AS node
    MERGE (n:Satellite {name: node.name})
    SET n += node
    RETURN count(n) AS count
    """
    result = client.execute_write(query, {"nodes": nodes})
    return result

def batch_insert_relationships(client: Neo4jClient, rels: list[dict]):
    """Insert multiple relationships in a single transaction."""
    query = """
    UNWIND $rels AS rel
    MATCH (a:Satellite {name: rel.satellite})
    MATCH (b:Product {name: rel.product})
    MERGE (a)-[r:PROVIDES]->(b)
    SET r += rel.properties
    RETURN count(r) AS count
    """
    result = client.execute_write(query, {"rels": rels})
    return result
```

### Pattern 7: neo4j-admin import for Initial Load
**What:** Use CLI tool for bulk import from CSV files
**When to use:** Initial data load, millions of nodes/relationships
**Example:**
```bash
# Source: Neo4j Operations Manual (https://neo4j.com/docs/operations-manual/current/import/)
# Stop Neo4j first
neo4j stop

# Import CSV files
neo4j-admin database import full \
  --nodes=Satellite=nodes/satellites.csv \
  --nodes=Sensor=nodes/sensors.csv \
  --nodes=Product=nodes/products.csv \
  --relationships=PROVIDES=rels/provides.csv \
  --relationships=USES=rels/uses.csv \
  --database=mosdac

# Start Neo4j
neo4j start
```

**CSV format example for nodes:**
```csv
name,type,launch_date,status
INSAT-3D,Geostationary,2013-07-26,Operational
INSAT-3DR,Geostationary,2016-09-08,Operational
```

**CSV format for relationships:**
```csv
satellite_name,product_name,since
INSAT-3D,Cloud Products,2013-07-26
```

### Anti-Patterns to Avoid
- **No constraints on unique properties:** Leads to duplicate nodes (e.g., "INSAT-3D" inserted twice)
- **Missing indexes on filtered properties:** Slow queries on large graphs
- **Single row inserts in loop:** Extremely slow, use UNWIND batch inserts
- **neo4j-admin import for incremental updates:** Only works on empty database, use Python driver for updates

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph database | Build custom graph storage | Neo4j | ACID transactions, Cypher queries, optimized storage |
| Connection pooling | Implement manually | neo4j driver | Handles Bolt protocol, connection lifecycle |
| Bulk import | Python loop inserts | neo4j-admin import | 10-100x faster for initial load |
| Unique node enforcement | Check before insert | CREATE CONSTRAINT | Atomic, enforced at DB level |

**Key insight:** Neo4j's constraint system ensures data integrity at the database level. Always create constraints before loading data.

## Common Pitfalls

### Pitfall 1: Constraint Creation Fails on Existing Data
**What goes wrong:** Creating unique constraint fails because duplicate values exist
**Why it happens:** Data violates the constraint before constraint exists
**How to avoid:** Clean duplicates first, or use `--skip-duplicate-nodes` with neo4j-admin
**Warning signs:** "Constraint could not be created" error

### Pitfall 2: Index Not Used in Queries
**What goes wrong:** Query is slow despite creating index
**Why it happens:** Index on wrong property, or query doesn't use indexed property
**How to avoid:** Use EXPLAIN to check query plan, index properties used in WHERE/MATCH
**Warning signs:** "NodeIndexSeek" vs "NodeByLabelScan" in EXPLAIN

### Pitfall 3: Driver Session Not Closed
**What goes wrong:** Connection pool exhausted, new queries fail
**Why it happens:** Session created without context manager
**How to avoid:** Always use `with driver.session() as session:` or call session.close()
**Warning signs:** "Connection pool exhausted" error

### Pitfall 4: MERGE Creates Unwanted Nodes
**What goes wrong:** MERGE on relationship creates new nodes
**Why it happens:** MERGE matches or creates entire pattern
**How to avoid:** Use MATCH for existing nodes, then MERGE for relationship only
**Warning signs:** Unexpected new nodes in graph

## Code Examples

### Complete Schema Setup
```python
"""Setup complete schema for MOSDAC knowledge graph."""
from neo4j import GraphDatabase

class SchemaSetup:
    """Create constraints and indexes for MOSDAC graph."""
    
    CONSTRAINTS = [
        # SCHEMA-03: Unique constraints for each node type
        "CREATE CONSTRAINT satellite_name_unique IF NOT EXISTS FOR (s:Satellite) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT sensor_id_unique IF NOT EXISTS FOR (s:Sensor) REQUIRE s.sensor_id IS UNIQUE", 
        "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
        "CREATE CONSTRAINT document_url_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.url IS UNIQUE",
        "CREATE CONSTRAINT faq_id_unique IF NOT EXISTS FOR (f:FAQ) REQUIRE f.faq_id IS UNIQUE",
    ]
    
    INDEXES = [
        # SCHEMA-04: Indexes for query performance
        "CREATE INDEX satellite_type_idx IF NOT EXISTS FOR (s:Satellite) ON (s.type)",
        "CREATE INDEX satellite_status_idx IF NOT EXISTS FOR (s:Satellite) ON (s.status)",
        "CREATE INDEX sensor_type_idx IF NOT EXISTS FOR (s:Sensor) ON (s.type)",
        "CREATE INDEX product_category_idx IF NOT EXISTS FOR (p:Product) ON (p.category)",
        "CREATE INDEX document_type_idx IF NOT EXISTS FOR (d:Document) ON (d.type)",
        "CREATE INDEX faq_category_idx IF NOT EXISTS FOR (f:FAQ) ON (f.category)",
    ]
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def setup(self):
        """Run all schema setup commands."""
        with self.driver.session(database="neo4j") as session:
            # Create constraints first
            for constraint in self.CONSTRAINTS:
                try:
                    session.run(constraint)
                    print(f"Created: {constraint[:50]}...")
                except Exception as e:
                    print(f"Constraint error (may already exist): {e}")
            
            # Create indexes
            for index in self.INDEXES:
                try:
                    session.run(index)
                    print(f"Created: {index[:50]}...")
                except Exception as e:
                    print(f"Index error (may already exist): {e}")
    
    def close(self):
        self.driver.close()


# Usage
setup = SchemaSetup("bolt://localhost:7687", "neo4j", "password")
setup.setup()
setup.close()
```

### Query Examples for Phase 6 GraphRAG
```python
"""Common graph queries for GraphRAG."""
class GraphQueries:
    """Cypher queries for retrieving graph context."""
    
    @staticmethod
    def get_satellite_info(name: str) -> str:
        return """
        MATCH (s:Satellite {name: $name})
        OPTIONAL MATCH (s)-[:USES]->(sensor:Sensor)
        OPTIONAL MATCH (s)-[:PROVIDES]->(product:Product)
        RETURN s.name AS name, s.type AS type, 
               collect(DISTINCT sensor.name) AS sensors,
               collect(DISTINCT product.name) AS products
        """
    
    @staticmethod
    def get_related_entities(entity: str) -> str:
        return """
        MATCH (start {name: $entity})-[r]-(end)
        RETURN type(r) AS relationship, end.name AS entity, 
               labels(end) AS type
        """
    
    @staticmethod
    def get_subgraph(start_node: str, depth: int = 2) -> str:
        return """
        MATCH path = (start {name: $entity})-[*1..$depth]-(other)
        RETURN path
        """
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| py2neo | neo4j Python driver 5.x | 2023 | Official driver with Bolt protocol, better performance |
| CREATE INDEX ON | CREATE INDEX FOR | Neo4j 5.x | New syntax, IF NOT EXISTS support |
| Unique constraint syntax | REQUIRE ... IS UNIQUE | Neo4j 5.x | New constraint syntax, more explicit |

**Deprecated/outdated:**
- **py2neo library:** No longer maintained, use official neo4j driver
- **Legacy constraint syntax:** Old `CREATE CONSTRAINT ON (n:Label) ASSERT` syntax deprecated in 5.x

## Open Questions

1. **Vector index for semantic search**
   - What we know: Neo4j supports vector indexes for similarity search (new in 5.x)
   - What's unclear: Whether GraphRAG requires vector embeddings stored in Neo4j
   - Recommendation: Phase 5/6 may need vector index for semantic search, keep as option

2. **Schema versioning**
   - What we know: Neo4j has no built-in schema migration
   - What's unclear: How to handle schema changes (new node types) after initial load
   - Recommendation: Document schema version, handle migrations in Python code

3. **APOC library usage**
   - What we know: APOC provides useful procedures (apoc.load.json, apoc.periodic.iterate)
   - What's unclear: Whether APOC needed for Phase 4 data loader
   - Recommendation: Start without APOC, add if needed for complex transformations

## Sources

### Primary (HIGH confidence)
- Neo4j Python Driver Manual (https://neo4j.com/docs/python-manual/5/) - Driver API, transactions
- Neo4j Cypher Manual - Constraints (https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/) - Constraint syntax
- Neo4j Operations Manual - Import (https://neo4j.com/docs/operations-manual/current/import/) - neo4j-admin import

### Secondary (MEDIUM confidence)
- Neo4j Community - Python driver batch insert patterns
- Neo4j Blog - Graph data modeling best practices

### Tertiary (LOW confidence)
- Various tutorials on neo4j-admin import - Need verification

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - Official driver well-documented, 5.x stable
- Architecture: HIGH - Cypher patterns verified in official docs
- Pitfalls: MEDIUM - Common issues documented, but some are edge cases

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days - stable domain)