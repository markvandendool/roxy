# Existing RAG/Brain/AI Optimization Systems Inventory

**Date:** 2025-12-08  
**Purpose:** Complete catalog of existing RAG, Brain, and AI optimization systems before building documentation upgrade  
**Status:** Pre-Implementation Audit

---

## 🎯 EXECUTIVE SUMMARY

**Found 8 distinct RAG/Brain/AI systems:**
1. **RAG Score Graph Schema** - RockyAI rhythm intelligence (music scores)
2. **Documentation Brain** - Vector embeddings for docs/brain/ (LanceDB)
3. **Semantic Search** - Code entity search (hash-based embeddings)
4. **Chunked Embeddings** - Function/class-level code search
5. **Figma RAG** - Design system embeddings
6. **Service Registry Embeddings** - Service/component search
7. **Error Catalog Embeddings** - Error solution search
8. **Simple Search Index** - Basic JSON index for docs/brain/

**Key Finding:** Multiple overlapping systems exist. Documentation upgrade should **integrate with** existing systems, not duplicate them.

---

## 📊 DETAILED INVENTORY

### 1. RAG Score Graph Schema (RockyAI Rhythm Brain)

**Location:** `src/services/rockyai/rag-score-graph-schema.ts`  
**Purpose:** Knowledge graph for RockyAI's rhythmic intelligence RAG system  
**Status:** ✅ Production-ready schema (v1.0.0)  
**Technology:** Graph database (Neo4j/Supabase), vector embeddings for semantic search

**Features:**
- Score nodes with embeddings (title, rhythm)
- Meter, beat grouping, tempo range nodes
- Similarity queries for scores
- Rhythm pattern search
- Graph operations interface

**Database Schema:**
- `rag_scores` table with vector embeddings
- `rag_meters`, `rag_beat_groupings` lookup tables
- Similarity edges between scores
- pgvector extension for semantic search

**Query Interface:**
```typescript
interface ScoreGraphOperations {
  addScore(score: ScoreNode): Promise<void>;
  searchScores(query: SimilarityQuery): Promise<QueryResult<ScoreNode>[]>;
  findSimilarScores(scoreId: string): Promise<QueryResult<ScoreNode>[]>;
}
```

**Related Files:**
- `docs/sprints/RAG_SCORE_METADATA_EXTRACTION_PLAN.md` - Extraction pipeline
- `docs/sprints/PHOENIX_PROTOCOL_PHASE1_IMPLEMENTATION.md` - Implementation plan

**Integration Note:** This is for **music scores**, not documentation. Keep separate.

---

### 2. Documentation Brain (LanceDB Vector Store)

**Location:** `scripts/doc-brain/`  
**Purpose:** Vector embeddings for documentation in `docs/brain/`  
**Status:** ⚠️ Partially implemented (requires LangChain dependencies)  
**Technology:** LanceDB, LangChain, OpenAI embeddings

**Files:**
- `build-embeddings.mjs` - Builds vector store from markdown files
- `vector-query.mjs` - Semantic search using LanceDB
- `query-docs.mjs` - Fallback simple search
- `mcp-server.mjs` - MCP server for agent access

**Current State:**
- ✅ Simple index generation (`docs/brain/search-index.json`)
- ⚠️ Vector store requires: `vectordb`, `@langchain/community`, `langchain`, `@langchain/openai`
- ⚠️ Vector store path: `docs/brain/vector-store/` (may not exist)

**Chunking Strategy:**
- Chunk size: 1000 tokens
- Overlap: 200 tokens
- Uses `RecursiveCharacterTextSplitter`

**Embedding Model:**
- `text-embedding-3-small` (faster, cheaper)

**Query Interface:**
```bash
node scripts/doc-brain/vector-query.mjs "How do I fix E0277?"
```

**Integration Note:** This is **specifically for docs/brain/** directory. Documentation upgrade should **extend this** to cover all `docs/` directories.

---

### 3. Semantic Search (Code Entity Search)

**Location:** `scripts/semantic-search.mjs`  
**Purpose:** Find code entities (services, components, utilities) using natural language  
**Status:** ✅ Fully implemented and working  
**Technology:** Hash-based TF-IDF embeddings (384 dimensions)

**Files:**
- `scripts/semantic-search.mjs` - Main search script
- `scripts/semantic-search-chunked.mjs` - Chunked version
- `docs/.embeddings.json` - Generated embeddings (3.5 MB, 481 entities)

**Embedding Method:**
- Hash-based TF-IDF projection to 384 dimensions
- No external dependencies (lightweight)
- Cosine similarity for matching

**Query Interface:**
```bash
pnpm search "audio playback service"
# or
node scripts/semantic-search.mjs "MIDI event handling"
```

**Coverage:**
- Services (from service registry)
- Components
- Utilities
- Singletons
- Error catalogs

**Performance:**
- Query time: 3-4ms average
- 481 entities indexed

**Integration Note:** This is for **code entities**, not documentation. Keep separate but can share embedding infrastructure.

---

### 4. Chunked Embeddings (Function/Class Level)

**Location:** `scripts/embeddings/generate-chunked-embeddings.mjs`  
**Purpose:** Hierarchical search at function/class/method level  
**Status:** ✅ Fully implemented  
**Technology:** ts-morph for AST parsing, hash-based embeddings

**Files:**
- `scripts/embeddings/generate-chunked-embeddings.mjs`
- `docs/.embeddings-chunked.json` - Generated embeddings (41 MB, production-ready)

**Chunking Strategy:**
- Classes (with all methods)
- Functions (standalone)
- Methods (within classes)
- Interfaces/Types

**Features:**
- Line number tracking
- Code preview (first 300-500 chars)
- Search text includes: type, name, description, parameters

**Query Interface:**
- Uses same `semantic-search-chunked.mjs` script
- Results include file path, line numbers, code preview

**Integration Note:** This is for **code structure**, not documentation. Can share chunking strategies.

---

### 5. Figma RAG (Design System Embeddings)

**Location:** `scripts/figma-generate-embeddings.mjs`  
**Purpose:** Vector embeddings for Figma design system chunks  
**Status:** ✅ Implemented  
**Technology:** OpenAI embeddings API

**Files:**
- `scripts/figma-generate-embeddings.mjs`
- `docs/brain/80-research/figma/RAG_CHUNKS/` - Chunk files

**Coverage:**
- Figma design components
- Design system patterns
- UI/UX guidelines

**Integration Note:** This is for **design system**, not general documentation. Keep separate.

---

### 6. Service Registry Embeddings

**Location:** `scripts/embeddings/generate-embeddings.mjs`  
**Purpose:** Embeddings for service registry entities  
**Status:** ✅ Fully implemented  
**Technology:** Hash-based TF-IDF (384 dimensions)

**Files:**
- `scripts/embeddings/generate-embeddings.mjs`
- `docs/.service-registry.json` - Service registry
- `docs/.embeddings.json` - Includes service registry embeddings

**Coverage:**
- Services
- Components
- Utilities
- Singletons
- Error catalogs (via `include-error-catalog.mjs`)

**Integration Note:** This is **already integrated** into semantic search. Documentation upgrade can reuse this infrastructure.

---

### 7. Error Catalog Embeddings

**Location:** `scripts/embeddings/include-error-catalog.mjs`  
**Purpose:** Embeddings for error solutions  
**Status:** ✅ Integrated into main embeddings  
**Technology:** Hash-based TF-IDF

**Coverage:**
- Error codes and solutions
- Error patterns
- Fix strategies

**Integration Note:** Already part of semantic search. Documentation upgrade should **include error catalog** in documentation search.

---

### 8. Simple Search Index

**Location:** `docs/brain/search-index.json`  
**Purpose:** Basic JSON index for quick document lookup  
**Status:** ✅ Generated by `build-embeddings.mjs`  
**Technology:** Simple JSON structure

**Structure:**
```json
{
  "generated": "2025-10-24T17:14:01.076Z",
  "documents": [
    {
      "path": "AGENT_ONBOARDING.md",
      "type": "general",
      "title": "Agent Onboarding Guide",
      "preview": "..."
    }
  ]
}
```

**Coverage:**
- All markdown files in `docs/brain/`
- Basic metadata (path, type, title, preview)

**Integration Note:** This is a **fallback** when vector store doesn't exist. Documentation upgrade should **enhance this** with full metadata.

---

## 🔗 INTEGRATION OPPORTUNITIES

### What to Reuse:
1. **Embedding Infrastructure** - Hash-based TF-IDF method (lightweight, no deps)
2. **Chunking Strategies** - Function/class-level chunking patterns
3. **Query Interface Patterns** - CLI scripts, similarity search
4. **Service Registry** - Already has entity discovery
5. **Error Catalog** - Already indexed, should be in doc search

### What to Extend:
1. **Documentation Brain** - Extend from `docs/brain/` to all `docs/`
2. **Simple Search Index** - Add full metadata (YAML frontmatter)
3. **Vector Store** - Use LanceDB or ChromaDB (already planned)
4. **MCP Server** - Extend for full documentation access

### What to Avoid Duplicating:
1. **Code Entity Search** - Keep separate (for code, not docs)
2. **RAG Score Graph** - Keep separate (for music scores)
3. **Figma RAG** - Keep separate (for design system)
4. **Service Registry** - Already works, don't rebuild

---

## 📋 RECOMMENDATIONS FOR DOCUMENTATION UPGRADE

### 1. Extend Documentation Brain (Not Replace)
- **Current:** Only covers `docs/brain/`
- **Upgrade:** Extend to all `docs/` directories
- **Method:** Enhance `build-embeddings.mjs` to scan all docs

### 2. Enhance Simple Index
- **Current:** Basic JSON with path, type, title, preview
- **Upgrade:** Add YAML frontmatter metadata, freshness, related docs
- **Method:** Parse frontmatter, enrich index structure

### 3. Unify Query Interface
- **Current:** Multiple scripts (`vector-query.mjs`, `query-docs.mjs`, `semantic-search.mjs`)
- **Upgrade:** Single `DocumentationBrain` service class
- **Method:** Create `src/services/DocumentationBrain.ts` that wraps all systems

### 4. Integrate Error Catalog
- **Current:** Error catalog in code search
- **Upgrade:** Also in documentation search
- **Method:** Include error solutions in doc search results

### 5. Add Health Monitoring
- **Current:** No freshness tracking
- **Upgrade:** Automated health checks
- **Method:** Scripts to check broken links, outdated docs, missing metadata

### 6. Metadata System
- **Current:** No frontmatter in most docs
- **Upgrade:** YAML frontmatter for all docs
- **Method:** Script to add/validate frontmatter

---

## 🎯 ARCHITECTURE DECISION

**Build on top of existing systems, don't replace them:**

1. **Extend Documentation Brain** - Add all `docs/` directories
2. **Enhance Simple Index** - Add metadata, freshness
3. **Create Unified Service** - `DocumentationBrain.ts` wraps all systems
4. **Add Health Monitoring** - New scripts for freshness/link checking
5. **Integrate Error Catalog** - Include in doc search results

**Keep separate:**
- Code entity search (semantic-search.mjs)
- RAG Score Graph (music scores)
- Figma RAG (design system)

**Result:** Unified documentation system that leverages existing infrastructure while adding new capabilities.

---

## 📊 SYSTEM MAP

```
Documentation Upgrade Architecture
├── DocumentationBrain.ts (NEW - Unified Service)
│   ├── Extends: Documentation Brain (LanceDB)
│   ├── Enhances: Simple Search Index
│   ├── Integrates: Error Catalog
│   └── Adds: Health Monitoring
│
├── Existing Systems (Keep Separate)
│   ├── Semantic Search (code entities)
│   ├── RAG Score Graph (music scores)
│   └── Figma RAG (design system)
│
└── Shared Infrastructure
    ├── Embedding methods (hash-based TF-IDF)
    ├── Chunking strategies
    └── Query patterns
```

---

**Next Steps:**
1. Review this inventory
2. Update documentation upgrade plan to integrate with existing systems
3. Avoid duplicating functionality
4. Build on top of Documentation Brain infrastructure




























