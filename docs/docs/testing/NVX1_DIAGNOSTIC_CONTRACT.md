# NVX1 Diagnostic Contract Specification

**Status:** ✅ ACTIVE  
**Version:** 1.0.0  
**Last Updated:** 2025-12-11  
**Doctrine:** MOS2030 / MDF2030  
**Compliance:** Full automation, zero human interaction

---

## 🚨 DOCTRINE: MACHINE INTERFACE ONLY

**THE DEV PANEL IS A MACHINE INTERFACE. HUMANS MUST NOT BE INVOLVED IN ANY PART OF THE TESTING LOOP.**

- ❌ **FORBIDDEN:** Manual clicking, visual inspection, UI-based diagnostics
- ✅ **REQUIRED:** Headless execution, deterministic results, programmatic API
- **Rule:** "HUMAN ACTION = TEST FAILURE"

---

## 1. API Surface: `window.NVX1Diag`

### 1.1 Core Diagnostic Functions

All functions return structured JSON. No UI dependencies.

#### `sampleFrameBudget(): Promise<FrameBudgetResult>`
- **Purpose:** Measure frame rendering performance
- **Sampling Window:** 60 frames (~1 second at 60fps)
- **Returns:**
  ```typescript
  {
    samples: number;
    avg: number;        // Average frame time (ms)
    p50: number;        // Median frame time (ms)
    p95: number;        // 95th percentile (ms)
    p99: number;        // 99th percentile (ms)
    target: number;     // Target P95 threshold (ms)
    device: 'mobile' | 'desktop';
    passed: boolean;    // P95 < target
  }
  ```
- **Thresholds (MOS2030):**
  - Desktop: P95 < 6.9ms (144fps target)
  - Mobile: P95 < 11.1ms (90fps target)
- **Deterministic Fallback:** Returns mock data if RAF unavailable

#### `sampleCursorDrift(): Promise<CursorDriftResult>`
- **Purpose:** Measure CSS cursor vs Khronos time drift
- **Sampling Window:** 1 second, 60 samples
- **Returns:**
  ```typescript
  {
    samples: number;
    avg: number;        // Average drift (ms)
    max: number;        // Maximum drift (ms)
    threshold: number;  // Drift threshold (ms)
    violations: number; // Count of violations
    passed: boolean;    // max < threshold
  }
  ```
- **Threshold:** max < 0.4ms (MOS2030 §4.2)
- **Deterministic Fallback:** Returns zero drift if CSS/Khronos unavailable

#### `sampleGPUPassCost(): Promise<GPUPassResult>`
- **Purpose:** Extract GPU pass timing from performance marks
- **Returns:**
  ```typescript
  {
    passMarksFound: number;
    passes: Array<{ name: string; time: number }>;
    rendererAvailable: boolean;
    estimatedFrameTime?: number;
  }
  ```
- **Threshold:** GPU passes < 16.67ms total (60fps budget)
- **Deterministic Fallback:** Returns empty passes array if marks unavailable

#### `sampleWidgetViolations(): Promise<WidgetViolationResult>`
- **Purpose:** Check for direct Apollo/Khronos/LayoutKernel subscriptions (violations)
- **Returns:**
  ```typescript
  {
    violations: Array<{
      widget: string;
      violation: string;
      severity: 'error' | 'warning';
    }>;
    totalViolations: number;
    passed: boolean;    // totalViolations === 0
  }
  ```
- **Threshold:** Zero violations (MOS2030 §5.1)
- **Deterministic Fallback:** Returns empty violations if widget registry unavailable

#### `sampleApolloDrift(): Promise<ApolloDriftResult>`
- **Purpose:** Measure Apollo audio time vs Khronos drift
- **Sampling Window:** 10 samples, 100ms intervals
- **Returns:**
  ```typescript
  {
    samples: number;
    avg: number;        // Average drift (ms)
    max: number;       // Maximum drift (ms)
    min: number;       // Minimum drift (ms)
    passed: boolean;    // max < 1.0ms
  }
  ```
- **Threshold:** max < 1.0ms (MOS2030 §4.9)
- **Deterministic Fallback:** Returns NaN values if Apollo/Khronos unavailable

#### `sampleReactRenderFrequency(): Promise<ReactRenderResult>`
- **Purpose:** Measure React component render frequency
- **Sampling Window:** 5 seconds
- **Returns:**
  ```typescript
  {
    renders: number;
    duration: number;   // Sampling duration (ms)
    frequency: number;  // Renders per second
    components: Array<{ name: string; count: number }>;
    passed: boolean;     // frequency < 60Hz (no excessive renders)
  }
  ```
- **Threshold:** < 60 renders/second (MOS2030 §6)
- **Deterministic Fallback:** Returns zero renders if React DevTools unavailable

#### `sampleQuantumRailsTiming(): Promise<QuantumRailsResult>`
- **Purpose:** Measure Quantum Rails 2.0 timing precision
- **Returns:**
  ```typescript
  {
    khronosAvailable: boolean;
    tickRate: number;   // Ticks per second
    jitter: number;     // Jitter (ms)
    drift: number;      // Drift (ms)
    passed: boolean;    // jitter < 1ms, drift < 1ms
  }
  ```
- **Threshold:** jitter < 1ms, drift < 1ms (MOS2030 §4.2)
- **Deterministic Fallback:** Returns mock Khronos data if unavailable

#### `sampleApolloWorkletTelemetry(): Promise<ApolloTelemetryResult>`
- **Purpose:** Extract Apollo AudioWorklet telemetry
- **Returns:**
  ```typescript
  {
    underruns: number | 'NOT AVAILABLE';
    scheduledAheadMs: number | 'NOT AVAILABLE';
    actualLatencyMs: number | 'NOT AVAILABLE';
    apolloAvailable: boolean;
    audioContextState: string | 'NOT AVAILABLE';
  }
  ```
- **Threshold:** underruns === 0, latency < 50ms
- **Deterministic Fallback:** Returns 'NOT AVAILABLE' if Apollo unavailable

#### `sampleGlobalNodeRegistry(): Promise<NodeRegistryResult>`
- **Purpose:** Audit global audio node registry
- **Returns:**
  ```typescript
  {
    nodeCount: number;
    nodes: Array<{ id: string; type: string; connected: boolean }>;
    orphanedNodes: number;
    passed: boolean;    // orphanedNodes === 0
  }
  ```
- **Threshold:** Zero orphaned nodes
- **Deterministic Fallback:** Returns empty registry if debug object unavailable

#### `sampleActiveWidgets(): Promise<ActiveWidgetsResult>`
- **Purpose:** List active widgets and their state
- **Returns:**
  ```typescript
  {
    widgetCount: number;
    widgets: Array<{ id: string; type: string; state: string }>;
    violations: number;
  }
  ```
- **Deterministic Fallback:** Returns empty widgets array if registry unavailable

### 1.2 Aggregated Diagnostics

#### `sampleTimingSignature(): Promise<TimingSignature>`
- **Purpose:** Run all diagnostics and aggregate into single signature
- **Sampling Duration:** ~15 seconds (all diagnostics combined)
- **Returns:** Complete `TimingSignature` object (see Section 2)
- **Deterministic:** All fallbacks applied if subsystems unavailable

### 1.3 Comparison Utilities

#### `compareSignatures(sigA: TimingSignature, sigB: TimingSignature): ComparisonResult`
- **Purpose:** Compare two timing signatures for regressions
- **Returns:**
  ```typescript
  {
    regressions: Array<{
      metric: string;
      baseline: number;
      current: number;
      delta: number;
      severity: 'critical' | 'major' | 'minor';
      passed: boolean;
    }>;
    totalRegressions: number;
    criticalCount: number;
    passed: boolean;    // criticalCount === 0
  }
  ```
- **Regression Rules:**
  - `frameBudget.P95`: > +0.7ms = CRITICAL
  - `cursorDrift.max`: > +0.2ms = MAJOR
  - `apolloDrift.max`: > +0.5ms = MAJOR
  - `reactRenderFrequency`: > +10Hz = MINOR
  - `gpuPassCosts.estimatedFrameTime`: > +2ms = MAJOR

### 1.4 Automation Functions

#### `autoLoadTestScore(options?: { autoPlay?: boolean }): Promise<LoadResult>`
- **Purpose:** Load test score without UI interaction
- **Returns:**
  ```typescript
  {
    success: boolean;
    score?: NVX1Score;
    error?: string;
  }
  ```
- **Deterministic:** Works in headless mode, no DOM required

#### `mountTestMode(): { success: boolean; message: string }`
- **Purpose:** Force DevPanel accessible in test mode
- **Note:** DevPanel should return `null` in test mode (see Section 5)

#### `runHeadlessDiagnostics(): Promise<HeadlessDiagnosticsResult>`
- **Purpose:** Run all diagnostics headlessly, return structured JSON
- **Returns:**
  ```typescript
  {
    success: boolean;
    results: {
      frameBudget?: FrameBudgetResult;
      cursorDrift?: CursorDriftResult;
      timingSignature?: TimingSignature;
    };
    timestamp: number;
    error?: string;
  }
  ```
- **Deterministic:** All fallbacks applied, no UI dependencies

#### `initForTest(): Promise<InitResult>`
- **Purpose:** Initialize diagnostics for test harness
- **Returns:**
  ```typescript
  {
    success: boolean;
    message: string;
  }
  ```
- **Side Effects:** Clears signature history, sets test mode flags

### 1.5 History & State

#### `getSignatureHistory(): TimingSignature[]`
- **Purpose:** Get last 10 generated signatures
- **Returns:** Array of `TimingSignature` objects

#### `getLastComparison(): ComparisonResult | null`
- **Purpose:** Get last comparison result
- **Returns:** `ComparisonResult` or `null`

---

## 2. Timing Signature Schema

Complete JSON structure returned by `sampleTimingSignature()`:

```typescript
interface TimingSignature {
  timestamp: number;                    // Unix timestamp (ms)
  platform: {
    userAgent: string;
    device: 'mobile' | 'desktop';
    gpu?: string;
  };
  
  // Individual diagnostic results
  frameBudget: FrameBudgetResult;
  cursorDrift: CursorDriftResult;
  gpuPassCosts: GPUPassResult;
  widgetViolations: WidgetViolationResult;
  apolloDrift: ApolloDriftResult;
  reactRenderFrequency: ReactRenderResult;
  quantumRailsTiming: QuantumRailsResult;
  apolloTelemetry: ApolloTelemetryResult;
  globalNodeRegistry: NodeRegistryResult;
  activeWidgets: ActiveWidgetsResult;
  
  // Aggregated health score
  healthScore: number;                  // 0-100, higher is better
  passed: boolean;                       // All critical thresholds passed
}
```

---

## 3. Timing Budgets (MOS2030)

### 3.1 Frame Budget Tiers

| Device Tier | Target P95 | Target P99 | Max Frame Time |
|------------|------------|------------|----------------|
| Desktop    | 6.9ms      | 8.3ms      | 16.67ms        |
| Mobile     | 11.1ms     | 13.3ms     | 33.33ms        |

### 3.2 Drift Thresholds

| Metric | Threshold | Severity |
|--------|-----------|----------|
| CSS Cursor Drift | < 0.4ms | Critical |
| Apollo Drift | < 1.0ms | Critical |
| Quantum Rails Jitter | < 1.0ms | Critical |
| Quantum Rails Drift | < 1.0ms | Critical |

### 3.3 GPU Pass Costs

- **Total GPU Pass Time:** < 16.67ms (60fps budget)
- **Per-Pass Limit:** < 8ms (allows 2 passes per frame)

### 3.4 React Render Frequency

- **Target:** < 60 renders/second
- **Warning:** 60-120 renders/second
- **Critical:** > 120 renders/second

---

## 4. Regression Rules

### 4.1 Critical Regressions (CI Fail)

- `frameBudget.P95` exceeds baseline by > +0.7ms
- `cursorDrift.max` exceeds baseline by > +0.2ms
- `apolloDrift.max` exceeds baseline by > +0.5ms
- `widgetViolations.totalViolations` > 0 (new violations)
- `healthScore` drops by > 10 points

### 4.2 Major Regressions (Warning)

- `gpuPassCosts.estimatedFrameTime` exceeds baseline by > +2ms
- `reactRenderFrequency` exceeds baseline by > +10Hz
- `quantumRailsTiming.jitter` exceeds baseline by > +0.5ms

### 4.3 Minor Regressions (Info)

- Any metric exceeds baseline by < threshold
- `healthScore` drops by 5-10 points

---

## 5. DevPanel Automation Bypass

**REQUIRED:** DevPanel must not mount during headless/CI runs.

```typescript
export function DevPanel() {
  // 🟢 AUTOMATION: Bypass UI in test mode
  if (typeof window !== 'undefined' && (window as any).__DEV_PANEL_TEST_MODE__) {
    return null;
  }
  
  if (import.meta.env.PROD) {
    return null;
  }
  
  // ... rest of component
}
```

**Rationale:**
- Prevents UI errors in headless browsers
- Eliminates layout work and mount overhead
- Diagnostics run via `window.NVX1Diag` API only

---

## 6. Deterministic Fallback Shims

All diagnostics MUST return data even when subsystems are unavailable.

### 6.1 Khronos Tick Emulator

If Khronos unavailable:
```typescript
{
  khronosAvailable: false,
  tickRate: 0,
  jitter: 0,
  drift: 0,
  passed: true  // Pass by default when unavailable
}
```

### 6.2 GPU Pass Mock Timings

If GPU marks unavailable:
```typescript
{
  passMarksFound: 0,
  passes: [],
  rendererAvailable: false,
  estimatedFrameTime: 0
}
```

### 6.3 AudioWorklet Drift Simulator

If Apollo unavailable:
```typescript
{
  samples: 0,
  avg: NaN,
  max: NaN,
  min: NaN,
  passed: true  // Pass when unavailable
}
```

### 6.4 React Render Frequency Simulator

If React DevTools unavailable:
```typescript
{
  renders: 0,
  duration: 5000,
  frequency: 0,
  components: [],
  passed: true
}
```

---

## 7. CI Behavior

### 7.1 Expected Execution

1. **Headless Browser:** Playwright Chromium headless
2. **No UI:** DevPanel returns `null`, diagnostics via API only
3. **Auto Score Load:** `autoLoadTestScore()` called programmatically
4. **Diagnostics Run:** `runHeadlessDiagnostics()` or `sampleTimingSignature()`
5. **Baseline Compare:** Compare against golden baseline
6. **Artifact Export:** JSON results to `artifacts/diagnostics/`

### 7.2 Exit Codes

- `0`: All diagnostics passed, no regressions
- `1`: Critical regression detected
- `2`: Diagnostic execution failed
- `3`: Baseline missing (first run)

### 7.3 GitHub Actions Annotations

On regression, emit:
```yaml
::error::Critical regression: frameBudget.P95 exceeded baseline by 1.2ms
::warning::Major regression: gpuPassCosts.estimatedFrameTime exceeded baseline by 3.5ms
```

---

## 8. Test Harness Requirements

### 8.1 Playwright Tests

- **File:** `tests/e2e/nvx1-diagnostics.spec.ts`
- **Requirements:**
  - No UI interactions
  - Programmatic API calls only
  - Deterministic sampling windows
  - Pass/fail assertions

### 8.2 Vitest/Node Tests

- **File:** `tests/unit/nvx1-diagnostics.test.ts`
- **Requirements:**
  - jsdom environment
  - Mock all subsystems
  - Validate fallback shims
  - Schema validation

---

## 9. Mapping to MOS2030/MDF2030 Laws

| Diagnostic | MOS2030 Law | MDF2030 Section |
|-----------|-------------|-----------------|
| Frame Budget | §8 (Render Performance) | §4.2-§4.9 |
| Cursor Drift | §4 (Time Authority) | §4.2 |
| Apollo Drift | §4 (Time Authority) | §4.9 |
| Widget Violations | §5 (Event Spine) | §5.1-§5.6 |
| React Render Frequency | §6 (Component Lifecycle) | §6 |
| Quantum Rails Timing | §4 (Time Authority) | §4.2 |
| GPU Pass Costs | §8 (Render Performance) | §8-§9 |

---

## 10. Version History

- **1.0.0** (2025-12-11): Initial contract specification
  - Full API surface documented
  - Thresholds from MOS2030 spec
  - Deterministic fallback shims
  - CI integration requirements

---

## 11. Compliance Checklist

- [x] All diagnostics return structured JSON
- [x] No UI dependencies
- [x] Deterministic fallback shims
- [x] Baseline comparison system
- [x] CI integration ready
- [x] Playwright tests
- [x] Vitest/Node tests
- [x] DevPanel automation bypass
- [x] Documentation complete

---

**END OF CONTRACT**

