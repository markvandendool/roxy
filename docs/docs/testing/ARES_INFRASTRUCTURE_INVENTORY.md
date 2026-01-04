# A.R.E.S. Infrastructure Inventory

**Generated:** 2025-12-11  
**Purpose:** Complete mapping of all testing infrastructure for ARES consolidation

---

## Executive Summary

- **Total Test Files:** 503 in `tests/` + 271 in `src/**/__tests__/` = **774 test files**
- **Test Scripts:** 4 in `scripts/diagnostics/` + multiple in other script directories
- **Diagnostic APIs:** 15+ window diagnostic entrypoints
- **CI Workflows:** 40+ GitHub Actions workflows

---

## Test Directory Classification

### GREEN (Keep - Unique, Valuable)

#### `tests/unit/` (50 files)
- **Status:** KEEP
- **ARES Module:** `ARES.Core`
- **Purpose:** Vitest unit tests
- **Examples:**
  - `nvx1-diagnostics.test.ts`
  - `audioRouterNoteOff.test.ts`
  - Various component unit tests

#### `src/**/__tests__/` (271 files)
- **Status:** KEEP
- **ARES Module:** `ARES.Core`
- **Purpose:** Co-located unit tests
- **Key Locations:**
  - `src/audio/__tests__/UniversalAudioRouter.test.ts`
  - `src/services/audio/__tests__/`
  - `src/quantum-rails/__tests__/`
  - `src/models/EventSpine/__tests__/`

#### `tests/khronos/` (5 files)
- **Status:** KEEP
- **ARES Module:** `ARES.Khronos`
- **Files:**
  - `khronos-loop-timing.spec.ts`
  - `khronos-loop-sweep.spec.ts`
  - `cdp-perf-trace.spec.ts`
  - `khronos-north-star-migration.spec.ts`
  - `quantum-rails-perf-forensic.spec.ts`

#### `tests/savage3/` (27 files)
- **Status:** KEEP (consolidate into ARES.Savage3)
- **ARES Module:** `ARES.Savage3`
- **Subdirectories:**
  - `audio-queue/` (5 files) → `ARES.Audio`
  - `widgets/` (4 files) → `ARES.Widgets`
  - `olympus/` (3 files) → `ARES.Widgets`
  - Core SAVAGE³ tests (15 files) → `ARES.Savage3`

#### `scripts/luno/validate-*.mjs` (5 files)
- **Status:** KEEP (wrap in ARES.Gov)
- **ARES Module:** `ARES.Gov`
- **Files:**
  - `validate-governance.mjs`
  - `validate-epic-ids.mjs`
  - `validate-luno-order.mjs`
  - `validate-story-task-uniqueness.mjs`
  - `check-chief-approval.mjs`

---

### YELLOW (Merge - Overlaps, Consolidate)

#### `tests/audio/` (32 files)
- **Status:** MERGE
- **ARES Module:** `ARES.Audio`
- **Overlaps with:**
  - `tests/e2e/*audio*` tests
  - `tests/savage3/audio-queue/` tests
  - Audio diagnostic scripts
- **Action:** Consolidate all audio tests into `ARES.Audio`

#### `tests/e2e/` (100+ files)
- **Status:** MERGE
- **ARES Modules:** Multiple (split by purpose)
- **Classification:**
  - `*audio*` → `ARES.Audio`
  - `*timeline*` → `ARES.Khronos`
  - `*visual*` → `ARES.Render`
  - `*widget*` → `ARES.Widgets`
  - General E2E → `ARES.Savage3`

#### `tests/visual/` + `tests/visual-regression/` (9 files)
- **Status:** MERGE
- **ARES Module:** `ARES.Render`
- **Overlaps with:** `tests/e2e/*visual*` tests
- **Action:** Consolidate all visual tests into `ARES.Render`

#### `scripts/diagnostics/` (4 files)
- **Status:** MERGE
- **ARES Modules:** `ARES.Runtime` / `ARES.SavageLite`
- **Files:**
  - `headless-diagnostics.mjs` → `ARES.Runtime`
  - `nvx1-kronos-smoke.mjs` → `ARES.SavageLite`
  - `zero-edit-stabilization-diagnostics.mjs` → `ARES.Runtime`

#### `scripts/metronome/` (8 files)
- **Status:** MERGE
- **ARES Module:** `ARES.Audio`
- **Action:** Integrate metronome tests into `ARES.Audio`

---

### RED (Delete - Deprecated, Manual-Only, Superseded)

#### `tests/manual/` (1 file)
- **Status:** DELETE
- **Reason:** Manual-only testing, not automatable
- **File:** `VERIFY_ROCKY_TABLATURE.md`

#### `tests/static/` (1 file)
- **Status:** DELETE
- **Reason:** Legacy, superseded

#### `tests/debug/` (2 files)
- **Status:** DELETE (or merge into ARES.Runtime)
- **Reason:** Debug-only, should be part of ARES.Runtime
- **Action:** Review and merge useful parts into ARES.Runtime

#### Duplicate emergency audio diagnostics
- **Status:** DELETE
- **Files:**
  - `tests/e2e/emergency-audio-diagnostic-v2.spec.ts`
  - `tests/e2e/emergency-audio-diagnostic-v3.spec.ts`
- **Action:** Keep latest, delete older versions

#### Duplicate timeline forensic tests
- **Status:** DELETE
- **Files:** Multiple `nvx1-timeline-forensic*` variants
- **Action:** Consolidate into single `ARES.Khronos` test

---

## Diagnostic Entrypoints Inventory

### Window Diagnostic APIs

1. **`window.NVX1Diag`** (DevPanel)
   - **Location:** `src/components/dev/DevPanel.tsx`
   - **ARES Module:** `ARES.SavageLite` / `ARES.Runtime`
   - **Methods:**
     - `sampleFrameBudget()`
     - `sampleCursorDrift()`
     - `sampleGPUPassCost()`
     - `sampleWidgetViolations()`
     - `sampleApolloDrift()`
     - `sampleTimingSignature()`
     - `autoLoadTestScore()`
     - `runHeadlessDiagnostics()`

2. **`window.NVX1_FORENSICS`** (Existing Agent)
   - **Location:** `public/diagnostics/NVX1_FORENSIC_AGENT.js`
   - **ARES Module:** `ARES.Runtime`
   - **Methods:**
     - `run()` - Main forensic analysis

3. **`window.__audioPlaybackService`**
   - **Location:** `src/services/audio/AudioPlaybackService.ts`
   - **ARES Module:** `ARES.Audio`
   - **Methods:**
     - `getStrictReadiness()`
     - `getReadinessState()`

4. **`window.__khronos`** / `window.__KHRONOS__`
   - **Location:** `src/khronos/KhronosEngine.ts`
   - **ARES Module:** `ARES.Khronos`
   - **Properties:**
     - `isPlaying`
     - `tempo`
     - `beatFloor`
     - `tickHz`

5. **`window.audioRouter`**
   - **Location:** `src/services/audio/bootstrapAudioSystem.ts`
   - **ARES Module:** `ARES.Audio`
   - **Methods:**
     - `isReady()`
     - `getCurrentBackendName()`
     - `getQueueLength()`

6. **`window.apollo`** / `window.Apollo`
   - **Location:** `src/services/globalApollo.ts`
   - **ARES Module:** `ARES.Audio`
   - **Properties:**
     - `isReady`
     - `engineName`

7. **`window.__AUDIO_TELEMETRY__`**
   - **Location:** `src/services/audio/AudioTelemetry.ts`
   - **ARES Module:** All modules
   - **Properties:**
     - `counters`
     - `gauges`

8. **`window.__AUDIO_SYSTEM_READY__`**
   - **Location:** `src/services/audio/AudioSystemReady.ts`
   - **ARES Module:** `ARES.Audio`
   - **Type:** Boolean flag

9. **`window.__playbackController`**
   - **Location:** `src/services/playback/PlaybackController.ts`
   - **ARES Module:** `ARES.Audio`
   - **Methods:**
     - `play()`
     - `pause()`
     - `stop()`

10. **`window.railInstrumentRegistry`**
    - **Location:** `src/apollo/registry/RailInstrumentRegistry.ts`
    - **ARES Module:** `ARES.Audio`
    - **Methods:**
      - `getRailConfig()`
      - `playNote()`

11. **`window.audioBackendRegistry`**
    - **Location:** `src/services/audio/backends/AudioBackendRegistry.ts`
    - **ARES Module:** `ARES.Audio`
    - **Methods:**
      - `listBackends()`
      - `getCurrentName()`

12. **`window.GlobalAudioContext`**
    - **Location:** `src/audio/core/GlobalAudioContext.ts`
    - **ARES Module:** `ARES.Audio`
    - **Methods:**
      - `get()`
      - `ensureRunning()`

13. **`window.__AudioWorkletStatus`**
    - **Location:** Various AudioWorklet processors
    - **ARES Module:** `ARES.Audio`
    - **Properties:**
      - `loaded`
      - `processors`
      - `errors`

14. **`window.__DIAG.getRuntimeSignature()`**
    - **Location:** DevPanel / Diagnostic utilities
    - **ARES Module:** `ARES.Runtime`
    - **Purpose:** Runtime signature extraction

15. **`window.checkAudioSystemStatus()`**
    - **Location:** `src/services/audio/bootstrapAudioSystem.ts`
    - **ARES Module:** `ARES.Audio`
    - **Purpose:** Audio system diagnostic utility

---

## Script Classification

### Diagnostic Scripts

#### `scripts/diagnostics/` (4 files)
- **Status:** MERGE into ARES
- **Mapping:**
  - `headless-diagnostics.mjs` → `ARES.Runtime`
  - `nvx1-kronos-smoke.mjs` → `ARES.SavageLite`
  - `zero-edit-stabilization-diagnostics.mjs` → `ARES.Runtime`

#### `scripts/metronome/` (8 files)
- **Status:** MERGE into `ARES.Audio`
- **Files:**
  - `jitter_test_harness.mjs` → `ARES.Audio`
  - `publish-jitter-metrics.mjs` → `ARES.Audio` (telemetry)
  - `contrast-check.mjs` → `ARES.Audio`
  - `pa11y-check.mjs` → `ARES.Audio`
  - `axe-audit.mjs` → `ARES.Audio`

#### `scripts/nvx1/` (22 files)
- **Status:** MERGE into `ARES.Runtime`
- **Purpose:** NVX1 pipeline validation
- **Action:** Integrate into `ARES.Runtime` module

#### `scripts/score/` (4 files)
- **Status:** MERGE into `ARES.Render`
- **Files:**
  - `timeline-regression.ts` → `ARES.Khronos`
  - `capture-tab-snapshots.mjs` → `ARES.Render`
  - `compare-tab-snapshots.mjs` → `ARES.Render`
  - `profile-tab-renderer.mjs` → `ARES.Render`

#### `scripts/luno/validate-*.mjs` (5 files)
- **Status:** MERGE into `ARES.Gov`
- **Action:** Wrap in `ARES.Gov` module

---

## CI Workflow Classification

### Keep & Migrate to ARES

#### `.github/workflows/validate-luno-governance.yml`
- **Status:** MIGRATE to `ARES.Gov`
- **Action:** Update to use `pnpm ares gov`

#### `.github/workflows/e2e.yml`
- **Status:** MIGRATE to `ARES.Savage3`
- **Action:** Update to use `pnpm ares savage3`

#### `.github/workflows/nightly-drift-audit.yml`
- **Status:** MIGRATE to `ARES.Khronos`
- **Action:** Update to use `pnpm ares khronos`

#### `.github/workflows/test.yml`
- **Status:** MIGRATE to `ARES.Core`
- **Action:** Update to use `pnpm ares core`

### Create New ARES Workflows

#### `.github/workflows/ares-pr-validation.yml` (NEW)
- **Purpose:** PR validation
- **Modules:** `ARES.Core`, `ARES.Gov`, `ARES.Audio` (fast), `ARES.Render` (fast)

#### `.github/workflows/ares-savage-lab.yml` (NEW)
- **Purpose:** Nightly brutalizer
- **Modules:** `ARES.Savage3`, `ARES.SavageLab`, `ARES.Widgets`, `ARES.Render`, `ARES.Khronos`

---

## ARES Module Mapping

### ARES.Core
- `tests/unit/` (50 files)
- `src/**/__tests__/` (271 files)
- `scripts/luno/validate-*.mjs` (5 files)
- Lint checks
- TypeScript compilation

### ARES.Audio
- `tests/audio/` (32 files)
- `tests/e2e/*audio*` (multiple)
- `tests/savage3/audio-queue/` (5 files)
- `scripts/metronome/` (8 files)
- Audio diagnostic scripts

### ARES.Runtime
- `public/diagnostics/NVX1_FORENSIC_AGENT.js` (existing)
- `scripts/diagnostics/headless-diagnostics.mjs`
- `scripts/diagnostics/zero-edit-stabilization-diagnostics.mjs`
- `scripts/nvx1/` (22 files)

### ARES.SavageLite
- `scripts/diagnostics/nvx1-kronos-smoke.mjs`
- Fast DevPanel checks (0.2-1.5s)
- Uses `window.NVX1Diag` APIs

### ARES.Savage3
- `tests/savage3/` (27 files)
- `tests/e2e/` (general E2E tests)
- Browser harness tests

### ARES.SavageLab
- CI-only brutalizer
- Extended stress tests
- GPU memory pressure
- Async starvation detection

### ARES.Widgets
- `tests/savage3/widgets/` (4 files)
- `tests/savage3/olympus/` (3 files)
- Widget/EventSpine integration tests

### ARES.Render
- `tests/visual/` (7 files)
- `tests/visual-regression/` (2 files)
- `tests/e2e/*visual*` (multiple)
- `scripts/score/capture-*.mjs` (3 files)
- GPU/WASM tests

### ARES.Khronos
- `tests/khronos/` (5 files)
- `tests/e2e/*timeline*` (multiple)
- `tests/audio/nvx1-timeline*` (multiple)
- `scripts/score/timeline-regression.ts`

### ARES.Gov
- `scripts/luno/validate-*.mjs` (5 files)
- `.github/workflows/validate-luno-governance.yml`
- Epic ID validation
- Canonical order validation

---

## Deprecation Timeline

### Phase 1 (Week 1-2)
- Create ARES modules
- Old tests still work
- No file moves

### Phase 2 (Week 3-4)
- Tests migrated to ARES
- Old commands deprecated (warnings)
- ARES commands work

### Phase 3 (Week 5-6)
- Old commands removed
- ARES-only
- Cleanup deprecated files

### Phase 4 (Week 7+)
- Final cleanup
- Documentation updates
- Performance optimization

---

## Files to Create

### Phase 1 Outputs
- `docs/testing/ARES_INFRASTRUCTURE_INVENTORY.md` (this file)
- `docs/testing/ARES_MIGRATION_MAP.json` (classification JSON)

---

**END OF INVENTORY**
























