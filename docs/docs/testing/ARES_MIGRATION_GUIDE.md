# A.R.E.S. Migration Guide

**How to migrate existing tests to ARES**

---

## Overview

This guide explains how to migrate existing tests, scripts, and diagnostic tools into the ARES unified testing infrastructure.

---

## Migration Strategy

### Phase 1: Create ARES Modules (Week 1-2)
- ✅ ARES modules created
- ✅ Old tests still work
- ✅ No file moves yet

### Phase 2: Update Tests to Use ARES APIs (Week 3-4)
- Update test files to use ARES modules
- Deprecate old commands (warnings)
- ARES commands work alongside old commands

### Phase 3: Remove Old Commands (Week 5-6)
- Old commands removed
- ARES-only
- Cleanup deprecated files

### Phase 4: Final Cleanup (Week 7+)
- Remove deprecated files
- Update documentation
- Performance optimization

---

## How to Migrate Existing Tests

### Unit Tests → ARES.Core

**Before:**
```bash
pnpm test
pnpm test:unit
```

**After:**
```bash
pnpm ares core
# or
ARES.run('core')
```

**Migration Steps:**
1. Tests remain in `src/**/__tests__/` or `tests/unit/`
2. No file moves required
3. ARES.Core wraps existing Vitest runner
4. Results aggregated into ARESResult format

### Audio Tests → ARES.Audio

**Before:**
```bash
pnpm test tests/audio/
pnpm test:e2e --grep audio
```

**After:**
```bash
pnpm ares audio
# or
ARES.run('audio')
```

**Migration Steps:**
1. Audio tests remain in `tests/audio/`
2. ARES.Audio module wraps existing tests
3. Adds runtime diagnostics (Apollo, Router, etc.)
4. Consolidates all audio-related tests

### Diagnostic Scripts → ARES.Runtime / ARES.SavageLite

**Before:**
```bash
node scripts/diagnostics/headless-diagnostics.mjs
window.NVX1_FORENSICS.run()
```

**After:**
```bash
pnpm ares runtime
pnpm ares savage-lite
# or
ARES.run('runtime')
ARES.run('savage-lite')
```

**Migration Steps:**
1. `NVX1_FORENSIC_AGENT.js` → ARES.Runtime (wraps existing)
2. Fast diagnostics → ARES.SavageLite
3. Scripts remain as implementation details
4. Exposed via ARES modules only

### SAVAGE³ Tests → ARES.Savage3

**Before:**
```bash
pnpm test tests/savage3/
playwright test tests/savage3/
```

**After:**
```bash
pnpm ares savage3
# or
ARES.run('savage3')
```

**Migration Steps:**
1. SAVAGE³ tests remain in `tests/savage3/`
2. ARES.Savage3 wraps Playwright execution
3. Adds ARES result formatting
4. Integrates with ARES.Runtime for diagnostics

### Governance Scripts → ARES.Gov

**Before:**
```bash
node scripts/luno/validate-governance.mjs
node scripts/luno/validate-epic-ids.mjs
```

**After:**
```bash
pnpm ares gov
# or
ARES.run('gov')
```

**Migration Steps:**
1. Governance scripts remain in `scripts/luno/`
2. ARES.Gov wraps all validation scripts
3. Returns unified ARESResult format
4. Integrates with CI workflows

---

## How to Add New Tests to ARES

### Option 1: Add to Existing Module

If your test fits an existing ARES module:

1. Add test file to appropriate directory
2. Module automatically picks it up (if using Vitest/Playwright)
3. No code changes needed

**Example:**
```typescript
// tests/audio/my-new-audio-test.spec.ts
// Automatically included in ARES.Audio
```

### Option 2: Create New Module

If you need a new ARES module:

1. Create `src/testing/ares/modules/NewModule.ts`
2. Implement `ARESModule` interface
3. Register in `src/testing/ares/ARES.ts`
4. Add to `ARES_MODULE_IDS` in `types.ts`
5. Add CLI command in `package.json`

**Example:**
```typescript
// src/testing/ares/modules/NewModule.ts
export const NewModule: ARESModule = {
  id: 'new-module',
  name: 'ARES.NewModule',
  description: 'New module description',
  async run(options) {
    // Implementation
  },
  // ...
};
```

---

## How to Create New ARES Modules

### Step 1: Create Module File

Create `src/testing/ares/modules/YourModule.ts`:

```typescript
import type { ARESModule, ARESOptions, ARESResult } from '../types';
import { ARES_MODULE_IDS } from '../types';

let lastResult: ARESResult | null = null;

export const YourModule: ARESModule = {
  id: ARES_MODULE_IDS.YOUR_MODULE, // Add to types.ts first
  name: 'ARES.YourModule',
  description: 'Your module description',
  estimatedDuration: 5000, // milliseconds

  isAvailable(): boolean {
    // Check if module can run
    return true;
  },

  getStatus() {
    return {
      moduleId: this.id,
      available: this.isAvailable(),
      running: false,
      lastResult,
      lastExecuted: lastResult?.timestamp,
    };
  },

  async run(options?: ARESOptions): Promise<ARESResult> {
    const startTime = Date.now();
    
    try {
      // Your test logic here
      
      const result: ARESResult = {
        moduleId: this.id,
        moduleName: this.name,
        status: 'pass',
        duration: Date.now() - startTime,
        timestamp: startTime,
        summary: 'Your module completed successfully',
        tests: [],
        telemetry: {
          counters: {
            'ares.your-module.executions': 1,
            'ares.your-module.duration_ms': Date.now() - startTime,
          },
        },
      };

      lastResult = result;
      return result;
    } catch (error) {
      // Error handling
      const result: ARESResult = {
        moduleId: this.id,
        moduleName: this.name,
        status: 'error',
        duration: Date.now() - startTime,
        timestamp: startTime,
        summary: `Module failed: ${error instanceof Error ? error.message : String(error)}`,
        error: {
          message: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        },
      };
      lastResult = result;
      return result;
    }
  },
};
```

### Step 2: Add Module ID

Add to `src/testing/ares/types.ts`:

```typescript
export const ARES_MODULE_IDS = {
  // ... existing modules
  YOUR_MODULE: 'your-module',
} as const;
```

### Step 3: Register Module

Add to `src/testing/ares/ARES.ts`:

```typescript
const { YourModule } = await import('./modules/YourModule');
modules.set(ARES_MODULE_IDS.YOUR_MODULE, YourModule);
```

### Step 4: Add CLI Command

Add to `package.json`:

```json
{
  "scripts": {
    "ares:your-module": "pnpm ares your-module"
  }
}
```

### Step 5: Export Module

Add to `src/testing/ares/modules/index.ts`:

```typescript
export { YourModule } from './YourModule';
```

---

## Deprecation Timeline

### Week 1-2: ARES Created
- ✅ ARES modules exist
- ✅ Old commands still work
- ✅ No breaking changes

### Week 3-4: Deprecation Warnings
- Old commands show deprecation warnings
- ARES commands work
- Both systems coexist

### Week 5-6: Old Commands Removed
- Old commands removed
- ARES-only
- Migration complete

### Week 7+: Cleanup
- Remove deprecated files
- Update all documentation
- Final optimizations

---

## Backward Compatibility

During migration, both old and new commands work:

**Old Commands (Still Work):**
```bash
pnpm test
pnpm test:integration
node scripts/luno/validate-governance.mjs
```

**New Commands (ARES):**
```bash
pnpm ares core
pnpm ares gov
ARES.run('core')
```

**Both produce same results** - ARES wraps existing infrastructure.

---

## Common Migration Issues

### Issue: Module Not Available

**Error:** `Module not found: your-module`

**Solution:**
1. Check module is registered in `ARES.ts`
2. Check module ID matches `ARES_MODULE_IDS`
3. Check module file exists and exports correctly

### Issue: Tests Not Running

**Error:** Tests not executing in ARES module

**Solution:**
1. Check module `isAvailable()` returns true
2. Check test files are in correct directories
3. Check module wraps test runner correctly

### Issue: Results Not Showing

**Error:** ARESResult not formatted correctly

**Solution:**
1. Check result matches `ARESResult` interface
2. Check `status` is valid ('pass' | 'fail' | 'error' | 'warning' | 'skipped')
3. Check telemetry IDs follow naming convention

---

## Best Practices

1. **Keep Tests in Original Locations:** Don't move test files during migration
2. **Wrap, Don't Replace:** ARES wraps existing infrastructure
3. **Incremental Migration:** Migrate one module at a time
4. **Test Both Systems:** Ensure old and new commands work during migration
5. **Document Changes:** Update docs as you migrate

---

## Examples

### Example 1: Migrating Unit Tests

**Before:**
```bash
# Run all unit tests
pnpm test
```

**After:**
```bash
# Same tests, via ARES
pnpm ares core
```

**No test file changes needed** - ARES.Core wraps existing Vitest runner.

### Example 2: Migrating Audio Diagnostics

**Before:**
```javascript
// Manual diagnostic
const apollo = window.apollo;
console.log('Apollo ready:', apollo?.isReady);
```

**After:**
```javascript
// Automated diagnostic via ARES
const result = await ARES.run('audio');
console.log('Apollo status:', result.diagnostics?.apollo);
```

### Example 3: Migrating Governance Scripts

**Before:**
```bash
# Run individual scripts
node scripts/luno/validate-governance.mjs
node scripts/luno/validate-epic-ids.mjs
```

**After:**
```bash
# Run all governance checks
pnpm ares gov
```

**Scripts remain** - ARES.Gov wraps and aggregates results.

---

**END OF MIGRATION GUIDE**
























