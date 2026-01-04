# Bun Migration Epic - Complete Engineering Plan
## Ultra-Dense, Engineering-Grade, Zero Fluff

**Epic ID:** `EPIC-BUN-MIGRATION`  
**Status:** 📋 Planning Complete - Awaiting R15 Certification  
**Timing:** Post-Phoenix V1 (R15), Pre-SEB AAA Wave 3  
**Oracle Score:** 19.2/20 (A++)

---

## Phase 0: Research (COMPLETE)

**Deliverable:** `docs/planning/BUN_MIGRATION_RESEARCH_PROMPT.md` (100 metrics)  
**Status:** ✅ Complete

---

## Phase 0.5: Epic Structure

### Critical Invariants (NON-NEGOTIABLE)

```typescript
// .cursorrules invariant
BUN_MIGRATION_INVARIANT = {
  FORBIDDEN_PATHS: [
    '/src/phoenix/**',
    '/src/khronos/**',
    '/src/nvx1*/**',
    '/src/audio-engine/**'
  ],
  UNLOCK_CONDITION: 'after R15 signed-off by Codex1',
  LOCKFILE_VALIDATION: 'pnpm-lock.yaml === bun.lock dependency tree (same versions)'
}
```

### Performance Targets

| Metric | Baseline | Target | Multiplier |
|--------|----------|--------|------------|
| HMR Latency | ~1-2s | <50ms | 20-40× |
| TS Transpile | esbuild | Bun native | 4-8× |
| Test Execution | Vitest ~8-10s | Bun ~3s | 2-5× |
| Install Time | pnpm ~45s | Bun <5s | ~15× |
| Dev Startup | Vite ~3s | Bun <1s | 3× |

---

## Sprint 1: Parallel Bun Toolchain Setup

**Sprint ID:** `BUN-S1`  
**Duration:** 1 week  
**Objective:** Establish Bun alongside Node.js without breaking existing workflows

### Tasks

**BUN-S1-T1: Create bunfig.toml Configuration**
- **Type:** configuration
- **Priority:** critical
- **Story Points:** 3
- **Acceptance:**
  - `bunfig.toml` with registry, install, test settings
  - `linker=isolated` (match pnpm behavior)
  - Workspace configuration for monorepo
  - Registry matches npm/pnpm setup

**BUN-S1-T2: Mirror Scripts (dev-bun, test-bun, build-bun)**
- **Type:** chore
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - Parallel scripts: `dev-bun`, `test-bun`, `build-bun`, `install-bun`
  - Node scripts remain intact
  - Feature flag: `USE_BUN=true` or env var
  - Cross-platform tested (Windows/POSIX)

**BUN-S1-T3: Generate Bun Lockfile**
- **Type:** chore
- **Priority:** critical
- **Story Points:** 2
- **Acceptance:**
  - `bun.lock` generated and committed
  - Dependency versions match pnpm resolution
  - Install <5s (vs pnpm ~45s)
  - Both lockfiles coexist

**BUN-S1-T4: Verify Package Installation Performance**
- **Type:** test
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - Cold install: bun <5s vs pnpm ~45s (15×)
  - Warm install: bun <1s vs pnpm ~10s
  - All binaries accessible via `bun x` or `.bun/bin`
  - Metrics documented

**BUN-S1-T5: Test Environment Setup (HappyDOM)**
- **Type:** configuration
- **Priority:** high
- **Story Points:** 5
- **Acceptance:**
  - HappyDOM installed
  - `bun-test-setup.ts` initializes DOM
  - `bun test --preload=bun-test-setup.ts` works
  - React Testing Library tests pass

**BUN-S1-T6: Create Mock Audio Subsystems**
- **Type:** infrastructure
- **Priority:** critical
- **Story Points:** 8
- **Description:** Create `MockAudioContext`, `MockAudioWorkletNode`, `MockAudioWorklet` for Bun test runner
- **Acceptance:**
  - MockAudioContext with deterministic `currentTime`
  - MockAudioWorkletNode with `port.onmessage` stub
  - MockAudioWorklet with `addModule()` no-op
  - All audio tests use mocks under Bun

**BUN-S1-T7: Create Mock WebGPU Subsystems**
- **Type:** infrastructure
- **Priority:** critical
- **Story Points:** 8
- **Description:** Create `MockGPUDevice`, `MockGPUAdapter`, `MockGPUQueue` for Bun test runner
- **Acceptance:**
  - MockGPUAdapter with `requestDevice()` stub
  - MockGPUDevice with `createRenderPipeline()` stub
  - Conditional GPU init: `if (!navigator.gpu) useMock()`
  - Renderer tests use mocks under Bun

**BUN-S1-T8: Add .cursorrules Invariant**
- **Type:** configuration
- **Priority:** critical
- **Story Points:** 2
- **Description:** Add BUN_MIGRATION invariant to prevent touching Phoenix/SEB code
- **Acceptance:**
  - Invariant added to `.cursorrules`
  - Forbidden paths enforced
  - Unlock condition documented
  - Lockfile validation check added

---

## Sprint 2: Test Suite Migration (Vitest → Bun Test)

**Sprint ID:** `BUN-S2`  
**Duration:** 1-2 weeks  
**Objective:** Migrate all unit/integration tests to Bun test runner

### Tasks

**BUN-S2-T1: Update Test Imports (vitest → bun:test)**
- **Type:** refactor
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - All `import { describe, it, expect, vi } from 'vitest'` → `import { describe, test, expect } from 'bun:test'`
  - `import { vi } from 'bun:test'` for mocks
  - Globals available (Bun provides)
  - No Vitest imports remain

**BUN-S2-T2: Migrate Mocking System**
- **Type:** refactor
- **Priority:** critical
- **Story Points:** 8
- **Description:** Verify `vi.mock()`, `vi.fn()`, `vi.spyOn()` work with Bun, create compatibility map
- **Acceptance:**
  - All mocks function identically
  - Module mocking works
  - Timer mocks work (`vi.useFakeTimers`)
  - Compatibility map: `vitest.mock → bun.test.mock` equivalence table

**BUN-S2-T3: Update Snapshot Tests**
- **Type:** test
- **Priority:** medium
- **Story Points:** 3
- **Acceptance:**
  - Snapshots regenerated: `bun test --update-snapshots`
  - Format compatible
  - No false positives
  - Snapshots committed

**BUN-S2-T4: Configure Coverage Reporting**
- **Type:** configuration
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - `bun test --coverage --coverage-reporter=lcov`
  - Coverage within 1% of Vitest baseline
  - CI uploads correctly
  - Excludes test files and node_modules

**BUN-S2-T5: Run Full Test Suite Validation**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - 100% test pass rate (same as Vitest)
  - Execution time: 2-5× faster
  - All test types pass
  - Performance metrics documented

**BUN-S2-T6: Update CI Test Jobs**
- **Type:** ci/cd
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - CI runs `bun test --coverage`
  - Parallel Node/Vitest job for validation
  - Test execution time reduced
  - Coverage uploads work

**BUN-S2-T7: Remove Vitest Dependency**
- **Type:** chore
- **Priority:** medium
- **Story Points:** 2
- **Acceptance:**
  - Vitest removed from package.json
  - `vitest.config.ts` removed
  - Documentation updated
  - No Vitest references remain

**BUN-S2-T8: Audio/GPU Test Gating**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Description:** Skip or mock audio/GPU tests under Bun, ensure Playwright handles real browser tests
- **Acceptance:**
  - Audio tests skip under Bun (use mocks)
  - GPU tests skip under Bun (use mocks)
  - Playwright remains Node-driven
  - Real browser tests for audio/GPU

---

## Sprint 3: Savage³ Core Harness on Bun

**Sprint ID:** `BUN-S3`  
**Duration:** 1 week  
**Objective:** Validate Bun compatibility with critical systems

### Tasks

**BUN-S3-T1: Create Bun-Compatible Savage³ Harness**
- **Type:** test
- **Priority:** critical
- **Story Points:** 8
- **Acceptance:**
  - Harness runs on Bun
  - All scenarios execute
  - Performance metrics collected
  - Results compared to Node baseline

**BUN-S3-T2: Test Layout Commit Timings**
- **Type:** test
- **Priority:** high
- **Story Points:** 5
- **Acceptance:**
  - Layout commits complete within expected timeframes
  - No timing drift or jitter
  - Performance matches or exceeds Node
  - Metrics documented

**BUN-S3-T3: Test NVX1 Score Graph Execution**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - Score graphs execute correctly
  - Parsing accuracy maintained
  - Rendering quality unchanged
  - Playback timing accurate (mocked)

**BUN-S3-T4: Test Apollo Chord Dispatch**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - Chord dispatch works (mocked)
  - Audio routing functional (mocked)
  - Timing maintained
  - Quantum Rails integration intact (mocked)

**BUN-S3-T5: Test Audio Service Queue**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - Queue operations function (mocked)
  - Priority handling works
  - Error recovery functional
  - No audio glitches (mocked environment)

**BUN-S3-T6: Test Fretboard Widget Commit Lifecycle**
- **Type:** test
- **Priority:** high
- **Story Points:** 5
- **Acceptance:**
  - Widget renders correctly (mocked GPU)
  - Commit lifecycle functions
  - WebGPU integration mocked
  - WASM loading successful

**BUN-S3-T7: Document Compatibility Gaps**
- **Type:** documentation
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - All gaps documented
  - Workarounds implemented
  - Upstream issues filed
  - Migration guide updated

**BUN-S3-T8: WebGPU/Three.js Shader Validation Test**
- **Type:** test
- **Priority:** high
- **Story Points:** 5
- **Description:** Validate shader compilation, WASM memory stress test (15MB → 60MB), GPU fallback path
- **Acceptance:**
  - Shader compilation validated
  - Large WASM stress test passes
  - GPU fallback to CPU works
  - Memory usage documented

**BUN-S3-T9: GC Stress Test for WebGPU Renderer**
- **Type:** test
- **Priority:** medium
- **Story Points:** 3
- **Description:** Test Bun's GC behavior under large WASM loads, detect memory leaks
- **Acceptance:**
  - GC stress test passes
  - No memory leaks detected
  - Performance stable under load
  - Metrics documented

**BUN-S3-T10: Dynamic Import Consistency Audit**
- **Type:** test
- **Priority:** medium
- **Story Points:** 3
- **Description:** Verify ESM resolver differences in dynamic imports, test `import()` behavior
- **Acceptance:**
  - Dynamic imports work identically
  - ESM resolver consistent
  - No path resolution issues
  - Test coverage added

---

## Sprint 4: Vite/Rollup Pipeline Migration

**Sprint ID:** `BUN-S4`  
**Duration:** 1-2 weeks  
**Objective:** Migrate build pipeline to Bun-compatible mode

### Tasks

**BUN-S4-T1: Test Vite + Bun Integration**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Description:** Run Vite dev server with Bun, verify HMR works, test for known HMR websocket issues
- **Acceptance:**
  - Vite runs with Bun
  - HMR functional (or workaround)
  - Performance improvement measured
  - No regressions

**BUN-S4-T1.6: HMR Memory Leak Detector**
- **Type:** test
- **Priority:** high
- **Story Points:** 3
- **Description:** Add memory leak detection for HMR, monitor WASM reload behavior
- **Acceptance:**
  - Memory leak detector added
  - WASM reload monitored
  - No leaks detected
  - Metrics documented

**BUN-S4-T2: Verify WebGPU Polyfills Compile**
- **Type:** test
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - WebGPU code compiles
  - Shaders load correctly
  - WASM integration works
  - No compilation errors

**BUN-S4-T2.5: React Refresh Equivalence Test**
- **Type:** test
- **Priority:** high
- **Story Points:** 5
- **Description:** Verify React Fast Refresh behavior matches Vite, test component state preservation
- **Acceptance:**
  - React Refresh works identically
  - Component state preserved
  - No refresh regressions
  - Test coverage added

**BUN-S4-T3: Verify WASM Bundling**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - WASM files bundle correctly
  - Large files (15MB+) handled
  - MIME types correct (`application/wasm`)
  - wasm-pack integration works

**BUN-S4-T3.1: wasm-bindgen Glue Compatibility Audit**
- **Type:** test
- **Priority:** high
- **Story Points:** 3
- **Description:** Verify wasm-bindgen glue code works with Bun bundler, test memory management
- **Acceptance:**
  - wasm-bindgen glue compatible
  - Memory management correct
  - No binding errors
  - Test coverage added

**BUN-S4-T3.2: Large-WASM Streaming Benchmark**
- **Type:** test
- **Priority:** medium
- **Story Points:** 3
- **Description:** Benchmark WASM streaming performance (15MB → 60MB), test MIME type handling
- **Acceptance:**
  - Streaming benchmark passes
  - Large files handled efficiently
  - MIME types correct
  - Performance metrics documented

**BUN-S4-T4: Verify AudioWorklet Bundling**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Description:** Test AudioWorklet file bundling (browser-only), verify worklet files copied to dist, test loading
- **Acceptance:**
  - AudioWorklet files bundle correctly
  - Files copied to `dist/assets`
  - Browser loading works
  - No runtime errors

**BUN-S4-T4.5: AudioWorklet Loader Regression Snapshots**
- **Type:** test
- **Priority:** high
- **Story Points:** 3
- **Description:** Create regression snapshots for AudioWorklet loader, verify `addModule()` succeeds in Bun-served environment
- **Acceptance:**
  - Regression snapshots created
  - `addModule()` succeeds
  - Loader paths correct
  - Test coverage added

**BUN-S4-T5: Evaluate Bun Native Bundler (Spike)**
- **Type:** spike
- **Priority:** medium
- **Story Points:** 8
- **Acceptance:**
  - Experimental build created
  - Output compared to Vite
  - Performance measured
  - Gaps documented
  - Decision: Vite or Bun bundler

**BUN-S4-T6: Update Build Scripts**
- **Type:** chore
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - Build scripts use Bun
  - Node fallback available
  - CI builds successfully
  - Build time improved

**BUN-S4-T7: TypeScript Transpilation Performance Test**
- **Type:** test
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - Transpilation 4-8× faster
  - Incremental compilation works
  - Type checking uses tsc
  - Performance metrics documented

---

## Sprint 5: CI/CD Migration

**Sprint ID:** `BUN-S5`  
**Duration:** 1 week  
**Objective:** Migrate all CI/CD pipelines to use Bun

### Tasks

**BUN-S5-T1: Update GitHub Actions Workflows**
- **Type:** ci/cd
- **Priority:** critical
- **Story Points:** 8
- **Description:** Update all 43 workflows to use `oven-sh/setup-bun@v1`, update commands to use `bun`
- **Acceptance:**
  - All workflows updated
  - Bun installed correctly
  - Commands use Bun
  - Workflows pass
  - CI time reduced

**BUN-S5-T2: Update Caching Strategy**
- **Type:** ci/cd
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - Cache uses `~/.bun`
  - Cache keys correct
  - Hit rate maintained
  - Install time improved

**BUN-S5-T3: Update Docker Images**
- **Type:** ci/cd
- **Priority:** medium
- **Story Points:** 5
- **Description:** Update base images to include Bun, ensure Rust toolchain available for WASM builds
- **Acceptance:**
  - Docker images updated
  - Bun available in containers
  - Rust toolchain maintained
  - Image size optimized

**BUN-S5-T4: Update Deployment Pipelines**
- **Type:** ci/cd
- **Priority:** high
- **Story Points:** 3
- **Acceptance:**
  - Deployment uses Bun
  - Production builds successful
  - Deployment tested
  - No regressions

**BUN-S5-T5: Maintain Playwright Node Requirement**
- **Type:** ci/cd
- **Priority:** medium
- **Story Points:** 2
- **Description:** Ensure Node.js available for Playwright E2E tests (install Node alongside Bun or use Node image with Bun)
- **Acceptance:**
  - Node available for Playwright
  - E2E tests run successfully
  - Both runtimes coexist
  - Documentation updated

**BUN-S5-T6: Performance Monitoring in CI**
- **Type:** ci/cd
- **Priority:** medium
- **Story Points:** 3
- **Acceptance:**
  - Metrics collected
  - Performance tracked
  - Reports generated
  - Improvements documented

**BUN-S5-T7: Dual-Runtime CI Template**
- **Type:** ci/cd
- **Priority:** high
- **Story Points:** 5
- **Description:** Create CI template supporting both Node and Bun, with fallback for audio tests
- **Acceptance:**
  - Dual-runtime template created
  - Fallback for audio tests
  - Both runtimes tested
  - Template documented

**BUN-S5-T8: Docker Acceptance Test**
- **Type:** test
- **Priority:** medium
- **Story Points:** 5
- **Description:** Test Docker image running NVX1 + WebGPU headlessly, verify all systems work
- **Acceptance:**
  - Docker test passes
  - NVX1 works in container
  - WebGPU mocked correctly
  - All systems functional

---

## Sprint 6: Final Node → Bun Flip & Validation

**Sprint ID:** `BUN-S6`  
**Duration:** 1-2 weeks  
**Objective:** Complete migration, remove Node.js dependency

### Tasks

**BUN-S6-T1: Replace All Scripts with Bun**
- **Type:** refactor
- **Priority:** critical
- **Story Points:** 5
- **Acceptance:**
  - All 126 scripts use Bun
  - No Node-specific scripts (except where needed)
  - Documentation updated
  - Scripts execute successfully

**BUN-S6-T2: Remove Node from Dev Dependencies**
- **Type:** chore
- **Priority:** high
- **Story Points:** 2
- **Acceptance:**
  - Node version spec removed
  - Unnecessary deps removed
  - package.json cleaned
  - Dependencies validated

**BUN-S6-T3: Remove pnpm-lock.yaml**
- **Type:** chore
- **Priority:** medium
- **Story Points:** 1
- **Acceptance:**
  - pnpm-lock.yaml removed
  - bun.lock is authoritative
  - No lockfile conflicts
  - Installation works from clean state

**BUN-S6-T4: Full System Re-verify with Savage³**
- **Type:** test
- **Priority:** critical
- **Story Points:** 8
- **Acceptance:**
  - All harness tests pass
  - No regressions
  - Performance maintained/improved
  - System fully functional

**BUN-S6-T5: E2E Test Validation**
- **Type:** test
- **Priority:** critical
- **Story Points:** 5
- **Description:** Run full Playwright E2E suite against Bun-served app, verify user flows, check behavioral differences
- **Acceptance:**
  - All E2E tests pass
  - User flows functional
  - No behavioral differences
  - Performance acceptable

**BUN-S6-T6: Real-Browser Playwright NVX1 Test**
- **Type:** test
- **Priority:** high
- **Story Points:** 5
- **Description:** Add real-browser Playwright test for NVX1 micro-playback, verify audio timing in actual browser
- **Acceptance:**
  - Real-browser test passes
  - Audio timing verified
  - NVX1 playback works
  - Test coverage added

**BUN-S6-T7: Performance Benchmark Report**
- **Type:** documentation
- **Priority:** high
- **Story Points:** 5
- **Acceptance:**
  - Baseline metrics documented
  - Final metrics documented
  - Improvements quantified
  - Report published

**BUN-S6-T8: Create Rollback Procedure**
- **Type:** documentation
- **Priority:** critical
- **Story Points:** 3
- **Acceptance:**
  - Rollback procedure documented
  - Rollback script created
  - Both lockfiles preserved (during transition)
  - Procedure tested

**BUN-S6-T9: Add Environment Variable Lock**
- **Type:** configuration
- **Priority:** high
- **Story Points:** 2
- **Description:** Add `NODE_ONLY` or `BUN_ONLY` mode with validation checks to prevent mixed environments
- **Acceptance:**
  - Environment lock added
  - Validation checks work
  - Mixed environment prevented
  - Documentation updated

**BUN-S6-T10: Pin Bun Version**
- **Type:** configuration
- **Priority:** high
- **Story Points:** 2
- **Description:** Pin Bun version: `Bun >= 1.1.0 < 1.2.0` to prevent breaking changes
- **Acceptance:**
  - Bun version pinned
  - Version check added
  - CI validates version
  - Documentation updated

**BUN-S6-T11: Team Training & Documentation**
- **Type:** documentation
- **Priority:** high
- **Story Points:** 5
- **Acceptance:**
  - Migration guide complete
  - README updated
  - Development guide created
  - Team trained
  - Migration-aware onboarding guide created

**BUN-S6-T12: Final Validation & Sign-off**
- **Type:** validation
- **Priority:** critical
- **Story Points:** 3
- **Acceptance:**
  - All validation criteria met
  - Chief sign-off obtained
  - Epic marked complete
  - Progress updated

---

## Oracle Mode: Predicted Failures & Mitigations

### Top 10 Predicted Failures

| # | Failure | Root Cause | Where | Fix |
|---|---------|------------|-------|-----|
| 1 | NVX1 cursor freeze | Missing AudioContext | Bun test runner | MockKhronosClock (BUN-S1-T6) |
| 2 | Apollo `undefined playNote()` | No real audio graph | Runtime bridge | Interface abstraction (BUN-S1-T6) |
| 3 | Tone.Transport drift | Polyfill mismatch | Scheduling logs | Replace Tone timing with Khronos |
| 4 | Renderer init panic | Missing GPU device | WASM init | Conditional GPU init (BUN-S1-T7) |
| 5 | Supabase reconnect storms | Bun WS timing | Logs: reconnect loop | Retry caps (BUN-S3-T7) |
| 6 | Worklet load failure | Bun bundle path | Network errors | Copy module to static assets (BUN-S4-T4) |
| 7 | MockAudioContext inconsistent time | No monotonic clock | Audio tests | Simulated high-res timer (BUN-S1-T6) |
| 8 | Test flakiness | Bun's GC/timers | Vitest → Bun test | Deterministic mocks (BUN-S2-T2) |
| 9 | Vite-Bun plugin ordering break | Plugin incompat | Build | Plugin audit (BUN-S4-T1) |
| 10 | Cross-env vars missing | Bun.env loader | CI | `.env` loader shim (BUN-S5-T1) |

### Additional Mitigations

- **Lockfile Validation:** Automated CI check: `pnpm-lock.yaml === bun.lock` dependency tree
- **Path Protection:** `.cursorrules` invariant prevents Phoenix/SEB contamination
- **Version Pinning:** Bun >= 1.1.0 < 1.2.0
- **Environment Lock:** `NODE_ONLY` or `BUN_ONLY` mode with validation
- **Continuous Stress Harness:** CI detects timing regression (BUN-S3-T9)

---

## Critical Constraints

### Timing Constraints
- ❌ **CANNOT START:** Phoenix V1 is FROZEN (zero runtime changes)
- ❌ **CANNOT START:** SEB AAA Waves 1-2 just passed
- ✅ **MUST START AFTER:** Phoenix V1 Certification (R15)
- ✅ **MUST COMPLETE BEFORE:** SEB AAA Wave 3

### Technical Constraints
- **AudioWorklet:** Bun doesn't support in runtime (browser-only) - dev server bundling unaffected
- **WebGPU:** Bun doesn't support (browser-only) - must mock in tests
- **Native Modules:** Audit required, alternatives identified
- **Playwright:** May need Node alongside Bun in CI

### Risk Mitigation
- **Parallel Toolchain:** Maintain Node scripts during transition
- **Rollback Plan:** Preserve pnpm-lock.yaml during transition, document rollback procedure
- **Comprehensive Testing:** Savage³ harness validates all critical systems
- **Gradual Migration:** Test → Dev → CI → Production sequence

---

## Success Metrics

### Performance Targets
- ✅ HMR: 20-40× faster (<50ms vs ~1-2s)
- ✅ TS Transpile: 4-8× faster
- ✅ Test Execution: 2-5× faster (~3s vs ~8-10s)
- ✅ Install: ~15× faster (<5s vs ~45s)
- ✅ Dev Startup: 3× faster (<1s vs ~3s)

### Quality Targets
- ✅ 100% test pass rate (zero regressions)
- ✅ All systems functional (audio/GPU mocked appropriately)
- ✅ Zero production issues
- ✅ Team trained and documentation complete

---

## Epic Completion Criteria

1. ✅ All 6 sprints completed
2. ✅ All tasks marked done
3. ✅ Performance targets met
4. ✅ Zero regressions in Savage³ harness
5. ✅ E2E tests pass
6. ✅ CI/CD fully migrated
7. ✅ Documentation complete
8. ✅ Team trained
9. ✅ Chief sign-off obtained
10. ✅ Epic marked complete in master-progress.json

---

**Plan Version:** 2.0.0  
**Last Updated:** 2025-12-09  
**Status:** ✅ Complete - Ready for Execution (Post-R15)




























