# Phase 3 Plan 1: User Setup Required

## Neo4j Database Setup

### Environment Variables

| Variable | Default | Source |
|----------|---------|--------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Desktop → Select Database → Connect → URI |
| `NEO4J_USER` | `neo4j` | Default: neo4j |
| `NEO4J_PASSWORD` | (required) | Neo4j Desktop → Select Database → Connect → Password |

### Setup Instructions

1. **Download & Install Neo4j Desktop:**
   - Visit: https://neo4j.com/download/
   - Install the desktop application

2. **Create a Database:**
   - Open Neo4j Desktop
   - Click "New Database" 
   - Give it a name (e.g., "mosdac")
   - Set a password (this becomes NEO4J_PASSWORD)

3. **Get Connection Details:**
   - Click on your database in the sidebar
   - Click "Connect"
   - Copy the URI shown (usually `bolt://localhost:7687`)

4. **Add to Your Environment:**
   ```bash
   # On Windows (PowerShell)
   $env:NEO4J_URI = "bolt://localhost:7687"
   $env:NEO4J_USER = "neo4j"
   $env:NEO4J_PASSWORD = "your_password_here"
   
   # Or add to .env file in project root
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here
   ```

### Verification Commands

```bash
# Test Python import
python -c "from src.neo4j import Neo4jClient; c = Neo4jClient(); print('Connected:', c.is_connected)"

# Test connectivity (if credentials set)
python -c "from src.neo4j import Neo4jClient; c = Neo4jClient(); print('Verified:', c.verify_connectivity())"
```

---

**Status:** Incomplete - Requires Neo4j installation and credentials

*Generated: 2026-04-12*