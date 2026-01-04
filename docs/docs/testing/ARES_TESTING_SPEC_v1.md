# A.R.E.S. Testing Specification v1.0

**A.R.E.S. — Autonomous Runtime Evaluation System**

**Version:** 1.0.0  
**Date:** 2025-12-11  
**Status:** Active

---

## Executive Summary

A.R.E.S. is the unified testing infrastructure for MindSong Juke Hub, consolidating 774 test files, diagnostic scripts, SAVAGE³ stress tests, and governance validators into a single, modular, console-driven, DevPanel-embedded, CI-invokable testing system.

**Key Principles:**
- **Single Command Vocabulary:** `ARES.run('module')` / `pnpm ares module`
- **Zero Duplication:** All tests accessible via ARES
- **Modular Architecture:** 9 core modules
- **Self-Healing:** Automated diagnostics and recovery
- **Self-Forensic:** Complete runtime state capture

---

## Architecture Overview

### Core Components

1. **ARES Namespace** (`src/testing/ares/ARES.ts`)
   - Module registry
   - Execution engine
   - Result aggregation
   - Window exposure (`window.ARES`)

2. **ARES Modules** (`src/testing/ares/modules/`)
   - 9 specialized modules
   - Each module implements `ARESModule` interface
   - Lazy-loaded on demand

3. **ARES Runner** (`scripts/ares/runner.mjs`)
   - CLI entrypoint
   - Builds TypeScript on-demand
   - Executes modules
   - Formats output

4. **DevPanel Integration** (`src/components/dev/ARESPanel.tsx`)
   - Visual interface
   - Real-time results
   - Module status
   - Logs display

---

## Module Descriptions

### ARES.Core
- **Purpose:** Unit tests, governance, lint, TypeScript validation
- **Duration:** ~30 seconds
- **Consolidates:**
  - All `src/**/__tests__/` unit tests (271 files)
  - `tests/unit/` directory (50 files)
  - Governance validators (`scripts/luno/validate-*.mjs`)
  - Lint checks
  - TypeScript compilation

### ARES.Audio
- **Purpose:** Audio forensics, Apollo routing, RailRegistry validation
- **Duration:** ~10 seconds
- **Consolidates:**
  - `tests/audio/` (32 files)
  - `tests/e2e/*audio*` tests
  - `tests/savage3/audio-queue/` tests
  - Audio diagnostic scripts

### ARES.Runtime
- **Purpose:** In-runtime forensic agent
- **Duration:** ~5 seconds
- **Implementation:**
  - Wraps `window.NVX1_FORENSICS.run()`
  - Complete system diagnostics
  - Failure trace extraction

### ARES.SavageLite
- **Purpose:** Fast DevPanel instant checks (0.2-1.5s)
- **Duration:** ~1.5 seconds
- **Implementation:**
  - Uses `window.NVX1Diag` APIs
  - No browser reload
  - Quick pass/fail

### ARES.Savage3
- **Purpose:** Full browser harness (45-120s stress + drift)
- **Duration:** ~120 seconds
- **Consolidates:**
  - `tests/savage3/` (27 files)
  - Browser runner
  - Stress tests
  - Drift detection

### ARES.SavageLab
- **Purpose:** CI-only brutalizer
- **Duration:** ~5 minutes
- **Implementation:**
  - Extended stress tests
  - GPU memory pressure
  - Async starvation detection
  - Long-run drift tests
  - **Only runs in CI environment**

### ARES.Widgets
- **Purpose:** Widget subscription + EventSpine tests
- **Duration:** ~15 seconds
- **Consolidates:**
  - `tests/savage3/widgets/` tests
  - `tests/savage3/olympus/` widget tests
  - EventSpine integration tests

### ARES.Render
- **Purpose:** GPU/WASM/layout tests
- **Duration:** ~20 seconds
- **Consolidates:**
  - `tests/visual/` tests
  - `tests/visual-regression/` tests
  - `tests/e2e/*visual*` tests
  - GPU diagnostic tests

### ARES.Khronos
- **Purpose:** Timing engine tests
- **Duration:** ~15 seconds
- **Consolidates:**
  - `tests/khronos/` (5 files)
  - `tests/e2e/*timeline*` tests
  - `tests/audio/nvx1-timeline*` tests
  - Transport/scheduler tests

### ARES.Gov
- **Purpose:** Canonical governance validation
- **Duration:** ~5 seconds
- **Consolidates:**
  - `scripts/luno/validate-*.mjs` scripts
  - Epic ID validation
  - Canonical order validation
  - Story/task uniqueness validation

---

## Naming Conventions

### Module IDs
- Use kebab-case: `core`, `savage-lite`, `savage3`
- Match `ARES_MODULE_IDS` constants in `types.ts`

### Commands
- Console: `ARES.run('module-id')`
- CLI: `pnpm ares module-id`
- DevPanel: Button labels use module names

### Files
- Module files: `{ModuleName}Module.ts`
- Types: `types.ts`
- Core: `ARES.ts`
- Runner: `runner.mjs`

---

## Execution Commands

### Console (Browser DevTools)

```javascript
// Run single module
ARES.run('core')
ARES.run('audio')
ARES.run('runtime')

// Run multiple
ARES.runMultiple(['core', 'audio'])

// Run all
ARES.run('all')
ARES.runAll()

// Run critical only
ARES.run('critical')
ARES.runCritical()

// List modules
ARES.list()

// Get status
ARES.status('audio')
```

### CLI (Terminal)

```bash
# Run single module
pnpm ares core
pnpm ares audio
pnpm ares runtime

# Run all
pnpm ares all

# Run critical
pnpm ares critical

# List modules
pnpm ares list

# Get status
pnpm ares status audio
```

### DevPanel (UI)

- **RUN CRITICAL** button - Runs core, audio, khronos
- **RUN ALL MODULES** button - Runs all modules
- Individual module buttons - Run specific module
- Results display - Shows recent execution results
- Logs display - Shows execution logs

---

## Runner API

### ARES.run(moduleId, options?)

Execute a single ARES module.

**Parameters:**
- `moduleId: string` - Module identifier
- `options?: ARESOptions` - Execution options

**Returns:** `Promise<ARESResult>`

**Example:**
```typescript
const result = await ARES.run('audio', { verbose: true });
console.log(result.status); // 'pass' | 'fail' | 'error'
```

### ARES.runAll(options?)

Execute all available modules.

**Returns:** `Promise<ARESResult[]>`

### ARES.runCritical(options?)

Execute critical modules only (core, audio, khronos).

**Returns:** `Promise<ARESResult[]>`

### ARES.list()

List all available module IDs.

**Returns:** `string[]`

### ARES.status(moduleId)

Get module status.

**Returns:** `ARESModuleStatus | null`

---

## DevPanel Integration

### ARESPanel Component

Located at `src/components/dev/ARESPanel.tsx`.

**Features:**
- Module buttons
- Real-time execution status
- Results display
- Logs display
- Clear results button

### Integration Points

1. **DevPanel.tsx** - Imports and renders `ARESPanel`
2. **main.tsx** - Loads ARES in dev mode
3. **window.ARES** - Exposed globally for console access

---

## CI Integration

### PR Validation Workflow

**File:** `.github/workflows/ares-pr-validation.yml`

**Runs on:** Pull requests

**Modules:**
- `ARES.Core` (required)
- `ARES.Gov` (required)
- `ARES.Audio` (fast, optional)
- `ARES.Render` (fast, optional)

**Timeout:** 10 minutes

### Nightly Savage Lab Workflow

**File:** `.github/workflows/ares-savage-lab.yml`

**Runs on:** Schedule (nightly 2 AM UTC)

**Modules:**
- `ARES.Savage3` (full suite)
- `ARES.SavageLab` (CI-only brutalizer)
- `ARES.Widgets` (full widget suite)
- `ARES.Render` (full visual regression)
- `ARES.Khronos` (long-run drift tests)

**Timeout:** 60 minutes

**Artifacts:**
- Test results
- Screenshots
- Performance reports
- Drift analysis

---

## Telemetry Integration

### Telemetry IDs

All ARES modules publish telemetry with the following IDs:

- `ares.{module}.executions` - Execution count
- `ares.{module}.duration_ms` - Execution duration
- `ares.{module}.tests.passed` - Passed test count
- `ares.{module}.tests.failed` - Failed test count
- `ares.{module}.tests.total` - Total test count

### Integration Points

- Uses existing `AudioTelemetry` system
- Exposes to `window.__AUDIO_TELEMETRY__`
- DevPanel displays telemetry graphs

---

## Default Budgets

### Execution Time Budgets

- **ARES.Core:** 30 seconds
- **ARES.Audio:** 10 seconds
- **ARES.Runtime:** 5 seconds
- **ARES.SavageLite:** 1.5 seconds
- **ARES.Savage3:** 120 seconds
- **ARES.SavageLab:** 300 seconds
- **ARES.Widgets:** 15 seconds
- **ARES.Render:** 20 seconds
- **ARES.Khronos:** 15 seconds
- **ARES.Gov:** 5 seconds

### Performance Budgets

- **Frame Budget:** P95 < 6.9ms (desktop) / < 11.1ms (mobile)
- **CSS Cursor Drift:** < 0.4ms (Quantum Rails 2.0)
- **GPU Pass Cost:** Per-pass budgets defined in MOS2030 spec

---

## Example Failures

### Module Not Available

```json
{
  "moduleId": "runtime",
  "status": "error",
  "error": {
    "message": "NVX1_FORENSICS not available - agent not loaded",
    "code": "AGENT_NOT_LOADED"
  }
}
```

### Test Failures

```json
{
  "moduleId": "audio",
  "status": "fail",
  "tests": [
    {
      "name": "apollo",
      "status": "fail",
      "error": "Apollo not ready"
    }
  ]
}
```

### Timeout

```json
{
  "moduleId": "savage3",
  "status": "error",
  "error": {
    "message": "Module execution timeout",
    "code": "TIMEOUT"
  }
}
```

---

## Recovery and Escalation Flow

### Automatic Recovery

1. **Module Unavailable:** Skip with warning
2. **Test Failure:** Continue, report at end
3. **Timeout:** Abort, report timeout

### Manual Escalation

1. **Check Module Status:** `ARES.status('module-id')`
2. **Run Individual Module:** `ARES.run('module-id', { verbose: true })`
3. **Check Logs:** DevPanel logs or console output
4. **Review Diagnostics:** Module-specific diagnostic data

### CI Escalation

1. **PR Validation Fails:** Block merge, require fix
2. **Nightly Lab Fails:** Create issue, notify team
3. **Artifacts:** Review uploaded test results

---

## Compliance Table

| Requirement | Status | Notes |
|------------|--------|-------|
| Single command vocabulary | ✅ | `ARES.run()` / `pnpm ares` |
| Zero duplication | ✅ | All tests via ARES |
| DevPanel integration | ✅ | ARESPanel component |
| CI integration | ✅ | PR + Nightly workflows |
| Telemetry integration | ✅ | Uses AudioTelemetry |
| Documentation | ✅ | This spec + module reference |
| Backward compatibility | ✅ | Old tests still work during migration |
| Self-tests | ⚠️ | Planned (Phase 10) |

---

## Future Enhancements

### Phase 8: Migration
- Migrate all test files to ARES modules
- Consolidate scripts
- Remove deprecated files

### Phase 9: Telemetry
- Enhanced telemetry integration
- DevPanel telemetry graphs
- Performance dashboards

### Phase 10: Validation
- ARES self-tests
- Integration tests
- End-to-end validation

---

**END OF SPECIFICATION**
























