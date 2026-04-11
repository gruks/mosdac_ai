# Requirements: MOSDAC GraphRAG

**Defined:** 2026-04-11
**Core Value:** Weather data Q&A using Knowledge Graph + Fine-tuned LLM

## Phase 1: Web Scraper

- [ ] **SCRAPE-01**: Scrape satellite data from mosdac.gov.in
- [ ] **SCRAPE-02**: Scrape sensor specifications
- [ ] **SCRAPE-03**: Scrape data product descriptions
- [ ] **SCRAPE-04**: Scrape FAQs
- [ ] **SCRAPE-05**: Handle dynamic content (JavaScript-rendered pages)

## Phase 2: NLP Entity Extraction

- [ ] **NLP-01**: Extract satellite entities (INSAT-3D, etc.)
- [ ] **NLP-02**: Extract sensor entities
- [ ] **NLP-03**: Extract product entities
- [ ] **NLP-04**: Extract relationships (PROVIDES, USES, etc.)
- [ ] **NLP-05**: Entity normalization (INSAT 3D → INSAT-3D)

## Phase 3: Neo4j Schema

- [ ] **SCHEMA-01**: Define Node types (Satellite, Sensor, Product, Document, FAQ)
- [ ] **SCHEMA-02**: Define Relationship types
- [ ] **SCHEMA-03**: Create constraints for unique nodes
- [ ] **SCHEMA-04**: Create indexes for query performance

## Phase 4: Data Loader

- [ ] **LOAD-01**: Bulk import scraped data to Neo4j
- [ ] **LOAD-02**: Incremental updates for new data
- [ ] **LOAD-03**: Link documents to entities
- [ ] **LOAD-04**: Cache embeddings in FAISS

## Phase 5: Fine-tuned Model

- [ ] **FINE-01**: Prepare training data from knowledge graph
- [ ] **FINE-02**: Fine-tune model for weather queries
- [ ] **FINE-03**: Evaluate model quality

## Phase 6: GraphRAG Pipeline

- [ ] **GRAGRAG-01**: Vector search for documents
- [ ] **GRAGRAG-02**: Graph traversal for relationships
- [ ] **GRAGRAG-03**: Combine contexts
- [ ] **GRAGRAG-04**: Prompt injection defense

## Phase 7: Q&A Interface

- [ ] **QA-01**: REST API endpoint for queries
- [ ] **QA-02**: Stream responses
- [ ] **QA-03**: Show sources/references
- [ ] **QA-04**: Rate limiting

---
*Requirements defined: 2026-04-11*