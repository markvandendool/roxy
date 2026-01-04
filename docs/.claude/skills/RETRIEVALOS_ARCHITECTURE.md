# RetrievalOS Architecture Map

> **C4-Level System Architecture — GraphRAG-Aware**
> **Version:** 1.0.0
> **Date:** December 2025

---

## Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │   Claude     │    │   Cursor     │    │   ChatGPT    │                 │
│   │   Agent      │    │   Codex      │    │   Agent      │                 │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                 │
│          │                   │                   │                         │
│          └───────────────────┼───────────────────┘                         │
│                              │                                             │
│                              ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                                                                     │  │
│   │                      RETRIEVALOS ENGINE                             │  │
│   │                                                                     │  │
│   │   33 Skills • 1,169 Chunks • GraphRAG Fusion • OpenAI Embeddings   │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                             │
│                              ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      MINDSONG CODEBASE                              │  │
│   │                                                                     │  │
│   │              870,696 LOC • TypeScript/Rust/WASM                     │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RETRIEVALOS ENGINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     QUERY PROCESSING LAYER                          │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Query     │  │   Alias     │  │   Synonym   │                 │   │
│  │  │  Expansion  │──│   Lookup    │──│  Expansion  │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                             │
│                              ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     RETRIEVAL LAYER                                 │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │    BM25     │  │    Dense    │  │   Graph     │                 │   │
│  │  │  Retrieval  │  │  Retrieval  │  │  Lookup     │                 │   │
│  │  │  (sparse)   │  │ (semantic)  │  │ (structure) │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │         │                │                │                         │   │
│  │         └────────────────┼────────────────┘                         │   │
│  │                          ▼                                          │   │
│  │                 ┌─────────────────┐                                 │   │
│  │                 │   RRF Fusion    │                                 │   │
│  │                 │  (40/60 split)  │                                 │   │
│  │                 └─────────────────┘                                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                             │
│                              ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     RANKING LAYER                                   │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Lexical   │  │   Graph     │  │  Precision  │                 │   │
│  │  │  Reranker   │──│   Boost     │──│   Boost     │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                             │
│                              ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     POST-PROCESSING LAYER                           │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Skill     │  │  Security   │  │   Result    │                 │   │
│  │  │   Dedup     │──│  Redaction  │──│  Formatting │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Level 3: Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA STORES                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐   ┌──────────────────────┐                       │
│  │  .embeddings-v2.json │   │  .skill-graph.json   │                       │
│  │                      │   │                      │                       │
│  │  • 1,169 chunks      │   │  • 33 nodes          │                       │
│  │  • 1,536 dimensions  │   │  • 80 edges          │                       │
│  │  • BM25 index        │   │  • Domain clusters   │                       │
│  │  • 40MB              │   │                      │                       │
│  └──────────────────────┘   └──────────────────────┘                       │
│                                                                             │
│  ┌──────────────────────┐   ┌──────────────────────┐                       │
│  │  .graph-embeddings   │   │  .query-cache.json   │                       │
│  │                      │   │                      │                       │
│  │  • 33 skill vectors  │   │  • LRU cache         │                       │
│  │  • 64 dimensions     │   │  • 1000 entries max  │                       │
│  │  • Node2Vec          │   │  • Fuzzy matching    │                       │
│  └──────────────────────┘   └──────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCRIPTS                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GENERATION                     RETRIEVAL                                   │
│  ┌─────────────────────┐       ┌─────────────────────┐                     │
│  │ embeddings-v2.mjs   │       │ hybrid-search-v2.mjs│                     │
│  │ (605 lines)         │       │ (450+ lines)        │                     │
│  │                     │       │                     │                     │
│  │ • Semantic chunking │       │ • BM25 + Dense      │                     │
│  │ • OpenAI API        │       │ • RRF fusion        │                     │
│  │ • BM25 index build  │       │ • Redaction         │                     │
│  └─────────────────────┘       └─────────────────────┘                     │
│                                                                             │
│  ┌─────────────────────┐       ┌─────────────────────┐                     │
│  │ graph-embeddings.mjs│       │ reranker.mjs        │                     │
│  │ (400 lines)         │       │ (400+ lines)        │                     │
│  │                     │       │                     │                     │
│  │ • Node2Vec walks    │       │ • Lexical scoring   │                     │
│  │ • 64d embeddings    │       │ • Graph boost       │                     │
│  │ • Structural sim    │       │ • Precision boost   │                     │
│  └─────────────────────┘       └─────────────────────┘                     │
│                                                                             │
│  VERIFICATION                   UTILITIES                                   │
│  ┌─────────────────────┐       ┌─────────────────────┐                     │
│  │ astral-gauntlet.mjs │       │ query-expansion.mjs │                     │
│  │ (650 lines)         │       │ (362 lines)         │                     │
│  │                     │       │                     │                     │
│  │ • H1-H8 phases      │       │ • Alias lookup      │                     │
│  │ • Security tests    │       │ • Synonyms          │                     │
│  │ • Death run         │       │ • Acronyms          │                     │
│  └─────────────────────┘       └─────────────────────┘                     │
│                                                                             │
│  ┌─────────────────────┐       ┌─────────────────────┐                     │
│  │ omega-dashboard.mjs │       │ query-cache.mjs     │                     │
│  │ (250 lines)         │       │ (180 lines)         │                     │
│  │                     │       │                     │                     │
│  │ • Real-time metrics │       │ • LRU eviction      │                     │
│  │ • Color output      │       │ • Similarity match  │                     │
│  │ • Phase status      │       │ • Persistence       │                     │
│  └─────────────────────┘       └─────────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Level 4: Code Diagram — Search Pipeline

```
hybrid-search-v2.mjs
│
├─► expandQuery(query)                    // query-expansion.mjs
│   ├─► detectSkillNames(query)           // Alias lookup
│   ├─► expandAcronyms(query)             // E2E → end-to-end
│   └─► expandWithSynonyms(query)         // Audio → sound, playback
│
├─► bm25Retrieval(query, chunks)          // Sparse retrieval
│   ├─► tokenize(query)
│   ├─► bm25Score(query, chunk)           // k1=1.2, b=0.75
│   └─► sort by score, return top 30
│
├─► denseRetrieval(query, chunks)         // Semantic retrieval
│   ├─► generateQueryEmbedding(query)     // OpenAI API or fallback
│   ├─► cosineSimilarity(q, chunk)        // For each chunk
│   └─► sort by score, return top 30
│
├─► fusionScore(bm25, dense)              // RRF fusion
│   └─► 0.4 * bm25 + 0.6 * dense
│
├─► rerank(fused, query)                  // reranker.mjs
│   ├─► lexicalScore(query, doc)          // Phrase match, coverage
│   ├─► graphBoost(doc.skill)             // Graph embeddings similarity
│   ├─► precisionBoost(query, doc)        // Known difficult queries
│   └─► sort by combined score
│
├─► deduplicateBySkill(results)           // Keep best chunk per skill
│
├─► applyRedaction(results, agentType)    // Security layer
│   └─► canAccess(agentType, level)       // public/internal/secret
│
└─► return results
```

---

## GraphRAG Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GRAPH STRUCTURE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌─────────────────┐                                │
│                         │  AUDIO CLUSTER  │                                │
│                         └────────┬────────┘                                │
│                                  │                                         │
│            ┌─────────────────────┼─────────────────────┐                   │
│            │                     │                     │                   │
│     ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐           │
│     │apollo-audio │◄─────►│apollo-cons. │◄─────►│vgm-soundfont│           │
│     └──────┬──────┘       └──────┬──────┘       └─────────────┘           │
│            │                     │                                         │
│            │              ┌──────▼──────┐                                  │
│            └─────────────►│prof-mixer   │                                  │
│                           └─────────────┘                                  │
│                                                                             │
│                         ┌─────────────────┐                                │
│                         │ MUSIC CLUSTER   │                                │
│                         └────────┬────────┘                                │
│                                  │                                         │
│            ┌─────────────────────┼─────────────────────┐                   │
│            │                     │                     │                   │
│     ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐           │
│     │music-theory │◄─────►│voice-leading│◄─────►│chord-engine │           │
│     └─────────────┘       └─────────────┘       └─────────────┘           │
│                                                                             │
│                         ┌─────────────────┐                                │
│                         │RENDERING CLUSTER│                                │
│                         └────────┬────────┘                                │
│                                  │                                         │
│            ┌─────────────────────┼─────────────────────┐                   │
│            │                     │                     │                   │
│     ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐           │
│     │  olympus-3d │◄─────►│threejs-runt.│◄─────►│webgpu-rend. │           │
│     └─────────────┘       └─────────────┘       └─────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Sequence

```
1. QUERY RECEIVED
   │
   ▼
2. QUERY EXPANSION
   │  - "apollo" → ["apollo-audio", "apollo-consolidation"]
   │  - "e2e" → "end-to-end"
   │  - "audio" → ["audio", "sound", "playback"]
   │
   ▼
3. PARALLEL RETRIEVAL
   │
   ├──► BM25 (sparse)
   │    - Exact keyword matching
   │    - TF-IDF scoring
   │    - 30 candidates
   │
   └──► Dense (semantic)
        - OpenAI embedding
        - Cosine similarity
        - 30 candidates
   │
   ▼
4. RRF FUSION
   │  - BM25 weight: 0.40
   │  - Dense weight: 0.60
   │  - Reciprocal rank combination
   │
   ▼
5. RERANKING
   │  - Lexical: phrase match, term coverage
   │  - Graph: structural similarity boost
   │  - Precision: known difficult query boost
   │  - Combined weighted score
   │
   ▼
6. POST-PROCESSING
   │  - Deduplicate by skill (keep best chunk)
   │  - Apply security redaction
   │  - Format results
   │
   ▼
7. RESULTS RETURNED
```

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Query Expansion | <5ms | In-memory lookup |
| BM25 Retrieval | ~50ms | Pre-computed index |
| Dense Retrieval | 200-2000ms | OpenAI API (cached: <10ms) |
| RRF Fusion | <5ms | Simple arithmetic |
| Reranking | ~20ms | Score computation |
| Post-processing | <5ms | Filtering |
| **Total (cached)** | **~100ms** | With query cache |
| **Total (uncached)** | **~2000ms** | OpenAI API call |

---

## Security Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ACCESS LEVELS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PUBLIC                    INTERNAL                   SECRET                │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐     │
│  │ • All skills    │      │ • Architecture  │      │ • Credentials   │     │
│  │ • Public APIs   │      │ • Internal APIs │      │ • API keys      │     │
│  │ • Tutorials     │      │ • Design docs   │      │ • Secrets       │     │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘     │
│         ▲                        ▲                        ▲                │
│         │                        │                        │                │
│  ┌──────┴──────┐          ┌──────┴──────┐          ┌──────┴──────┐        │
│  │   default   │          │claude-opus  │          │   admin     │        │
│  │   chatgpt   │          │             │          │             │        │
│  │   cursor    │          │             │          │             │        │
│  └─────────────┘          └─────────────┘          └─────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Architecture document generated for MindSong Juke Hub RetrievalOS*
*Version 1.0.0 — December 2025*
