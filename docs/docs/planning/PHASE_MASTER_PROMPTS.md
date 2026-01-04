# 🎯 PHASE MASTER PROMPTS
## Deterministic Execution Prompts for Phases 2-12

**Version:** 2.1.0  
**Purpose:** Zero-drift execution prompts for Cursor/AI agents  
**Governance:** Must follow Plan Version 2.1.0 + Execution Model invariants

---

## ⭐ PHASE 2 MASTER PROMPT — Netflix-Grade UI Overhaul

```
You are building Phase 2 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Implement Netflix/Spotify-grade media browsing UI:
- Hero banner system with featured song
- 8 carousel rows (Recommended, Skill Level, Trending, etc.)
- Hover preview system with IntersectionObserver
- Design system foundations (Tailwind + vanilla-extract)

CONSTRAINTS:
- Follow UnifiedSong as canonical data model (from Phase 1)
- Do not modify Phoenix Protocol modules (runtime, editor, renderer, quantum-rails)
- CSS bundle <10kB (Tailwind JIT enforced, purge rules active)
- React 18+ App Router file structure
- Use SongVaultLoader for all song data (no direct Supabase queries)
- Performance budget: <150ms first paint, 60fps carousel scroll, <50ms hover preview

TASKS:
1. Create src/ui/hero/HeroBanner.tsx using UnifiedSong
   - Full-width edge-to-edge display
   - Harmonic color palette background (auto-generated from key/mode)
   - "Start Practice" CTA
   - Skill badges overlay
   - Difficulty meter
   - Preview waveform/animation placeholder
   - GPU-accelerated transitions (Framer Motion)

2. Create src/ui/carousels/CarouselRow.tsx
   - Horizontal scrollable list
   - Left/right navigation arrows
   - Peek effect (shows partial cards at edges)
   - Smooth scroll snap
   - 8 row types: Recommended, Skill Level, Trending, Top Skill, Recently Updated, Daily Challenge, Similar, Favorites

3. Create src/ui/previews/HoverPreview.tsx
   - IntersectionObserver for lazy loading
   - Prefetch song metadata on hover
   - Overlay with quick stats (key, tempo, difficulty)
   - Skill tags
   - Play button
   - "Add to Practice" button
   - CSS GPU acceleration

4. Create src/app/songvault/page.tsx (Next.js RSC)
   - Server Component for initial render
   - Use SongVaultLoader in server component
   - Hero banner at top
   - 8 carousel rows below
   - Streaming SSR for progressive loading

5. Create src/app/songvault/[id]/page.tsx (Next.js RSC detail page)
   - Server Component for song detail
   - Full song metadata
   - Harmonic profile visualization
   - Skill connections
   - Practice mode entry point

6. Implement design tokens (src/ui/design-system/tokens.ts)
   - Colors (harmonic palette system)
   - Spacing (8px grid)
   - Typography (font families, sizes)
   - Export as CSS variables

7. Configure Tailwind (tailwind.config.js)
   - JIT mode enabled
   - Purge rules for <10kB bundle
   - Design token integration
   - Custom animations

8. Add Framer Motion animations
   - Hero banner entrance (<2ms budget)
   - Carousel transitions (60fps)
   - Hover preview fade-in (<50ms)
   - No layout shifts

9. Integrate real data using SongVaultLoader
   - Server Component: Load songs in RSC
   - Pass to Client Components for interactivity
   - Use useSongVaultLoader hook for client-side updates

DELIVERABLES:
- All components SSR-ready (Next.js App Router)
- Tailwind config with purge rules (<10kB CSS bundle)
- RSC for data lists (no hydration for static content)
- No hydration regressions (check React DevTools)
- Performance: <150ms first paint, 60fps carousels, <50ms hover

AGENT PROTOCOL:
- Post activity to Breakroom: "Claimed Phase 2: Netflix-Grade UI"
- Follow Execution Model invariants
- Use fileIndex from plan for file locations
- Post discoveries for any architectural decisions

BEGIN NOW.
```

---

## ⚡ PHASE 3.1 MASTER PROMPT — React Server Components Integration

```
You are building Phase 3.1 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Integrate React Server Components (RSC) for song lists, carousels, and search results.
Enable streaming SSR for progressive page load.

CONSTRAINTS:
- Phase 2 must be complete (Netflix UI)
- Use Next.js 14+ App Router
- Server Components for data fetching
- Client Components only for interactivity
- No hydration for static content
- Performance: <150ms first paint, <500ms TTI

TASKS:
1. Convert src/app/songvault/page.tsx to RSC
   - Move SongVaultLoader calls to Server Component
   - Stream song data as HTML
   - Client Components for carousels (interactive only)

2. Create src/app/songvault/feed/page.tsx (RSC)
   - Server Component for song feed
   - Streaming SSR for progressive load
   - Pagination via Server Actions

3. Create src/app/songvault/carousels/page.tsx (RSC)
   - Server Component for carousel data
   - Separate RSC for each carousel row
   - Selective hydration (only navigation arrows)

4. Implement Server Actions for mutations
   - Add to favorites
   - Add to practice playlist
   - Update user preferences

5. Add Suspense boundaries
   - Wrap carousel rows in Suspense
   - Show loading states during streaming
   - Progressive enhancement

6. Optimize hydration
   - Use 'use client' only where needed
   - Minimize client bundle size
   - Lazy load interactive components

DELIVERABLES:
- All song lists as RSC (server-rendered HTML)
- Streaming SSR working (progressive load)
- Selective hydration (only interactive widgets)
- Performance: <150ms first paint, <500ms TTI

AGENT PROTOCOL:
- Post activity: "Claimed Phase 3.1: RSC Integration"
- Verify Phase 2 completion
- Follow Execution Model dependency rules

BEGIN NOW.
```

---

## ⚡ PHASE 3.2 MASTER PROMPT — SongVault Edge Service

```
You are building Phase 3.2 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Create Supabase Edge Functions + Bun microservices for global search and recommendations.
Enable <100ms queries globally via edge deployment.

CONSTRAINTS:
- Phase 3.1 must be complete (RSC)
- Use Supabase Edge Functions (Deno-based)
- Use Bun for compute-heavy microservices
- Coalesce multiple queries into one response
- Edge caching via KV store
- Performance: <100ms query latency (p95)

TASKS:
1. Create edge/functions/songvault-search/index.ts
   - Supabase Edge Function
   - Accept search query + filters
   - Call SongVaultLoader logic
   - Return UnifiedSong[]
   - Cache results in edge KV

2. Create edge/functions/songvault-recommendations/index.ts
   - Supabase Edge Function
   - Accept user ID + context
   - Compute recommendations (placeholder for Phase 5)
   - Return recommended UnifiedSong[]
   - Cache user embeddings

3. Create services/songvault-search-engine/index.ts (Bun)
   - Bun-powered search ranking
   - Vector distance calculations
   - Metadata filtering
   - Export as microservice

4. Create services/songvault-recommendations/index.ts (Bun)
   - Bun-powered recommendation computation
   - Multi-persona matching (placeholder for Phase 5)
   - Difficulty tier ranking
   - Export as microservice

5. Integrate edge functions with RSC
   - Call edge functions from Server Components
   - Handle edge caching
   - Fallback to direct Supabase if edge fails

6. Set up edge KV store (Upstash Redis)
   - Cache frequent queries
   - TTL strategies
   - Invalidation on song updates

DELIVERABLES:
- Edge functions deployed (Supabase)
- Bun microservices running (Cloudflare Workers or similar)
- Edge caching operational (>80% hit rate)
- Performance: <100ms queries globally

AGENT PROTOCOL:
- Post activity: "Claimed Phase 3.2: Edge Service"
- Verify Phase 3.1 completion
- Test edge deployment

BEGIN NOW.
```

---

## ⚡ PHASE 3.3 MASTER PROMPT — Image & CDN Optimization

```
You are building Phase 3.3 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Optimize images and CDN strategy for fast global delivery.
Enable responsive images, lazy loading, and prefetching.

CONSTRAINTS:
- Phase 3.1 must be complete (RSC)
- Use CDN (Cloudinary/ImageKit)
- Responsive images (srcset, WebP/AVIF)
- Lazy loading (IntersectionObserver)
- Prefetching (next song's album art)
- Performance: <50ms image load (p95)

TASKS:
1. Create scripts/image-optimization.mjs
   - Generate multiple image sizes
   - Convert to WebP/AVIF
   - Upload to CDN
   - Generate srcset strings

2. Create scripts/cdn-sync.mjs
   - Sync local images to CDN
   - Invalidate CDN cache on updates
   - Generate CDN URLs

3. Integrate CDN with components
   - Use CDN URLs in HeroBanner
   - Use CDN URLs in SongCard
   - Responsive srcset attributes

4. Implement lazy loading
   - IntersectionObserver for off-screen images
   - Placeholder blur (next/image)
   - Progressive enhancement

5. Add prefetching
   - Prefetch next song's album art on hover
   - Prefetch carousel images before scroll
   - Background prefetch for likely next actions

6. Optimize harmonic color palettes
   - Generate palette images server-side
   - Cache in CDN
   - Use as fallback for missing album art

DELIVERABLES:
- All images via CDN
- Responsive images (srcset)
- Lazy loading operational
- Prefetching working
- Performance: <50ms image load

AGENT PROTOCOL:
- Post activity: "Claimed Phase 3.3: CDN Optimization"
- Verify Phase 3.1 completion

BEGIN NOW.
```

---

## 🔍 PHASE 4 MASTER PROMPT — Vector Intelligence Layer

```
You are building Phase 4 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Implement hybrid vector search (pgvector + Qdrant) for semantic queries.
Enable natural language search: "songs that teach syncopation".

CONSTRAINTS:
- Phase 3.1 must be complete (RSC)
- Use pgvector (Supabase Postgres extension)
- Use Qdrant (dedicated vector DB)
- Generate multi-modal embeddings (metadata, skill, harmonic, rhythm)
- Performance: <100ms semantic search (p95)

TASKS:
1. Create supabase/migrations/add_pgvector.sql
   - Enable pgvector extension
   - Create embeddings table
   - Add vector columns to songs table
   - Create HNSW indexes

2. Create src/services/embeddings/generator.ts
   - Generate metadata embeddings (genre, key, tempo, difficulty)
   - Generate skill embeddings (skill tags → vector)
   - Generate harmonic embeddings (chord progression → vector)
   - Generate NVX1 rhythm embeddings (rhythmic density → vector)
   - Use OpenAI embeddings API or open-source model

3. Create src/services/vector-search/pgvector.ts
   - Query pgvector for similarity search
   - Filter by metadata (key, tempo, genre)
   - Return UnifiedSong[] with similarity scores

4. Create src/services/vector-search/qdrant.ts
   - Connect to Qdrant
   - Store song embeddings
   - Query for semantic similarity
   - Hybrid filtering (vector + metadata)

5. Create src/services/vector-search/hybrid.ts
   - Combine pgvector (consistency) + Qdrant (scale)
   - Route queries based on complexity
   - Merge results with ranking

6. Create src/services/semantic-search/query-parser.ts
   - Parse natural language queries
   - Extract intent ("songs like X", "songs that teach Y")
   - Generate query embeddings

7. Create src/services/semantic-search/executor.ts
   - Execute semantic queries
   - Use vector search + metadata filters
   - Return UnifiedSong[] with explanations

8. Create harmonic color palette system
   - Auto-generate palettes from key/tempo/rhythm
   - Store as metadata
   - Use in UI rendering

DELIVERABLES:
- pgvector operational (Supabase)
- Qdrant operational (vector DB)
- Embedding generation working
- Semantic search functional
- Natural language queries working
- Performance: <100ms semantic search

AGENT PROTOCOL:
- Post activity: "Claimed Phase 4: Vector Intelligence"
- Verify Phase 3.1 completion
- Test semantic queries

BEGIN NOW.
```

---

## 🤖 PHASE 5 MASTER PROMPT — Hybrid Recommender Engine

```
You are building Phase 5 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Implement Spotify-style hybrid recommender (collaborative + content + multi-persona).
Target: 85%+ recommendation relevance.

CONSTRAINTS:
- Phase 4 must be complete (Vector Intelligence)
- Use collaborative filtering (playlist co-occurrence)
- Use content-based filtering (metadata similarity)
- Implement multi-persona user profiles (4+ personas)
- Context-aware personalization (practice/learning/browsing modes)
- Performance: <100ms recommendation generation (p95)

TASKS:
1. Create src/services/recommendations/collaborative.ts
   - Playlist co-occurrence (songs in same playlists → similar)
   - Practice patterns (users who practiced X also practiced Y)
   - Tempo preferences (user's preferred BPM range)
   - Practice streaks (songs that keep users engaged)

2. Create src/services/recommendations/content-based.ts
   - Key similarity (same/distant keys)
   - Rhythm similarity (NVX1 rhythmic patterns)
   - Skill similarity (shared skill tags)
   - Harmonic complexity (chord progression vectors)
   - Difficulty tier (1-10 scale matching)

3. Create src/services/recommendations/personas.ts
   - Persona A: Rhythm-leaning (syncopation, polyrhythms)
   - Persona B: Harmony-leaning (chord progressions, modulations)
   - Persona C: Genre familiarity (pop/rock vs. jazz/classical)
   - Persona D: Difficulty-seeking (challenge vs. comfort)
   - Generate embeddings for each persona

4. Create src/services/recommendations/multi-persona.ts
   - Store 4+ user embeddings
   - Generate candidate list from all personas
   - Re-rank by context (practice mode vs. browsing)
   - Apply diversity filter (avoid genre clustering)
   - Boost educational value (skill progression)

5. Create src/services/recommendations/context-aware.ts
   - Practice Mode: Focus on skill progression
   - Learning Mode: Guided difficulty curve
   - Browsing Mode: Discovery + favorites
   - Review Mode: Spaced repetition scheduling

6. Create src/services/recommendations/hybrid.ts
   - Combine CF + content + persona results
   - Weight by context
   - Return UnifiedSong[] with explanations

7. Integrate with edge functions
   - Call recommendation service from edge
   - Cache user embeddings
   - Update recommendations on user activity

DELIVERABLES:
- Collaborative filtering working
- Content-based filtering working
- Multi-persona profiles operational
- Context-aware personalization working
- Hybrid recommender functional
- Performance: <100ms recommendation generation
- Target: 85%+ recommendation relevance

AGENT PROTOCOL:
- Post activity: "Claimed Phase 5: Hybrid Recommender"
- Verify Phase 4 completion
- Test recommendation quality

BEGIN NOW.
```

---

## 🎼 PHASE 6 MASTER PROMPT — Learning Engine (Duolingo-Grade)

```
You are building Phase 6 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Implement Duolingo-grade learning engine with guided paths, spaced repetition, and skill graph.
Target: +40% practice retention, +30% skill progression.

CONSTRAINTS:
- Phase 5 must be complete (Hybrid Recommender)
- Build skills → songs bipartite graph
- Implement guided path system (AI-curated playlists)
- Add spaced repetition (half-life regression model)
- Create Practice Mode UI
- Performance: <100ms path generation (p95)

TASKS:
1. Create src/services/learning/skill-graph.ts
   - Build bipartite graph: Skills ↔ Songs
   - Define prerequisites (Skill A unlocks Skill B)
   - Assign difficulty tiers (1-10 per skill)
   - Graph queries: "Next skill after X", "Songs that teach skill Y at difficulty Z"

2. Create src/services/learning/prerequisites.ts
   - Define skill prerequisites
   - Check unlock conditions
   - Generate skill progression paths

3. Create src/services/learning/guided-path.ts
   - AI-curated playlist based on:
     - Last practiced skills
     - Upcoming skill unlocks
     - Weaknesses (low performance)
     - Strengths (mastery confirmation)
     - NVX1 performance metrics
     - Song difficulty curve
   - Interleaving: Mix new + review (not sequential)
   - Adaptive difficulty: Adjust based on performance

4. Create src/services/learning/spaced-repetition.ts
   - Half-life regression model (Duolingo approach)
   - Predict forgetting curve for each skill
   - Schedule reviews before predicted forgetting
   - Boost frequency for struggling skills

5. Create src/services/learning/hlr-model.ts
   - Implement half-life regression
   - Calculate retention probability
   - Schedule optimal review times

6. Create src/pages/PracticeMode.tsx
   - Guided playlist UI
   - Progress tracking (skill mastery %)
   - Streak system (daily practice)
   - Badges (skill milestones)
   - Feedback loop ("Too easy/too hard" → adjust)

7. Create src/components/practice/GuidedPlaylist.tsx
   - Display AI-curated playlist
   - Show skill progression
   - Highlight next unlocks

8. Create src/components/practice/ProgressTracker.tsx
   - Visualize skill mastery
   - Show practice streaks
   - Display badges

DELIVERABLES:
- Skills → Songs graph operational
- Guided path system working
- Spaced repetition scheduling functional
- Practice Mode UI complete
- Performance: <100ms path generation
- Target: +40% retention, +30% progression

AGENT PROTOCOL:
- Post activity: "Claimed Phase 6: Learning Engine"
- Verify Phase 5 completion
- Test guided paths

BEGIN NOW.
```

---

## 🧙‍♂️ PHASE 7 MASTER PROMPT — RockyAI Music Tutor

```
You are building Phase 7 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Implement RAG-powered music tutor with explainable recommendations.
Enable natural language queries: "How do I improve syncopation?"

CONSTRAINTS:
- Phase 6 must be complete (Learning Engine)
- Use RockyAI (existing LLM integration)
- RAG pipeline (retrieval → generation)
- Vector search for skill/song retrieval
- Graph traversal for skill recommendations
- Performance: <2s tutor response (p95)

TASKS:
1. Create src/services/tutor/skill-tutor.ts
   - Natural language query parsing
   - RAG retrieval (vector search for relevant songs/skills)
   - Skill graph traversal
   - NVX1 score analysis
   - LLM generation (explanatory responses)

2. Create src/services/tutor/rag-pipeline.ts
   - Retrieve relevant content (songs, skills, lessons)
   - Generate context for LLM
   - Call RockyAI with context
   - Return formatted response

3. Create src/services/tutor/explainable-recommendations.ts
   - "Why was this song recommended?"
   - Show similarity scores
   - Show skill alignment
   - Show difficulty match
   - Generate explanation: "You enjoyed songs with swing rhythm, so next I suggest a syncopation piece to broaden your rhythm skills."

4. Create src/services/tutor/reasoning-generator.ts
   - Generate reasoning for recommendations
   - Explain skill progression
   - Provide practice suggestions

5. Create src/services/tutor/progress-reviews.ts
   - Weekly/monthly reports
   - Skills mastered
   - Skills needing review
   - Recommended next steps
   - Personalized feedback

6. Create src/services/tutor/diagnostics.ts
   - After practice session analysis
   - Identify weak areas
   - Suggest targeted practice
   - Explain mistakes (if applicable)
   - Celebrate improvements

7. Create src/pages/Tutor.tsx
   - Chat interface for tutor
   - Natural language input
   - Formatted responses
   - Skill recommendations
   - Practice suggestions

8. Create src/components/tutor/ChatInterface.tsx
   - Chat UI component
   - Message history
   - Input field
   - Send button

DELIVERABLES:
- Skill tutor operational
- RAG pipeline working
- Explainable recommendations functional
- Progress reviews working
- Practice diagnostics functional
- Tutor UI complete
- Performance: <2s tutor response

AGENT PROTOCOL:
- Post activity: "Claimed Phase 7: RockyAI Tutor"
- Verify Phase 6 completion
- Test tutor queries

BEGIN NOW.
```

---

## 🖼 PHASE 8 MASTER PROMPT — Visual Enhancements

```
You are building Phase 8 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Add visual enhancements: animated harmonic art, rhythm badges, key badges, progress heatmaps.

CONSTRAINTS:
- Phase 2 must be complete (Netflix UI)
- Phase 4 must be complete (Vector Intelligence - for harmonic palettes)
- Use Framer Motion for animations
- GPU-accelerated rendering
- Performance: 60fps animations

TASKS:
1. Create src/components/visual/HarmonicArt.tsx
   - Animated harmonic art (key-based gradients)
   - GPU-accelerated animations
   - Responsive to song key/mode

2. Create src/components/visual/RhythmBadges.tsx
   - Rhythm-density visual badges
   - Color-coded by complexity
   - Animated on hover

3. Create src/components/visual/KeyBadges.tsx
   - Key/mode micro-badges
   - Circle of fifths visualization
   - Interactive key selection

4. Create src/components/visual/TempoVisualization.tsx
   - Tempo/syncopation visualizations
   - Waveform display
   - Beat grid overlay

5. Create src/components/visual/ProgressHeatmap.tsx
   - Progress heatmap (skill mastery over time)
   - Calendar-style visualization
   - Color intensity = practice frequency

6. Integrate visual components
   - Add to HeroBanner
   - Add to SongCard
   - Add to Practice Mode
   - Add to Tutor interface

DELIVERABLES:
- All visual components created
- Animations GPU-accelerated
- Performance: 60fps
- Integrated into UI

AGENT PROTOCOL:
- Post activity: "Claimed Phase 8: Visual Enhancements"
- Verify Phase 2 and Phase 4 completion

BEGIN NOW.
```

---

## 🌐 PHASE 9 MASTER PROMPT — Multi-Platform Support

```
You are building Phase 9 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Add multi-platform support: TV UI, tablet UI, mobile-optimized Netflix-style layout.

CONSTRAINTS:
- Phase 2 must be complete (Netflix UI)
- Responsive design tokens
- Platform-specific navigation
- Touch-optimized for tablet/mobile
- Remote navigation for TV

TASKS:
1. Create src/app/tv/songvault/page.tsx
   - TV-optimized layout (large screen)
   - Remote navigation (arrow keys, select)
   - Focus management
   - Large touch targets

2. Create src/components/tv/RemoteNavigation.tsx
   - Arrow key navigation
   - Select button handling
   - Focus indicators
   - Keyboard shortcuts

3. Create src/app/tablet/songvault/page.tsx
   - Tablet-optimized layout
   - Touch-optimized carousels
   - Swipe gestures
   - Larger touch targets

4. Create src/app/mobile/songvault/page.tsx
   - Mobile-optimized layout
   - Single-column lists
   - Bottom navigation
   - Swipe gestures

5. Update design tokens for platforms
   - TV: Large fonts, high contrast
   - Tablet: Medium fonts, touch-friendly
   - Mobile: Compact, thumb-friendly

6. Add platform detection
   - Detect device type
   - Route to appropriate layout
   - Optimize images per platform

DELIVERABLES:
- TV UI complete
- Tablet UI complete
- Mobile UI complete
- Responsive design working
- Platform detection functional

AGENT PROTOCOL:
- Post activity: "Claimed Phase 9: Multi-Platform"
- Verify Phase 2 completion

BEGIN NOW.
```

---

## 🔒 PHASE 10 MASTER PROMPT — Certification Pass

```
You are building Phase 10 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Certify UI performance, accessibility, RSC hydration, CDN assets, and bundle sizes.
Ensure all performance budgets are met.

CONSTRAINTS:
- Phase 2 must be complete (Netflix UI)
- Phase 3 must be complete (Performance Architecture)
- WCAG 2.1 AA compliance
- Performance budgets: <150ms first paint, <500ms TTI, <10kB CSS, <200kB JS

TASKS:
1. Create tests/performance/ui-performance.test.ts
   - First paint <150ms
   - Time to interactive <500ms
   - Carousel scroll 60fps
   - Hover preview <50ms

2. Create tests/accessibility/a11y-certification.test.ts
   - WCAG 2.1 AA compliance
   - Keyboard navigation
   - Screen reader compatibility
   - Color contrast ratios

3. Create tests/rsc/hydration-budgets.test.ts
   - RSC hydration <500ms
   - No hydration regressions
   - Selective hydration working

4. Create scripts/audit/cdn-assets.mjs
   - Audit all CDN assets
   - Verify image optimization
   - Check CDN cache headers
   - Validate responsive images

5. Create scripts/audit/bundle-size.mjs
   - Audit CSS bundle (<10kB)
   - Audit JS bundle (<200kB initial load)
   - Identify optimization opportunities
   - Generate bundle report

6. Run all certification tests
   - Performance tests passing
   - Accessibility tests passing
   - Hydration tests passing
   - CDN audit passing
   - Bundle audit passing

DELIVERABLES:
- All certification tests passing
- Performance budgets met
- Accessibility certified
- Bundle sizes optimized
- CDN assets optimized

AGENT PROTOCOL:
- Post activity: "Claimed Phase 10: Certification"
- Verify Phase 2 and Phase 3 completion
- Generate certification report

BEGIN NOW.
```

---

## 📈 PHASE 11 MASTER PROMPT — Production Scaling

```
You are building Phase 11 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Scale production infrastructure: edge caching, read replicas, materialized views, load shedding.

CONSTRAINTS:
- Phase 3 must be complete (Performance Architecture)
- Phase 4 must be complete (Vector Intelligence)
- Phase 5 must be complete (Hybrid Recommender)
- Maintain <100ms query latency (p95)
- Handle 1M+ songs

TASKS:
1. Create scripts/scaling/edge-caching.mjs
   - Define TTL strategies
   - Cache frequent queries
   - Invalidate on updates
   - Monitor cache hit rate (>80%)

2. Create scripts/scaling/read-replicas.mjs
   - Set up Supabase read replicas
   - Route read queries to replicas
   - Route write queries to primary
   - Monitor replica lag

3. Create scripts/scaling/materialized-views.mjs
   - Create materialized views for expensive aggregations
   - Refresh strategy (daily/hourly)
   - Index materialized views
   - Monitor refresh performance

4. Create scripts/optimization/query-indexing.mjs
   - Audit all queries
   - Identify missing indexes
   - Create indexes for frequent filters
   - Monitor query performance

5. Create scripts/optimization/load-shedding.mjs
   - Implement load shedding (Netflix approach)
   - Drop low-priority requests under load
   - Use cached fallbacks
   - Maintain performance budgets

6. Monitor production metrics
   - Query latency (p95 <100ms)
   - Cache hit rate (>80%)
   - Error rate (<0.1%)
   - Throughput (requests/second)

DELIVERABLES:
- Edge caching operational
- Read replicas configured
- Materialized views created
- Query indexing optimized
- Load shedding functional
- Production metrics monitored

AGENT PROTOCOL:
- Post activity: "Claimed Phase 11: Production Scaling"
- Verify Phase 3, 4, 5 completion
- Test scaling under load

BEGIN NOW.
```

---

## 🪄 PHASE 12 MASTER PROMPT — AI-Orchestrated UX

```
You are building Phase 12 of the SongVault Master Plan (Version 2.1.0).

OBJECTIVE:
Implement fully adaptive UI, context-aware homepage, dynamic difficulty curves, auto-generated daily challenges, predictive prefetching.

CONSTRAINTS:
- Phase 5 must be complete (Hybrid Recommender)
- Phase 6 must be complete (Learning Engine)
- Phase 7 must be complete (RockyAI Tutor)
- Use AI for UI orchestration
- Maintain performance budgets

TASKS:
1. Create src/services/ai-orchestration/adaptive-ui.ts
   - Fully adaptive UI layout (persona-based)
   - Dynamic carousel ordering
   - Personalized hero banner
   - Context-aware component visibility

2. Create src/services/ai-orchestration/context-detector.ts
   - Detect time of day
   - Detect user mood (from activity)
   - Detect practice context
   - Adjust UI accordingly

3. Create src/services/ai-orchestration/daily-challenges.ts
   - Auto-generated daily challenges (AI-curated)
   - Skill-based challenges
   - Difficulty-matched challenges
   - Progress tracking

4. Create src/services/ai-orchestration/curator.ts
   - AI curation of content
   - Personalized playlists
   - Skill progression paths
   - Discovery recommendations

5. Create src/services/ai-orchestration/predictive-prefetch.ts
   - Predict next likely actions
   - Prefetch song data
   - Prefetch recommendations
   - Prefetch images

6. Integrate AI orchestration
   - Update homepage with context-aware content
   - Adjust difficulty curves in real-time
   - Generate daily challenges
   - Prefetch likely next actions

DELIVERABLES:
- Adaptive UI operational
- Context-aware homepage working
- Dynamic difficulty curves functional
- Daily challenges auto-generated
- Predictive prefetching working

AGENT PROTOCOL:
- Post activity: "Claimed Phase 12: AI-Orchestrated UX"
- Verify Phase 5, 6, 7 completion
- Test adaptive behavior

BEGIN NOW.
```

---

## 📋 EXECUTION CHECKLIST

Before executing any phase:

- [ ] Read Plan Version 2.1.0
- [ ] Read Execution Model invariants
- [ ] Verify phase dependencies are complete
- [ ] Post activity to Breakroom: "Claimed Phase X: [Name]"
- [ ] Use fileIndex for file locations
- [ ] Follow agent constraints
- [ ] Post discoveries for architectural decisions
- [ ] Complete all deliverables
- [ ] Verify performance budgets
- [ ] Post activity: "Completed Phase X: [Name]"

---

**END OF PHASE MASTER PROMPTS**

**Version 2.1.0 — Ready for Deterministic Execution**
