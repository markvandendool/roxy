# A.R.E.S. Module Reference

**Complete documentation for each ARES module**

---

## ARES.Core

**Module ID:** `core`  
**Name:** ARES.Core  
**Description:** Unit tests, governance, lint, TypeScript validation

### Purpose
Consolidates all unit tests, governance validators, lint checks, and TypeScript compilation into a single module.

### Consolidates
- All `src/**/__tests__/` unit tests (271 files)
- `tests/unit/` directory (50 files)
- Governance validators (`scripts/luno/validate-*.mjs`)
- ESLint checks
- TypeScript compilation checks

### Execution Time
- **Estimated:** ~30 seconds
- **Budget:** 30 seconds

### Dependencies
- `vitest` - Test runner
- `scripts/luno/validate-governance.mjs`
- `scripts/luno/validate-epic-ids.mjs`
- `scripts/luno/validate-luno-order.mjs`
- `scripts/luno/validate-story-task-uniqueness.mjs`

### Output Format
```json
{
  "moduleId": "core",
  "status": "pass",
  "tests": [
    { "name": "vitest", "status": "pass" },
    { "name": "governance:validate-governance.mjs", "status": "pass" },
    { "name": "lint", "status": "pass" },
    { "name": "typescript", "status": "pass" }
  ],
  "telemetry": {
    "counters": {
      "ares.core.tests.passed": 4,
      "ares.core.tests.failed": 0,
      "ares.core.tests.total": 4
    }
  }
}
```

### Failure Modes
- **Vitest failures:** Unit tests fail
- **Governance failures:** Epic IDs, canonical order, or story/task uniqueness violations
- **Lint failures:** ESLint errors
- **TypeScript failures:** Type errors

### Telemetry IDs
- `ares.core.tests.passed`
- `ares.core.tests.failed`
- `ares.core.tests.total`
- `ares.core.duration_ms`

---

## ARES.Audio

**Module ID:** `audio`  
**Name:** ARES.Audio  
**Description:** Audio forensics, Apollo routing, RailRegistry validation

### Purpose
Validates the complete audio pipeline: AudioContext → Apollo → Router → Backend → RailRegistry.

### Consolidates
- `tests/audio/` (32 files)
- `tests/e2e/*audio*` tests
- `tests/savage3/audio-queue/` tests
- Audio diagnostic scripts

### Execution Time
- **Estimated:** ~10 seconds
- **Budget:** 10 seconds

### Dependencies
- `window.audioRouter`
- `window.apollo` / `window.Apollo`
- `window.__audioPlaybackService`
- `window.railInstrumentRegistry`
- `window.GlobalAudioContext`

### Tests Performed
1. **AudioContext State:** Must be 'running'
2. **Apollo Readiness:** `apollo.isReady` must be true
3. **Router Backend:** Must be 'apollo-worklet' or 'nvx1'
4. **RailRegistry Backend:** Default backend must be 'apollo-worklet'
5. **AudioPlaybackService Readiness:** Strict readiness check
6. **SmartAudioRouter Initialization:** Must be initialized

### Output Format
```json
{
  "moduleId": "audio",
  "status": "pass",
  "tests": [
    { "name": "audioContext", "status": "pass", "data": { "state": "running" } },
    { "name": "apollo", "status": "pass", "data": { "isReady": true } },
    { "name": "routerBackend", "status": "pass", "data": { "backendName": "apollo-worklet" } }
  ],
  "diagnostics": {
    "audioContext": { "state": "running" },
    "apollo": { "isReady": true, "engineName": "apollo-worklet" },
    "router": { "isReady": true, "backendName": "apollo-worklet" }
  }
}
```

### Failure Modes
- **AudioContext suspended:** Context not running
- **Apollo not ready:** Apollo initialization failed
- **Wrong backend:** Router using incorrect backend
- **RailRegistry misconfigured:** Default backend incorrect
- **PlaybackService not ready:** Readiness gates failed

### Telemetry IDs
- `ares.audio.tests.passed`
- `ares.audio.tests.failed`
- `ares.audio.duration_ms`

---

## ARES.Runtime

**Module ID:** `runtime`  
**Name:** ARES.Runtime  
**Description:** In-runtime forensic agent

### Purpose
Wraps the existing NVX1_FORENSIC_AGENT for complete system diagnostics.

### Implementation
- Wraps `window.NVX1_FORENSICS.run()`
- Returns structured ARESResult
- Integrates with DevPanel

### Execution Time
- **Estimated:** ~5 seconds
- **Budget:** 5 seconds

### Dependencies
- `window.NVX1_FORENSICS` (from `public/diagnostics/NVX1_FORENSIC_AGENT.js`)

### Output Format
```json
{
  "moduleId": "runtime",
  "status": "pass",
  "diagnostics": {
    "primaryBreakpoint": null,
    "audioSnapshot": { /* ... */ },
    "failureTrace": []
  },
  "output": "# NVX1 Forensic Report\n\n...",
  "json": { /* Full forensic data */ }
}
```

### Failure Modes
- **Agent not loaded:** `NVX1_FORENSICS` not available
- **Forensic analysis failed:** Agent execution error

### Telemetry IDs
- `ares.runtime.executions`
- `ares.runtime.duration_ms`

---

## ARES.SavageLite

**Module ID:** `savage-lite`  
**Name:** ARES.SavageLite  
**Description:** Fast DevPanel instant checks (0.2-1.5s)

### Purpose
Ultra-fast diagnostics using DevPanel APIs - no browser reload required.

### Execution Time
- **Estimated:** ~1.5 seconds
- **Budget:** 1.5 seconds

### Dependencies
- `window.NVX1Diag` (DevPanel API)
- `window.GlobalAudioContext`
- `window.apollo`
- `window.audioRouter`
- `window.__AUDIO_TELEMETRY__`

### Tests Performed
1. **AudioContext State:** Quick check
2. **Apollo Readiness:** Quick check
3. **Router Backend:** Quick check
4. **Telemetry Snapshot:** Basic telemetry

### Output Format
```json
{
  "moduleId": "savage-lite",
  "status": "pass",
  "tests": [
    { "name": "audioContext", "status": "pass" },
    { "name": "apollo", "status": "pass" },
    { "name": "router", "status": "pass" },
    { "name": "telemetry", "status": "pass" }
  ]
}
```

### Failure Modes
- **DevPanel not loaded:** `NVX1Diag` unavailable
- **Quick checks fail:** Basic system state invalid

### Telemetry IDs
- `ares.savage-lite.tests.passed`
- `ares.savage-lite.tests.failed`
- `ares.savage-lite.duration_ms`

---

## ARES.Savage3

**Module ID:** `savage3`  
**Name:** ARES.Savage3  
**Description:** Full browser harness (45-120s stress + drift)

### Purpose
Full SAVAGE³ test suite - browser-based stress tests and drift detection.

### Consolidates
- `tests/savage3/` (27 files)
- Browser runner
- Audio queue stress tests
- Widget render tests
- Clock alignment tests

### Execution Time
- **Estimated:** ~120 seconds
- **Budget:** 120 seconds

### Dependencies
- Playwright (Node.js environment)
- Browser automation

### Commands
- `ARES.run('savage3')` - Full suite
- `ARES.run('savage3:fast')` - Quick subset (planned)
- `ARES.run('savage3:full')` - Complete with all stress tests (planned)

### Output Format
```json
{
  "moduleId": "savage3",
  "status": "pass",
  "tests": [ /* Playwright test results */ ],
  "summary": "SAVAGE³ test suite completed"
}
```

### Failure Modes
- **Playwright unavailable:** Not in Node.js environment
- **Test failures:** Stress tests fail
- **Drift detected:** Timing drift exceeds thresholds

### Telemetry IDs
- `ares.savage3.executions`
- `ares.savage3.duration_ms`

---

## ARES.SavageLab

**Module ID:** `savage-lab`  
**Name:** ARES.SavageLab  
**Description:** CI-only brutalizer

### Purpose
Extended stress tests that only run in CI environment.

### Execution Time
- **Estimated:** ~300 seconds (5 minutes)
- **Budget:** 300 seconds

### Dependencies
- CI environment (`CI=true`)
- Extended test infrastructure

### Tests Performed
- GPU memory pressure tests
- Async starvation detection
- Long-run drift tests
- Resource exhaustion tests

### Output Format
```json
{
  "moduleId": "savage-lab",
  "status": "pass",
  "summary": "SavageLab CI brutalizer execution"
}
```

### Failure Modes
- **Not in CI:** Skipped (not an error)
- **Stress test failures:** Resource exhaustion or drift

### Telemetry IDs
- `ares.savage-lab.executions`
- `ares.savage-lab.duration_ms`

---

## ARES.Widgets

**Module ID:** `widgets`  
**Name:** ARES.Widgets  
**Description:** Widget subscription + EventSpine tests

### Purpose
Validates widget architecture compliance with "Widgets are SLAVES" doctrine.

### Consolidates
- `tests/savage3/widgets/` tests
- `tests/savage3/olympus/` widget tests
- EventSpine integration tests

### Execution Time
- **Estimated:** ~15 seconds
- **Budget:** 15 seconds

### Dependencies
- `window.__eventSpine`
- `window.useEventSpine`
- `window.__widgetRegistry`

### Tests Performed (Planned)
- Widget → EventSpine hooks
- Widget → Khronos hooks
- "Widgets are SLAVES" doctrine validation
- Widget subscription patterns
- Widget unsubscription

### Output Format
```json
{
  "moduleId": "widgets",
  "status": "pass",
  "tests": [ /* Widget test results */ ]
}
```

### Failure Modes
- **Widget system unavailable:** APIs not loaded
- **Doctrine violations:** Widgets directly accessing Apollo/Khronos

### Telemetry IDs
- `ares.widgets.executions`
- `ares.widgets.duration_ms`

---

## ARES.Render

**Module ID:** `render`  
**Name:** ARES.Render  
**Description:** GPU/WASM/layout tests

### Purpose
Validates rendering pipeline: GPU passes, WASM boundaries, layout reflow.

### Consolidates
- `tests/visual/` tests
- `tests/visual-regression/` tests
- `tests/e2e/*visual*` tests
- GPU diagnostic tests
- WASM boundary tests

### Execution Time
- **Estimated:** ~20 seconds
- **Budget:** 20 seconds

### Dependencies
- `window.navigator.gpu` (WebGPU)
- `window.__renderer`
- `window.__webgpu`

### Tests Performed (Planned)
- GPU pass budget validation
- WASM copy/mutation rules
- Layout reflow tests
- Visual regression baselines
- Renderer budget compliance

### Output Format
```json
{
  "moduleId": "render",
  "status": "pass",
  "tests": [ /* Render test results */ ]
}
```

### Failure Modes
- **WebGPU unavailable:** No GPU support
- **Budget violations:** Render costs exceed budgets
- **Visual regressions:** Screenshot diffs detected

### Telemetry IDs
- `ares.render.executions`
- `ares.render.duration_ms`

---

## ARES.Khronos

**Module ID:** `khronos`  
**Name:** ARES.Khronos  
**Description:** Timing engine tests

### Purpose
Validates Khronos timing engine: TickHz, drift, cycle correctness.

### Consolidates
- `tests/khronos/` (5 files)
- `tests/e2e/*timeline*` tests
- `tests/audio/nvx1-timeline*` tests
- Transport/scheduler tests

### Execution Time
- **Estimated:** ~15 seconds
- **Budget:** 15 seconds

### Dependencies
- `window.__khronos` / `window.__KHRONOS__`
- `window.__KHRONOS_BUS__`
- `window.__KHRONOS_TICK_COUNT__`

### Tests Performed
1. **Khronos Engine State:** isPlaying, tempo, beatFloor, tickHz
2. **KhronosBus Subscription:** Bus availability
3. **Tick Count:** Tick counter tracking

### Tests Planned
- TickHz validation
- Drift detection
- Cycle correctness
- Beat-floor synchronization
- AudioWorklet integration
- KhronosStore validation

### Output Format
```json
{
  "moduleId": "khronos",
  "status": "pass",
  "tests": [
    { "name": "khronosState", "status": "pass" },
    { "name": "khronosBus", "status": "pass" },
    { "name": "tickCount", "status": "pass" }
  ],
  "diagnostics": {
    "khronos": { "isPlaying": false, "tempo": 120, "beatFloor": 0, "tickHz": 480 }
  }
}
```

### Failure Modes
- **Khronos unavailable:** Engine not loaded
- **Bus missing:** KhronosBus not available
- **Drift detected:** Timing drift exceeds thresholds

### Telemetry IDs
- `ares.khronos.tests.passed`
- `ares.khronos.tests.failed`
- `ares.khronos.duration_ms`

---

## ARES.Gov

**Module ID:** `gov`  
**Name:** ARES.Gov  
**Description:** Canonical governance validation

### Purpose
Validates LUNO governance: Epic IDs, canonical order, story/task uniqueness.

### Consolidates
- `scripts/luno/validate-governance.mjs`
- `scripts/luno/validate-epic-ids.mjs`
- `scripts/luno/validate-luno-order.mjs`
- `scripts/luno/validate-story-task-uniqueness.mjs`

### Execution Time
- **Estimated:** ~5 seconds
- **Budget:** 5 seconds

### Dependencies
- Governance validation scripts
- `public/releaseplan/master-progress.json`
- `docs/luno/LUNO_CANONICAL_ID_MAP.md`

### Tests Performed
1. **Governance Validation:** Protected files, Chief approval
2. **Epic ID Validation:** Unique IDs, canonical format
3. **LUNO Order Validation:** Canonical order compliance
4. **Story/Task Uniqueness:** No duplicate IDs

### Output Format
```json
{
  "moduleId": "gov",
  "status": "pass",
  "tests": [
    { "name": "governance", "status": "pass" },
    { "name": "epicIds", "status": "pass" },
    { "name": "lunoOrder", "status": "pass" },
    { "name": "storyTaskUniqueness", "status": "pass" }
  ]
}
```

### Failure Modes
- **Epic ID violations:** Duplicate or invalid IDs
- **Canonical order violations:** Epics out of order
- **Story/task duplicates:** Duplicate IDs detected

### Telemetry IDs
- `ares.gov.tests.passed`
- `ares.gov.tests.failed`
- `ares.gov.duration_ms`

---

**END OF MODULE REFERENCE**

























