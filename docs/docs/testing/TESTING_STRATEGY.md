# Testing Strategy - MindSong Juke Hub

## 🎯 Vision & Goals

### Primary Objective
Establish a **comprehensive, automated testing infrastructure** that prevents regressions, validates critical functionality, and enables confident development at scale.

### Success Metrics
- **70%+ overall code coverage** (unit + integration)
- **90%+ coverage for critical services** (ChordDetection, MusicXML, TabArranger, UnifiedTransport)
- **Zero console errors** in E2E tests
- **All tests green before merge** (enforced via CI/CD)
- **< 5 minute total test runtime** (for fast feedback loops)

---

## 📋 Test Coverage Requirements

### Critical Path Services (90%+ Coverage Required)
1. **ChordDetectionService** ✅ (36/36 tests passing - 100%)
   - Real-time MIDI → chord detection
   - Zero lag requirement
   - Slash chord handling
   - ABC notation conversion

2. **UnifiedTransport Store** ✅ (23/25 tests passing - 92%)
   - KRONOS/HERMES synchronization
   - Play/pause/stop/restart
   - Tempo & volume control
   - Metronome toggle

3. **MusicXMLImportService** 🔄 (Pending)
   - MusicXML → NVX1Score conversion
   - Multi-instrument preservation
   - Metadata handling

4. **TabArranger** 🔄 (Pending)
   - String/finger inference
   - Voicing logic

5. **GlobalApollo** 🔄 (Pending)
   - Audio engine initialization
   - Instrument loading
   - Sample playback

### Standard Coverage (60%+ Coverage Required)
- UI Components (React)
- Utility functions
- Type definitions with runtime validation

### Exemptions (No Coverage Required)
- Type-only files (`*.d.ts`)
- Configuration files
- Build scripts
- Documentation

---

## 🏗️ Testing Architecture

### 4-Layer Testing Pyramid

```
         /\
        /  \  E2E Tests (10%)
       /____\
      /      \  Integration Tests (20%)
     /________\
    /          \  Unit Tests (70%)
   /__________  \
```

### Layer 1: Unit Tests (70% of tests)

**Purpose:** Test individual functions/classes in isolation.

**Framework:** Vitest + @testing-library/react

**What to Test:**
- Pure functions (chord detection, music theory calculations)
- Zustand stores (unifiedTransport, nvx1Store)
- Service classes (import/export, audio, chord extraction)
- Utility functions (note parsing, MIDI conversion)

**Example:**
```typescript
// ChordDetectionService.test.ts
describe('ChordDetectionService', () => {
  it('should detect C major from MIDI [60, 64, 67]', () => {
    const result = service.detectChord([60, 64, 67]);
    expect(result?.symbol).toContain('C');
    expect(result?.root).toBe('C');
  });
});
```

**Run:** `pnpm test:unit`

---

### Layer 2: Integration Tests (20% of tests)

**Purpose:** Test how multiple units work together.

**Framework:** Vitest + @testing-library/react

**What to Test:**
- Component + Store interactions
- Service + Service chains (e.g., MusicXML → TabArranger → Audio)
- OSMD integration (Orchestra Rail)
- Browser storage + Zustand persist

**Example:**
```typescript
// OrchestraRail.integration.test.tsx
describe('OrchestraRail Integration', () => {
  it('renders OSMD notation from MusicXML', async () => {
    const musicXML = '<score-partwise>...</score-partwise>';
    render(<OrchestraRail musicXML={musicXML} />);
    
    await waitFor(() => {
      expect(screen.getByTestId('osmd-container')).toBeInTheDocument();
    });
  });
});
```

**Run:** `pnpm test:integration`

---

### Layer 3: E2E Tests (10% of tests)

**Purpose:** Test complete user workflows in real browser.

**Framework:** Playwright

**What to Test:**
- NotaGen workflow (Rocky → MusicXML → Orchestra Rail)
- Score playback (play/pause/stop/restart)
- MIDI input → real-time chord detection
- File upload/import (MusicXML, Guitar Pro, MP3)
- Save/load score from profile

**Example:**
```typescript
// tests/e2e/notagen-workflow.spec.ts
test('NotaGen workflow: MusicXML → Orchestra Rail', async ({ page }) => {
  await page.goto('http://localhost:9135/nvx1-score');
  
  // Open Rocky
  await page.click('[data-testid="rocky-button"]');
  
  // Request score generation
  await page.fill('[data-testid="rocky-input"]', 'Create Hotel California');
  await page.click('[data-testid="rocky-send"]');
  
  // Wait for NotaGen task completion
  await page.waitForSelector('[data-testid="notagen-complete"]');
  
  // Verify Orchestra Rail visible with notes
  const osmdNotes = page.locator('.vf-note');
  await expect(osmdNotes.first()).toBeVisible();
});
```

**Run:** `pnpm test:e2e`

---

### Layer 4: Visual Regression Tests (Optional)

**Purpose:** Catch visual UI changes.

**Framework:** Playwright (screenshot comparison)

**What to Test:**
- Orchestra Rail rendering consistency
- Chord diagram layouts
- Score rail alignment

**Example:**
```typescript
test('Orchestra Rail visual regression', async ({ page }) => {
  await page.goto('http://localhost:9135/nvx1-score');
  await page.waitForSelector('[data-testid="orchestra-rail"]');
  
  await expect(page).toHaveScreenshot('orchestra-rail.png', {
    maxDiffPixels: 100,
  });
});
```

---

## 🚀 Running Tests

### Quick Commands

```bash
# All unit tests
pnpm test:unit

# Watch mode (TDD)
pnpm test:watch

# Coverage report
pnpm test:coverage

# Integration tests only
pnpm test:integration

# E2E tests (all browsers)
pnpm test:e2e

# E2E tests (with UI)
pnpm test:e2e:ui

# E2E tests (headed/visible browser)
pnpm test:e2e:headed

# All tests (unit + e2e)
pnpm test:all
```

### Pre-Commit Checklist

Before every commit:
```bash
# 1. Run all unit tests
pnpm test:unit

# 2. Check coverage
pnpm test:coverage

# 3. Lint
pnpm lint

# 4. Build (to catch type errors)
pnpm build
```

---

## 📊 CI/CD Pipeline

### GitHub Actions Workflow (`.github/workflows/test.yml`)

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: pnpm install
      
      - name: Run unit tests
        run: pnpm test:unit
      
      - name: Run integration tests
        run: pnpm test:integration
      
      - name: Generate coverage report
        run: pnpm test:coverage
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
      
      - name: Run E2E tests
        run: pnpm test:e2e
      
      - name: Build WASM (renderer-core)
        run: pnpm renderer:build:dev
      
      - name: Build app
        run: pnpm build
```

### Branch Protection Rules

**Require before merge:**
- ✅ All tests passing (unit + integration + e2e)
- ✅ Coverage >= 70%
- ✅ Lint passing
- ✅ Build succeeds

---

## 📝 Test Naming Conventions

### File Naming
- **Unit tests:** `*.test.ts` or `*.test.tsx`
- **Integration tests:** `*.integration.test.tsx`
- **E2E tests:** `*.spec.ts`

### Test Structure (AAA Pattern)
```typescript
describe('FeatureName', () => {
  describe('methodName()', () => {
    it('should [expected behavior] when [condition]', () => {
      // Arrange
      const input = setupTestData();
      
      // Act
      const result = service.method(input);
      
      // Assert
      expect(result).toBe(expected);
    });
  });
});
```

---

## 🛠️ Test Utilities

### Custom Render with Providers
```typescript
// src/test/utils.tsx
export function renderWithProviders(
  ui: ReactElement,
  { initialRoute = '/', ...options }: CustomRenderOptions = {}
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <BrowserRouter>{children}</BrowserRouter>;
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options }),
  };
}
```

### Mock Factories
```typescript
// src/test/utils.tsx
export function createMockNVX1Score(overrides = {}) {
  return {
    info: {
      title: 'Test Song',
      artist: 'Test Artist',
      ...overrides.info,
    },
    parts: [...],
    chordsInScore: {},
    ...overrides,
  };
}

export function createMockMusicXML(options = {}) {
  const { title = 'Test Song', composer = 'Test Composer', parts = 1 } = options;
  return `<?xml version="1.0"?>...`;
}
```

---

## 🚨 Critical Testing Rules

### RULE #1: No Feature Without Tests
Every new feature MUST include tests before being merged. This is **NON-NEGOTIABLE**.

**Minimum requirements:**
- ✅ Unit tests for core logic
- ✅ Integration test if multiple components interact
- ✅ E2E test if user-facing workflow

### RULE #2: Test Realistic Scenarios
Avoid testing implementation details. Test **behavior**, not **structure**.

❌ **BAD:**
```typescript
it('should call setState with correct argument', () => {
  const spy = vi.spyOn(component, 'setState');
  component.updateValue(5);
  expect(spy).toHaveBeenCalledWith({ value: 5 });
});
```

✅ **GOOD:**
```typescript
it('should update displayed value when user enters number', () => {
  const { getByRole } = render(<Component />);
  const input = getByRole('textbox');
  
  userEvent.type(input, '5');
  
  expect(screen.getByText('Value: 5')).toBeInTheDocument();
});
```

### RULE #3: Fast Tests Win
Tests should be **FAST**. If tests are slow, developers won't run them.

**Target:** < 5 minutes for full suite

**Optimization strategies:**
- Use `vi.mock()` to mock slow dependencies (network, file I/O)
- Run tests in parallel (`fullyParallel: true` in Playwright)
- Cache dependencies in CI/CD

### RULE #4: Flaky Tests = Broken Tests
If a test passes sometimes and fails sometimes, **fix it immediately** or delete it.

**Common causes of flakiness:**
- Race conditions (use `waitFor` in React Testing Library)
- Reliance on timing/delays (use deterministic waits)
- Shared state between tests (use `beforeEach` to reset)

---

## 🔧 Mocking Strategy

### When to Mock
- **External APIs** (NotaGen, Supabase, external services)
- **Browser APIs** (navigator, window.matchMedia, AudioContext)
- **Slow operations** (file uploads, large data processing)
- **Non-deterministic behavior** (Date.now(), Math.random())

### When NOT to Mock
- **Critical services** (ChordDetection, MusicXML import)
- **Zustand stores** (test the real thing)
- **UI components** (test real rendering)

### Mock Examples
```typescript
// Mock external API
vi.mock('@/services/notagen', () => ({
  generateScore: vi.fn(() => Promise.resolve(mockMusicXML)),
}));

// Mock audio context (doesn't exist in test env)
global.AudioContext = vi.fn(() => ({
  createOscillator: () => ({ connect: vi.fn(), start: vi.fn() }),
  destination: {},
}));

// Mock date for deterministic tests
vi.setSystemTime(new Date('2025-01-01'));
```

---

## 📚 Testing Best Practices

### 1. Test Edge Cases
- Empty arrays/strings
- Null/undefined values
- Very large/small numbers
- Invalid MIDI notes (< 0, > 127)
- Malformed MusicXML

### 2. Test Error Handling
```typescript
it('should throw error for invalid MIDI note', () => {
  expect(() => service.detectChord([-1, 256])).toThrow('Invalid MIDI');
});
```

### 3. Test Performance
```typescript
it('should detect chord in < 10ms (zero lag requirement)', () => {
  const startTime = performance.now();
  service.detectChord([60, 64, 67]);
  const duration = performance.now() - startTime;
  
  expect(duration).toBeLessThan(10);
});
```

### 4. Use Data-Driven Tests
```typescript
const testCases = [
  { midi: [60, 64, 67], expected: 'C' },
  { midi: [57, 60, 64], expected: 'Am' },
  { midi: [62, 65, 69, 72], expected: 'Dm7' },
];

testCases.forEach(({ midi, expected }) => {
  it(`should detect ${expected} from MIDI ${midi}`, () => {
    const result = service.detectChord(midi);
    expect(result?.symbol).toContain(expected);
  });
});
```

---

## 🎓 Onboarding for New Team Members

### Step 1: Run Tests Locally
```bash
# 1. Install dependencies
pnpm install

# 2. Run unit tests
pnpm test:unit

# 3. Watch a specific test file
pnpm test:watch src/services/ChordDetectionService.test.ts
```

### Step 2: Write Your First Test
- Pick a simple utility function
- Create `*.test.ts` file
- Write 3 tests (happy path, edge case, error case)
- Run `pnpm test:coverage` to see coverage increase

### Step 3: Run E2E Tests
```bash
# Install Playwright browsers (first time only)
npx playwright install

# Run E2E tests
pnpm test:e2e

# Open Playwright UI for debugging
pnpm test:e2e:ui
```

---

## 🐛 Debugging Tests

### Unit Test Debugging
```typescript
// Use .only to run single test
it.only('should detect C major', () => {
  // ...
});

// Add console.log for inspection
console.log('Result:', result);

// Use debugger
debugger; // Pause execution in VS Code debugger
```

### E2E Test Debugging
```bash
# Run in headed mode (see browser)
pnpm test:e2e:headed

# Run in debug mode (pause execution)
pnpm test:e2e:debug

# Run with trace (record all actions)
npx playwright test --trace on
```

---

## 📈 Current Test Status

### Summary (as of 2025-11-03)
- ✅ **Test Infrastructure:** Vitest, Playwright, coverage tools installed
- ✅ **ChordDetectionService:** 36/36 tests passing (100%)
- ✅ **UnifiedTransport Store:** 23/25 tests passing (92%)
- 🔄 **MusicXMLImportService:** Pending
- 🔄 **TabArranger:** Pending
- 🔄 **E2E Tests:** Pending
- 🔄 **CI/CD Pipeline:** Pending

### Next Steps
1. ✅ Write tests for MusicXMLImportService
2. ✅ Write tests for TabArranger
3. ✅ Create NotaGen workflow E2E test
4. ✅ Set up GitHub Actions CI/CD
5. ✅ Achieve 70%+ code coverage

---

## 🔗 References

- **Vitest Docs:** https://vitest.dev/
- **React Testing Library:** https://testing-library.com/react
- **Playwright Docs:** https://playwright.dev/
- **Testing Best Practices:** https://testingjavascript.com/

---

**Last Updated:** 2025-11-03  
**Maintained By:** Development Team





