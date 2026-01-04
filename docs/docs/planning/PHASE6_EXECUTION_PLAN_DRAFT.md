# 🎼 PHASE 6 EXECUTION PLAN DRAFT
## Learning Engine (Duolingo-Grade) — Pre-Execution Analysis

**Date:** 2025-12-09  
**Status:** 📋 **DRAFT — AWAITING CHIEF APPROVAL**  
**Plan Version:** 2.1.0  
**Agent:** Cursor  
**Task:** PHASE6-LEARNING-ENGINE

---

## ⚠️ **MANDATORY: DO NOT MODIFY CODE UNTIL PLAN APPROVED**

This is a **pre-execution analysis and planning document**. No code changes will be made until Chief approval.

---

## 1. PHASE 6 MASTER PROMPT SUMMARY

**Objective:**
Implement Duolingo-grade learning engine with guided paths, spaced repetition, and skill graph.
Target: +40% practice retention, +30% skill progression.

**Key Deliverables:**
1. Skills → Songs bipartite graph
2. Guided path system (AI-curated playlists)
3. Spaced repetition (half-life regression model)
4. Practice Mode UI (guided playlist, progress tracking, streaks, badges)

**Performance Target:** <100ms path generation (p95)

---

## 2. PRE-EXECUTION DISCOVERY SWEEP RESULTS

### 2.1 Skill Nodes Table Analysis

**Status:** ✅ **READY**

**Schema:**
- **Table:** `skill_nodes` (Supabase PostgreSQL)
- **Count:** 5,821 nodes
- **Structure:**
  - `id` (UUID primary key)
  - `slug` (TEXT, unique)
  - `name` (TEXT)
  - `level` (INTEGER)
  - `domain` (TEXT) - TECHNIQUE, THEORY, RHYTHM, EAR, REPERTOIRE, etc.
  - `category` (TEXT, optional)
  - `parent_id` (UUID, references skill_nodes)
  - `difficulty_tier` (INTEGER, 1-5)

**Indexes:**
- ✅ `idx_skill_nodes_slug` - Slug lookup
- ✅ `idx_skill_nodes_parent` - Parent-child relationships
- ✅ `idx_skill_nodes_domain` - Domain filtering
- ✅ `idx_skill_nodes_category` - Category filtering
- ✅ `idx_skill_nodes_difficulty` - Difficulty tier filtering

**Service:**
- ✅ `SkillTreeService` (`src/services/skilltree/SkillTreeService.ts`)
- ✅ Loads 5,821 nodes from static JSON + Supabase
- ✅ Methods: `getAllNodes()`, `getNodeById()`, `getNodesByDomain()`, `getChildren()`

**Readiness:** ✅ **FULLY OPERATIONAL** - Ready for graph construction

---

### 2.2 Song-Skills Junction Table Analysis

**Status:** ⚠️ **SPARSELY POPULATED** (Critical Gap)

**Schema:**
- **Table:** `song_skills` (Supabase PostgreSQL)
- **Structure:**
  - `song_id` (UUID, references songs.id)
  - `skill_id` (UUID, references skill_nodes.id)
  - `importance` (INTEGER, 1-5 scale)
  - `created_at` (TIMESTAMPTZ)

**Indexes:**
- ✅ `idx_song_skills_song` - Song → skills lookup
- ✅ `idx_song_skills_skill` - Skill → songs lookup
- ✅ `idx_song_skills_importance` - Importance ranking

**Current State:**
- ⚠️ **EXISTS BUT SPARSELY POPULATED** (<1% of songs have skill mappings)
- ⚠️ Estimated <6,790 songs out of 679,000+ have skill mappings
- ⚠️ Gap: 332,710+ songs need skill extraction

**Impact on Phase 6:**
- **BLOCKING:** Cannot build Skills → Songs graph without populated junction table
- **REQUIRED ACTION:** Populate `song_skills` before Phase 6 execution
- **ESTIMATED EFFORT:** 2-4 hours for automatic skill extraction pipeline

**Readiness:** ❌ **NOT READY** - Must populate before Phase 6

---

### 2.3 UnifiedSong Model Analysis

**Status:** ✅ **READY**

**Model Location:**
- `src/services/songvault/types.ts`

**Structure:**
```typescript
interface UnifiedSong {
  id: string;
  title: string;
  artist: string;
  key: string | null;
  tempo: number | null;
  genre: string | null;
  scoreType: 'nvx1' | 'musicxml' | 'abc' | 'midi';
  nvx1?: NVX1ScoreContract;
  metadata: {
    source: string;
    difficulty: number | null;
    skills?: SkillNode[];  // ✅ Already supports skills
    metrics?: ChordProgressionMetrics;
  };
}
```

**Compatibility:**
- ✅ Already includes `metadata.skills?: SkillNode[]`
- ✅ Compatible with Phase 5 recommender output (`UnifiedSongLite`)
- ✅ Used by `SongVaultLoader` (single source of truth)
- ✅ No breaking changes needed

**Readiness:** ✅ **FULLY COMPATIBLE** - Ready for Phase 6

---

### 2.4 Embedding Availability Analysis

**Status:** ⚠️ **PARTIAL** (Needs Verification)

**Embedding Infrastructure:**
- ✅ `songs.embedding` column exists (384 dimensions)
- ✅ HNSW index created (`idx_songs_embedding_hnsw`)
- ✅ Migration: `20251210_add_song_embeddings.sql`

**Embedding Generation:**
- ✅ `src/services/vector/combined-embedding.ts` - Generates combined embeddings
- ✅ `src/services/vector/SongVectorClient.ts` - Vector search client
- ✅ Components: `harmonic-embedder.ts`, `rhythm-embedder.ts`, `skill-embedder.ts`, `metadata-embedder.ts`

**Current Coverage:**
- ⚠️ **UNKNOWN** - Need to verify how many songs have embeddings
- ⚠️ Migration adds column but doesn't populate existing songs
- ⚠️ New songs may have embeddings, but existing 679K+ songs may not

**Impact on Phase 6:**
- **NOT BLOCKING** - Embeddings used for similarity, not required for skill graph
- **OPTIONAL** - Can enhance guided paths with embedding similarity
- **RECOMMENDATION:** Verify embedding coverage, backfill if needed

**Readiness:** ⚠️ **PARTIAL** - Functional but coverage unknown

---

### 2.5 Recommender Output Compatibility Analysis

**Status:** ✅ **FULLY COMPATIBLE**

**Phase 5 Output:**
- `RecommendationResult.song: UnifiedSongLite`
- `RecommendationResponse.results: RecommendationResult[]`

**Phase 6 Requirements:**
- Guided paths need `UnifiedSong[]` or `UnifiedSongLite[]`
- Practice Mode UI needs song data

**Compatibility:**
- ✅ `UnifiedSongLite` is subset of `UnifiedSong`
- ✅ Can convert `UnifiedSongLite` → `UnifiedSong` via `SongVaultLoader.loadSongById()`
- ✅ Recommender already outputs compatible format
- ✅ No adapter needed

**Integration Points:**
- ✅ `src/services/recommender/pipeline.ts` outputs `UnifiedSongLite[]`
- ✅ `src/services/recommender/types.ts` uses `UnifiedSongLite`
- ✅ Phase 6 can consume recommender output directly

**Readiness:** ✅ **FULLY COMPATIBLE** - No changes needed

---

### 2.6 MSMComplete Data Paths Analysis

**Status:** ✅ **MIGRATED TO UNIFIED LOADER**

**Current Implementation:**
- ✅ `MSMComplete.tsx` uses `useSongVaultLoader` hook
- ✅ Converts to `ParsedSong[]` for backward compatibility
- ✅ Auto-loads from Supabase (no CSV required)
- ✅ Data path: Supabase → `SongVaultLoader` → `UnifiedSong[]` → `ParsedSong[]`

**Phase 6 Integration:**
- ✅ Can use same `SongVaultLoader` for practice sessions
- ✅ No separate data path needed
- ✅ UnifiedSong model compatible

**Readiness:** ✅ **READY** - Unified data path operational

---

## 3. TASK LIST

### 3.1 Prerequisites (Must Complete Before Phase 6)

**P0-1: Populate song_skills Junction Table**
- **Priority:** 🔴 **CRITICAL BLOCKER**
- **Effort:** 2-4 hours
- **Tasks:**
  1. Create `SongSkillExtractor` service
  2. Extract skills from:
     - Chord progressions → THEORY skills
     - Rhythm patterns → RHYTHM skills
     - Tempo → TECHNIQUE skills
     - Key signatures → EAR skills
  3. Batch populate `song_skills` table (start with NVX1 scores)
  4. Verify population (target: 50%+ of songs have mappings)

**P0-2: Verify Embedding Coverage**
- **Priority:** 🟡 **HIGH** (Not blocking but recommended)
- **Effort:** 30 minutes
- **Tasks:**
  1. Query Supabase: `SELECT COUNT(*) FROM songs WHERE embedding IS NOT NULL`
  2. If <50% coverage, create backfill script
  3. Run backfill for existing songs (optional, can be async)

---

### 3.2 Core Phase 6 Tasks

**Task 1: Skills → Songs Graph Construction**
- **File:** `src/services/learning/skill-graph.ts` (new)
- **Effort:** 4-6 hours
- **Dependencies:** P0-1 (song_skills populated)
- **Tasks:**
  1. Build bipartite graph: Skills ↔ Songs
  2. Load skill nodes from `SkillTreeService`
  3. Load song-skill mappings from `song_skills` table
  4. Build graph structure (in-memory or Neo4j)
  5. Graph queries:
     - "Next skill after X"
     - "Songs that teach skill Y at difficulty Z"
     - "Prerequisites for skill Y"
  6. Cache graph structure (5-minute TTL)

**Task 2: Prerequisites System**
- **File:** `src/services/learning/prerequisites.ts` (new)
- **Effort:** 2-3 hours
- **Dependencies:** Task 1
- **Tasks:**
  1. Define skill prerequisites (from skill tree parent_id relationships)
  2. Check unlock conditions
  3. Generate skill progression paths
  4. Validate prerequisite chains (no circular dependencies)

**Task 3: Guided Path System**
- **File:** `src/services/learning/guided-path.ts` (new)
- **Effort:** 6-8 hours
- **Dependencies:** Task 1, Task 2, Phase 5 recommender
- **Tasks:**
  1. AI-curated playlist generation based on:
     - Last practiced skills
     - Upcoming skill unlocks
     - Weaknesses (low performance)
     - Strengths (mastery confirmation)
     - NVX1 performance metrics
     - Song difficulty curve
  2. Interleaving: Mix new + review (not sequential)
  3. Adaptive difficulty: Adjust based on performance
  4. Integration with Phase 5 recommender (use CF/CBF results)
  5. Performance: <100ms path generation

**Task 4: Spaced Repetition System**
- **File:** `src/services/learning/spaced-repetition.ts` (new)
- **File:** `src/services/learning/hlr-model.ts` (new)
- **Effort:** 4-6 hours
- **Dependencies:** Practice session tracking (see Task 6)
- **Tasks:**
  1. Implement half-life regression (HLR) model
  2. Calculate retention probability
  3. Schedule optimal review times
  4. Predict forgetting curve for each skill
  5. Boost frequency for struggling skills
  6. Store review schedules in Supabase

**Task 5: Practice Mode UI**
- **File:** `src/pages/PracticeMode.tsx` (new)
- **File:** `src/components/practice/GuidedPlaylist.tsx` (new)
- **File:** `src/components/practice/ProgressTracker.tsx` (new)
- **Effort:** 8-10 hours
- **Dependencies:** Task 3, Task 4
- **Tasks:**
  1. Create Practice Mode page
  2. Display AI-curated guided playlist
  3. Show skill progression visualization
  4. Highlight next unlocks
  5. Progress tracking (skill mastery %)
  6. Streak system (daily practice)
  7. Badges (skill milestones)
  8. Feedback loop ("Too easy/too hard" → adjust)

**Task 6: Practice Session Tracking**
- **File:** `src/services/learning/practice-session.ts` (new)
- **Effort:** 2-3 hours (reduced - table exists)
- **Dependencies:** None (can be parallel with other tasks)
- **Tasks:**
  1. ✅ **VERIFIED:** `rocky_practice_sessions` table already exists
     - Schema: `id`, `user_id`, `song_id`, `skill_id`, `created_at`, `duration_ms`, `performance_metrics` (JSONB)
     - Indexes: `idx_rocky_practice_sessions_user_created`
     - RLS policies: Users can view/create/update own sessions
  2. ⚠️ **MAY NEED:** `user_skill_progress` table (check if exists)
     - If missing: Create table for mastery tracking
     - If exists: Verify schema compatibility
  3. Create practice session service (wrapper around existing table)
  4. Track session start/end
  5. Update skill progress
  6. Calculate mastery levels

---

## 4. AFFECTED FILES

### 4.1 New Files to Create (12 files)

**Services:**
1. `src/services/learning/skill-graph.ts` - Bipartite graph construction
2. `src/services/learning/prerequisites.ts` - Prerequisite system
3. `src/services/learning/guided-path.ts` - Guided path generation
4. `src/services/learning/spaced-repetition.ts` - Spaced repetition scheduling
5. `src/services/learning/hlr-model.ts` - Half-life regression model
6. `src/services/learning/practice-session.ts` - Practice session tracking
7. `src/services/learning/SongSkillExtractor.ts` - Skill extraction (P0-1)

**UI Components:**
8. `src/pages/PracticeMode.tsx` - Practice Mode page
9. `src/components/practice/GuidedPlaylist.tsx` - Guided playlist display
10. `src/components/practice/ProgressTracker.tsx` - Progress visualization
11. `src/components/practice/SkillProgression.tsx` - Skill progression tree
12. `src/components/practice/StreakBadge.tsx` - Streak/badge display

**Database:**
13. ⚠️ `supabase/migrations/20251209_create_user_skill_progress.sql` - User skill progress table (if needed, verify existing first)

**Types:**
14. `src/services/learning/types.ts` - Phase 6 type definitions

**Documentation:**
15. `docs/planning/PHASE_6_COMPLETION_REPORT.md` - Completion report (end of phase)

---

### 4.2 Files to Modify (5 files)

1. `src/services/songvault/SongVaultLoader.ts`
   - **Change:** Ensure skill nodes loaded from `song_skills` junction
   - **Risk:** Low (additive change)

2. `src/pages/SongVault.tsx`
   - **Change:** Add "Practice Mode" navigation link
   - **Risk:** Low (UI addition)

3. `src/services/recommender/pipeline.ts`
   - **Change:** Integrate with guided path system (optional enhancement)
   - **Risk:** Low (additive integration)

4. `src/services/skilltree/SkillTreeService.ts`
   - **Change:** Add prerequisite query methods (if needed)
   - **Risk:** Low (additive methods)

5. `package.json`
   - **Change:** Add dependencies (if needed for graph library)
   - **Risk:** Low (dependency addition)

---

## 5. NEW SERVICES REQUIRED

### 5.1 Skill Graph Service

**Purpose:** Build and query Skills ↔ Songs bipartite graph

**Technology Options:**
1. **In-Memory Graph** (Recommended for Phase 6)
   - Use Map/Set data structures
   - Fast for <10K skills, <1M songs
   - No external dependencies
   - **Pros:** Simple, fast, no setup
   - **Cons:** Limited to in-memory size

2. **Neo4j** (Future scaling)
   - Graph database
   - Better for complex queries
   - **Pros:** Scalable, powerful queries
   - **Cons:** Requires Neo4j setup, overkill for Phase 6

**Recommendation:** Start with in-memory graph, migrate to Neo4j in Phase 11 if needed.

---

### 5.2 Spaced Repetition Service

**Purpose:** Calculate optimal review times using HLR model

**Algorithm:**
- Half-Life Regression (HLR) model
- Predicts forgetting curve
- Schedules reviews before predicted forgetting
- Adjusts based on user performance

**Dependencies:**
- Practice session data (Task 6)
- User skill progress tracking

---

### 5.3 Guided Path Service

**Purpose:** Generate AI-curated practice playlists

**Inputs:**
- User's current skill level
- Last practiced skills
- Upcoming skill unlocks
- Performance metrics
- Phase 5 recommender results

**Outputs:**
- Ordered playlist of songs
- Skill progression path
- Difficulty curve
- Interleaving schedule (new + review)

**Integration:**
- Uses Phase 5 recommender for candidate songs
- Uses skill graph for skill progression
- Uses spaced repetition for review scheduling

---

## 6. MIGRATION RISKS

### 6.1 Database Migration Risks

**Risk Level:** 🟡 **MEDIUM**

**Risks:**
1. **Practice Sessions Table Creation**
   - **Risk:** Table creation may fail if schema conflicts
   - **Mitigation:** Use `IF NOT EXISTS`, test in dev first
   - **Rollback:** Drop table if needed

2. **User Skill Progress Table Creation**
   - **Risk:** Similar to above
   - **Mitigation:** Same as above

3. **song_skills Population**
   - **Risk:** Large batch operation may timeout
   - **Mitigation:** Process in chunks (1000 songs at a time)
   - **Rollback:** Can delete and re-run

**Overall:** Low risk, standard migration patterns

---

### 6.2 Data Model Risks

**Risk Level:** 🟢 **LOW**

**Risks:**
1. **UnifiedSong Compatibility**
   - **Risk:** None - already supports skills
   - **Mitigation:** No changes needed

2. **Recommender Output Compatibility**
   - **Risk:** None - already uses UnifiedSongLite
   - **Mitigation:** No changes needed

**Overall:** No breaking changes expected

---

### 6.3 Performance Risks

**Risk Level:** 🟡 **MEDIUM**

**Risks:**
1. **Graph Construction Performance**
   - **Risk:** Building graph for 5,821 skills + 679K songs may be slow
   - **Mitigation:** 
     - Lazy load graph (build on demand)
     - Cache graph structure (5-minute TTL)
     - Use incremental updates
   - **Target:** <100ms graph construction

2. **Guided Path Generation Performance**
   - **Risk:** Complex path generation may exceed <100ms target
   - **Mitigation:**
     - Pre-compute common paths
     - Cache user-specific paths (10-minute TTL)
     - Use Phase 5 recommender (already optimized)
   - **Target:** <100ms path generation (p95)

**Overall:** Manageable with caching and optimization

---

### 6.4 Integration Risks

**Risk Level:** 🟢 **LOW**

**Risks:**
1. **Phase 5 Recommender Integration**
   - **Risk:** None - already compatible
   - **Mitigation:** Direct integration, no adapter needed

2. **MSMComplete Integration**
   - **Risk:** None - uses unified loader
   - **Mitigation:** No changes needed

**Overall:** Low integration risk

---

## 7. VALIDATION STRATEGY

### 7.1 Unit Tests

**Files to Test:**
1. `src/services/learning/skill-graph.ts`
   - Test graph construction
   - Test graph queries
   - Test prerequisite chains

2. `src/services/learning/spaced-repetition.ts`
   - Test HLR model calculations
   - Test review scheduling
   - Test retention probability

3. `src/services/learning/guided-path.ts`
   - Test path generation
   - Test interleaving logic
   - Test adaptive difficulty

**Test Coverage Target:** 80%+ for new services

---

### 7.2 Integration Tests

**Test Scenarios:**
1. **End-to-End Guided Path**
   - User starts practice → Guided path generated → Songs loaded → Practice session tracked

2. **Spaced Repetition Scheduling**
   - User practices skill → Progress updated → Review scheduled → Review appears at correct time

3. **Skill Progression**
   - User masters skill → Prerequisites checked → Next skill unlocked → Guided path updated

**Test Files:**
- `src/services/learning/__tests__/guided-path.integration.test.ts`
- `src/services/learning/__tests__/spaced-repetition.integration.test.ts`

---

### 7.3 Performance Tests

**Targets:**
- Graph construction: <100ms
- Guided path generation: <100ms (p95)
- Practice session save: <50ms
- Progress update: <50ms

**Test Files:**
- `src/services/learning/__tests__/performance.test.ts`

---

### 7.4 Browser Verification

**Checklist:**
- [ ] Practice Mode page loads
- [ ] Guided playlist displays
- [ ] Progress tracker updates
- [ ] Streak system works
- [ ] Badges awarded correctly
- [ ] "Too easy/too hard" feedback adjusts difficulty
- [ ] No console errors
- [ ] No React warnings

---

## 8. PHOENIX/NVX1 INVARIANTS CHECKLIST

### 8.1 Phoenix Protocol Compliance

- [x] **No modifications to `src/runtime/NVX1ScoreRuntime.ts`**
- [x] **No modifications to `src/quantum-rails/**`**
- [x] **No modifications to `src/audio-engine/**`**
- [x] **No modifications to Khronos timing systems**
- [x] **All score operations use `NVX1ScoreContract`**
- [x] **No breaking changes to existing systems**

**Status:** ✅ **FULLY COMPLIANT** - Phase 6 is isolated to learning services

---

### 8.2 UnifiedSong Model Compliance

- [x] **All outputs use `UnifiedSong` or `UnifiedSongLite`**
- [x] **No new song models created**
- [x] **Backward compatibility maintained**
- [x] **Uses `SongVaultLoader` for all song data**

**Status:** ✅ **FULLY COMPLIANT** - Uses existing models

---

### 8.3 SEB Isolation Compliance (CRITICAL)

**SEB Status:** 🔒 **DEAD ARCHIVE (READ-ONLY FORENSICS ONLY)**

**Rules Enforced:**
- [x] **No SEB code touched** — SEB is read-only archive
- [x] **No SEB epics or tasks created** — SEB is not an active project
- [x] **No SEB modifications allowed** — SEB exists only for forensic knowledge extraction
- [x] **All Phase 6 work is MSM-only** — Zero SEB contamination
- [x] **SEB knowledge extraction only** — Extract insights to MSM, never modify SEB

**Phase 6 Validation:**
- ✅ All file paths are MSM-only (`src/services/learning/**`, `src/components/practice/**`)
- ✅ All dependencies are MSM services (SongVaultLoader, SkillTreeService, Recommender)
- ✅ All database operations target Supabase (MSM infrastructure, not SEB code)
- ✅ Zero SEB code paths in execution plan

**Status:** ✅ **FULLY COMPLIANT** - Phase 6 is 100% MSM-only, SEB completely isolated

**See:** `docs/planning/PHASE6_SEB_ISOLATION_CONFIRMATION.md` for complete validation

---

## 9. EXECUTION SEQUENCE

### Phase 6.0: Prerequisites (2-4 hours)
1. ✅ Populate `song_skills` junction table (P0-1)
2. ⚠️ Verify embedding coverage (P0-2, optional)

### Phase 6.1: Core Graph & Prerequisites (6-9 hours)
1. Build skill graph service
2. Implement prerequisites system
3. Unit tests

### Phase 6.2: Spaced Repetition (4-6 hours)
1. Implement HLR model
2. Create practice session tracking
3. Schedule review system
4. Unit tests

### Phase 6.3: Guided Path System (6-8 hours)
1. Implement guided path generation
2. Integrate with Phase 5 recommender
3. Add interleaving logic
4. Add adaptive difficulty
5. Integration tests

### Phase 6.4: Practice Mode UI (8-10 hours)
1. Create Practice Mode page
2. Build guided playlist component
3. Build progress tracker
4. Add streak system
5. Add badges
6. Browser verification

### Phase 6.5: Integration & Validation (4-6 hours)
1. End-to-end integration tests
2. Performance tests
3. Browser verification
4. Generate completion report

**Total Estimated Effort:** 28-41 hours (reduced due to existing practice_sessions table)

---

## 10. BLOCKING ISSUES

### 🔴 **CRITICAL BLOCKER: song_skills Junction Table**

**Issue:** `song_skills` table exists but is sparsely populated (<1% of songs)

**Impact:** Cannot build Skills → Songs graph without populated data

**Resolution Required:**
1. Create `SongSkillExtractor` service
2. Batch populate `song_skills` table
3. Target: 50%+ of songs have skill mappings

**Estimated Time:** 2-4 hours

**Status:** ⏳ **MUST COMPLETE BEFORE PHASE 6 EXECUTION**

---

### 🟡 **HIGH PRIORITY: Embedding Coverage Verification**

**Issue:** Unknown how many songs have embeddings

**Impact:** May limit guided path quality (embeddings enhance similarity)

**Resolution Required:**
1. Query Supabase for embedding coverage
2. If <50%, create backfill script (can run async)

**Estimated Time:** 30 minutes (verification) + 2-4 hours (backfill if needed)

**Status:** ⚠️ **RECOMMENDED BUT NOT BLOCKING**

---

## 11. SUCCESS METRICS

### Functional Targets:
- ✅ Skills → Songs graph operational
- ✅ Guided path system working
- ✅ Spaced repetition scheduling functional
- ✅ Practice Mode UI complete
- ✅ Performance: <100ms path generation

### Business Targets:
- **+40% practice retention** (measured via practice session completion rate)
- **+30% skill progression** (measured via skill mastery rate)

### Technical Targets:
- Graph construction: <100ms
- Path generation: <100ms (p95)
- Practice session save: <50ms
- Progress update: <50ms

---

## 12. DEPENDENCIES & INTEGRATION POINTS

### With Phase 5 (Hybrid Recommender):
- ✅ Uses `RecommendationResult[]` as candidate songs
- ✅ Integrates CF/CBF results into guided paths
- ✅ Uses persona weights for personalization

### With Phase 4 (Vector Intelligence):
- ✅ Optional: Uses embeddings for similarity enhancement
- ✅ Not required: Can work without embeddings

### With Phase 3.2 (Edge Service):
- ✅ Uses `SongVaultEdgeClient` for song loading
- ✅ Compatible with edge caching

### With Phase 1 (Unified Song Loader):
- ✅ Uses `SongVaultLoader` for all song data
- ✅ Uses `UnifiedSong` model throughout

---

## 13. RISK MITIGATION STRATEGIES

### 13.1 Graph Construction Performance

**Strategy:**
- Lazy load graph (build on first query)
- Cache graph structure (5-minute TTL)
- Incremental updates (only add new songs/skills)
- Use Map/Set for O(1) lookups

**Fallback:**
- If graph too large, use database queries instead
- Query `song_skills` table directly for skill → songs

---

### 13.2 Guided Path Generation Performance

**Strategy:**
- Pre-compute common paths (cache for 10 minutes)
- Use Phase 5 recommender (already optimized)
- Limit path length (max 20 songs)
- Parallel computation where possible

**Fallback:**
- If exceeds 100ms, return cached path
- Show loading state while generating

---

### 13.3 Practice Session Tracking Performance

**Strategy:**
- Batch session saves (save every 5 sessions)
- Use Supabase batch inserts
- Async progress updates

**Fallback:**
- If save fails, queue for retry
- Show user notification if persistent failure

---

## 14. PHOENIX/NVX1 COMPLIANCE VERIFICATION

### ✅ **ALL INVARIANTS MAINTAINED**

**Verified:**
- ✅ No Phoenix Protocol violations
- ✅ No NVX1 Score Contract violations
- ✅ No Khronos timing system modifications
- ✅ UnifiedSong model compliance
- ✅ SEB frozen (no SEB code touched)
- ✅ Zero breaking changes

**Isolation:**
- Phase 6 code isolated to `src/services/learning/`
- New UI components in `src/components/practice/`
- New page: `src/pages/PracticeMode.tsx`
- No modifications to existing systems

---

## 15. NEXT STEPS (AFTER CHIEF APPROVAL)

1. **Execute P0-1:** Populate `song_skills` junction table
2. **Execute P0-2:** Verify embedding coverage (optional)
3. **Begin Phase 6.1:** Build skill graph service
4. **Post Breakroom Activity:** "Starting Phase 6.1: Skill Graph Construction"
5. **Follow Execution Sequence:** Phase 6.0 → 6.1 → 6.2 → 6.3 → 6.4 → 6.5

---

## 16. CHIEF APPROVAL CHECKLIST

Before Phase 6 execution begins, Chief must approve:

- [ ] **P0-1 Complete:** `song_skills` junction table populated (50%+ coverage)
- [ ] **P0-2 Verified:** Embedding coverage checked (optional)
- [ ] **Plan Approved:** This execution plan approved
- [ ] **Dependencies Verified:** Phase 5 complete, Phase 4 complete
- [ ] **Risk Assessment:** All risks acknowledged and mitigated
- [ ] **Timeline Approved:** 30-43 hour estimate acceptable

---

## 17. BREAKROOM PROTOCOL

**Activities to Post:**
1. ✅ Task claimed: "Phase 6 — Learning Engine preparation" (DONE)
2. ⏳ Discovery: "Pre-execution discovery sweep complete"
3. ⏳ Discovery: "song_skills population required before Phase 6"
4. ⏳ Plan ready: "Phase 6 Execution Plan Draft generated"
5. ⏳ Awaiting approval: "Holding until Chief approval"

**No code changes until approval.**

---

## 18. SUMMARY

**Phase 6 Readiness:**
- ✅ Master prompt loaded
- ✅ Discovery sweep complete
- ✅ Execution plan drafted
- ⚠️ **BLOCKER:** `song_skills` table must be populated (P0-1)
- ⚠️ **RECOMMENDED:** Verify embedding coverage (P0-2)

**Estimated Effort:** 30-43 hours (including prerequisites)

**Risk Level:** 🟡 **MEDIUM** (manageable with mitigation strategies)

**Status:** 📋 **DRAFT — AWAITING CHIEF APPROVAL**

---

**Report Generated:** 2025-12-09  
**Next Action:** Await Chief approval to begin Phase 6 execution
