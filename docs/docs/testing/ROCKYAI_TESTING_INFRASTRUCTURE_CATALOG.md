# RockyAI Testing Infrastructure Catalog

**Last Updated:** 2025-12-12  
**Purpose:** Complete inventory of all RockyAI testing infrastructure for forensic diagnostics and comprehensive test coverage planning.

---

## 📊 Executive Summary

**Total Test Files:** 30+  
**Test Types:** E2E (Playwright), Integration (Vitest), Unit (Vitest), Smoke (Node.js), Debug (Playwright)  
**Coverage Areas:** Chat, Score Generation, Harmonic Analysis, Theater Integration, Edge Functions, Service Layer, Widget Orchestration, Audio Coaching, Student Intelligence

---

## 🎯 Test Categories

### 1. E2E Tests (Playwright) - `tests/e2e/`

#### Core Functionality Tests
- **`rocky-full-verification.spec.ts`** - Fully automated score generation and verification
  - Tests: Score generation, NVX1 store integration, chord data conversion
  - Assertions: Score exists, measures count, chord data length
  
- **`rocky-features-smoke.spec.ts`** - Quick verification of new features
  - Tests: Practice coach route, ear training route, progression generation in theater
  - Timeout: 120s for AI responses
  
- **`rocky-bach-prelude-chat.spec.ts`** - Chat-based Bach Prelude generation
  - Tests: Asking Rocky via chat to create Bach Prelude in C
  - Simulates user interaction with chat interface
  
- **`rocky-theater-workflow.spec.ts`** - Complete Rocky → Theater workflow
  - Tests: Progression creation → Navigation → Score display → Layer visibility
  - Verifies: Navigation triggers, NVX1 store population, layer functionality

#### Harmonic Analysis Tests
- **`rocky-harmonic-analysis.spec.ts`** - Harmonic analysis integration
  - Tests: Progression generation → Harmonic analysis → Roman numeral display
  - Verifies: Analysis triggers, Roman numeral correctness
  
- **`rocky-score-conversion-debug.spec.ts`** - Score conversion debugging
  - Tests: Automated debug and fix for score conversion
  - Captures: Console logs, conversion logic traces, chord data generation

#### Builder/Edge Function Tests
- **`rocky-builder.spec.ts`** - Rocky Score Builder V2 production verification
  - Tests: Edge function response format, cache performance, validation
  - Edge Function: `rocky-generate-optimized`
  - Validates: Response structure, caching behavior, latency metrics
  
- **`rocky-builder-extreme-skepticism.spec.ts`** - Extreme skepticism test suite
  - Tests: Every claimed field, response format, type verification
  - Validates: Response keys, types, score structure, pattern existence
  
- **`rocky-builder-harsher-skepticism.spec.ts`** - Harsher skepticism tests
  - Tests: Validation errors for every possible missing field
  - Test Cases: Empty payload, missing chords/key/mode, invalid BPM, null values
  
- **`rocky-builder-verification-final.spec.ts`** - Final verification after fixes
  - Tests: Invalid mode returns 400, invalid BPM returns 400, valid requests succeed
  - Validates: Error handling, status codes, error messages

#### Debug/Diagnostic Tests
- **`rocky-automated-debug-fix.spec.ts`** - Automated debug and fix workflow
  - Tests: Score conversion logic step-by-step tracing
  - Captures: Beat-by-beat chord tracking, currentChord state changes
  
- **`rocky-tablature-debug.spec.ts`** - Tablature auto-generation debugging
  - Tests: Console log capture during Rocky generation
  - Captures: All console messages, errors, warnings, page errors
  
- **`rocky-chrome-verification.spec.ts`** - Chrome-specific verification
  - Tests: Generate score in Chrome, verify no errors
  - Captures: Console errors, warnings, logs, page errors, failed requests
  
- **`rocky-visual-check.spec.ts`** - Visual inspection test
  - Tests: Capture what user sees in browser
  - Captures: Page title, visible text, chord diagrams, tablature elements
  
- **`rocky-launch-and-keep-open.spec.ts`** - Manual inspection helper
  - Tests: Generate score and leave browser open for inspection
  - Purpose: Manual debugging aid

#### Integration Tests
- **`rocky-new-features.spec.ts`** - New features smoke tests
  - Tests: Feature accessibility and functionality
  - Verifies: Routes load, components render, basic interactions

#### Theater Integration
- **`theater.rocky-integration.spec.ts`** - Theater + Rocky integration
  - Tests: Rocky progression triggers theater display
  - Verifies: Score loading, layer visibility, widget orchestration

---

### 2. Integration Tests (Vitest) - `tests/integration/`

- **`rocky-harmonic-workflow.spec.ts`** - Harmonic analysis workflow integration
  - Tests: Rocky progression → Harmonic analysis → MSM visualization
  - Verifies: Analysis completion, smart suggestions, caching, Rocky learning integration

---

### 3. Unit Tests (Vitest) - `src/services/__tests__/`, `src/components/__tests__/`

#### Service Layer Tests
- **`RockyMultiModalService.test.ts`** - Multi-modal service unit tests
  - Tests: `startRealTimeAudioFeedback`, `stopRealTimeAudioFeedback`, `analyzeAudio`
  - Mocks: Supabase, GlobalMidiEventBus, BasicPitchTranscriber
  
- **`MSMRockyBridge.test.ts`** - MSM-Rocky bridge unit tests
  - Tests: `analyzeProgression`, caching, voice leading, style classification
  - Mocks: DeepHarmonicAnalysisEngine, VoiceLeadingAnalyzer, StylisticClassifier

#### Component Tests
- **`useRockyEvents.test.tsx`** - Rocky events hook tests
  - Tests: Event listener updates, cleanup, `getRandomResponse`
  - Verifies: Message/mood updates, listener cleanup on unmount

#### Stem Splitter Integration
- **`rocky-integration.test.ts`** - Stem splitter + Rocky integration
  - Tests: `separateAudioStems`, stem filtering, playImmediately option
  - Mocks: Audio context, URL.createObjectURL

---

### 4. Smoke Tests (Node.js) - `scripts/smoke-tests/`

- **`rocky-smoke-test.ts`** - Post-deployment smoke test suite
  - Tests: Database connection, loadScore tool, searchSongs tool, edge function health
  - Usage: `SUPABASE_URL=xxx SUPABASE_SERVICE_ROLE_KEY=xxx npx tsx scripts/smoke-tests/rocky-smoke-test.ts`
  - Validates: All Rocky capabilities are working after deployment

---

### 5. Stress Tests - `tests/rocky/`

- **`phase7-2-integration-stress.test.ts`** - Phase 7.2 integration stress tests
  - Tests: RockyAITutorEngine methods (100 concurrent), RealtimeFeedbackEngine, ConceptTutorEngine
  - Metrics: Duration, console logs, network requests, error rates
  - Purpose: Performance and concurrency validation

- **`phase7-2-unit-stress.test.ts`** - Unit-level stress tests
  - Tests: Individual service methods under load
  - Purpose: Isolated performance testing

- **`phase7-2-stress-test.mjs`** - Node.js stress test runner
  - Purpose: Non-browser stress testing

---

### 6. Browser-Based Test Suites - `src/`

- **`RockyTestGym.tsx`** - Comprehensive testing gym page (`/rocky-test-gym`)
  - Features: Real-time test execution, audio analysis visualization, service health monitoring
  - Test Runner: `testRunner` service
  - Test Scenarios: `allTestSuites` from `@/services/testing/testScenarios`
  - Purpose: Interactive testing dashboard

- **`RockyTestSuite.tsx`** - Browser-based test suite (`/rocky-test`)
  - Tests: Widget orchestration, educational strategy, widget choreography, string detection, finger position inference, real-time coaching, lesson generation, repertoire matching, adaptive learning
  - Purpose: In-browser capability verification

---

### 7. Test Utilities & Helpers

#### Playwright Helpers
- **`tests/e2e/playwright-skeptics-helper.ts`** - Skeptics report extraction
  - Functions: `extractSkepticsReport`, `writeSkepticsReport`
  - Purpose: Extract and persist skeptics reports from localStorage

#### Automation Scripts
- **`scripts/automate-rocky-test.ts`** - Automated Rocky chat test runner
  - Purpose: Browser automation for Rocky chat testing
  - Usage: Provides step-by-step browser automation instructions

---

### 8. Test Configuration Files

#### Playwright Configs
- **`playwright.config.ts`** - Main Playwright configuration
  - Port: `VITE_DEV_PORT` or 9135
  - Base URL: `http://127.0.0.1:${devPort}`
  - Timeout: 240s
  - Projects: chromium, edge (non-CI)
  - Web Server: `pnpm e2e:serve`
  - Features: Trace on first retry, video on failure, screenshot on failure

#### Vitest Configs
- **`vitest.config.ts`** - Main Vitest configuration
  - Environment: jsdom
  - Threads: false (for CWD/import.meta.url compatibility)
  - Coverage: v8 provider, 70% thresholds
  - Includes: `src/**/*.{test,spec}.{ts,tsx}`, `tests/unit/**/*.test.{js,ts,tsx}`
  - Excludes: E2E tests, Playwright specs, integration tests

- **`vitest.integration.config.ts`** - Integration test configuration
  - Extends: `vitest.config.ts`
  - Includes: `tests/integration/**/*.test.{ts,tsx}`
  - Purpose: Separate config for integration tests

---

## 🔧 Test Infrastructure Components

### Edge Functions Under Test
1. **`rocky-chat`** - Main chat edge function
   - Location: `supabase/functions/rocky-chat/index.ts`
   - Tools: 50+ tools (widget orchestration, audio coaching, student intelligence)
   - Session Management: Session hydration and persistence
   - Knowledge Base: `ROCKY_KNOWLEDGE_BASE`
   - Golden Examples: `GOLDEN_EXAMPLES`

2. **`rocky-generate-optimized`** - Optimized score generation
   - Location: `supabase/functions/rocky-generate-optimized/index.ts`
   - Features: Caching (Deno KV), validation, NVX1 score generation
   - Test Coverage: Extensive (builder tests)

3. **`rocky-progression-generator`** - Chord progression generation
   - Location: `supabase/functions/rocky-progression-generator/index.ts`
   - Features: 60+ pattern library, genre/mood matching, key signature parsing

4. **`rocky-skilltree`** - Skill tree integration
   - Location: `supabase/functions/rocky-skilltree/index.ts` (referenced, not directly tested)

### Frontend Components Under Test
1. **`RockyChat.tsx`** - Main chat component
   - Location: `src/components/RockyChat.tsx`
   - Features: Message handling, tool invocation, session persistence, event handling
   - Test Coverage: E2E (chat tests), Unit (events hook)

2. **`RockyScoreBuilder.tsx`** - Score builder UI
   - Location: `src/components/rocky/RockyScoreBuilder.tsx`
   - Features: Structured input, score generation, event dispatch
   - Test Coverage: Builder tests (edge function)

3. **`PracticeMode.tsx`** - Practice mode component
   - Location: `src/components/rocky/PracticeMode.tsx`
   - Features: Practice session management, Supabase integration
   - Test Coverage: Smoke tests

### Services Under Test
1. **`rockyService.ts`** - Core Rocky service
   - Location: `src/services/rockyService.ts`
   - Features: Progression generation, score creation, NVX1 integration
   - Test Coverage: E2E (score generation), Integration (workflows)

2. **`RockyMultiModalService.ts`** - Multi-modal service
   - Location: `src/services/RockyMultiModalService.ts`
   - Features: Real-time audio feedback, audio analysis
   - Test Coverage: Unit tests

3. **`MSMRockyBridge.ts`** - MSM-Rocky bridge
   - Location: `src/services/msm/MSMRockyBridge.ts`
   - Features: Harmonic analysis, voice leading, style classification
   - Test Coverage: Unit tests, Integration tests

4. **Widget Orchestration Services** (10 services)
   - `WidgetOrchestratorService`, `EducationalStrategyEngine`, `WidgetChoreographyService`, `StringDetectionService`, `FingerPositionInferenceService`, `RealTimeCoachingService`, `LessonGeneratorService`, `RepertoireMatchingService`, `AdaptiveLearningService`
   - Test Coverage: Browser-based test suite, Mega test suite

---

## 📈 Test Coverage Gaps & Opportunities

### Well-Covered Areas ✅
- Score generation (extensive E2E coverage)
- Edge function validation (builder tests)
- Harmonic analysis (integration + E2E)
- Theater integration (workflow tests)
- Service layer existence (mega test suite)

### Coverage Gaps ⚠️
1. **Tool Invocation Coverage** - Limited testing of individual tool calls
2. **Session Persistence** - No dedicated tests for session hydration/persistence
3. **Error Handling** - Limited edge case testing (quota errors, API failures)
4. **Performance** - No load/performance tests for chat responses
5. **Knowledge Base** - No tests verifying knowledge base accuracy/completeness
6. **Golden Examples** - No tests verifying example quality/coverage
7. **Multi-Modal** - Limited real audio input testing
8. **Widget Orchestration** - No E2E tests for widget orchestration workflows
9. **Student Intelligence** - No tests for student profile/learning path generation
10. **Real-Time Coaching** - No tests for real-time audio feedback accuracy

### Missing Test Types 🔴
1. **Forensic Diagnostics** - ✅ NOW AVAILABLE: `rocky-magnificent-diagnostic.spec.ts`
2. **Regression Tests** - No systematic regression test suite
3. **Security Tests** - No tests for API key handling, input validation
4. **Accessibility Tests** - No a11y tests for Rocky UI components
5. **Cross-Browser Tests** - Limited cross-browser testing (mostly Chromium)

### Magnificent Diagnostic Test Suite (NEW) ✅
- **`rocky-magnificent-diagnostic.spec.ts`** - Industry-standard comprehensive stress test
  - 7 test categories covering entire skill tree
  - Predicted vs Actual comparison for each function
  - Multi-user simulation (2 concurrent users)
  - Behavioral verification (not just output)
  - Detailed diagnostic reports
  - Run: `pnpm rocky:diagnostic`
  - Spec: `docs/testing/ROCKY_MAGNIFICENT_DIAGNOSTIC_SPEC.md`

---

## 🎯 Recommended Next Steps

1. **Create Comprehensive Forensic Test Suite** - Exhaustive stress testing for all Rocky capabilities
2. **Add Tool Invocation Tests** - Test each of the 50+ tools individually
3. **Add Session Persistence Tests** - Verify session hydration/persistence across page reloads
4. **Add Error Handling Tests** - Test quota errors, API failures, network issues
5. **Add Performance Tests** - Load testing for chat responses, score generation
6. **Add Knowledge Base Tests** - Verify knowledge base accuracy and completeness
7. **Add Multi-Modal Tests** - Real audio input testing with various formats
8. **Add Widget Orchestration E2E Tests** - End-to-end widget orchestration workflows
9. **Add Student Intelligence Tests** - Profile generation, learning path creation
10. **Add Real-Time Coaching Tests** - Audio feedback accuracy and latency

---

## 📝 Test Execution Commands

### Playwright E2E Tests
```bash
# Run all Rocky E2E tests
pnpm playwright test tests/e2e/rocky-*.spec.ts

# Run specific test file
pnpm playwright test tests/e2e/rocky-full-verification.spec.ts

# Run with UI
pnpm playwright test tests/e2e/rocky-full-verification.spec.ts --ui

# Run in debug mode
pnpm playwright test tests/e2e/rocky-full-verification.spec.ts --debug
```

### Vitest Unit/Integration Tests
```bash
# Run all unit tests
pnpm test

# Run integration tests
pnpm test:integration

# Run specific test file
pnpm test src/services/__tests__/RockyMultiModalService.test.ts
```

### Smoke Tests
```bash
# Run Rocky smoke test
SUPABASE_URL=xxx SUPABASE_SERVICE_ROLE_KEY=xxx npx tsx scripts/smoke-tests/rocky-smoke-test.ts
```

### Stress Tests
```bash
# Run Phase 7.2 stress tests
pnpm playwright test tests/rocky/phase7-2-integration-stress.test.ts
```

### Browser-Based Test Suites
```bash
# Navigate to test gym
# http://localhost:9135/rocky-test-gym

# Navigate to test suite
# http://localhost:9135/rocky-test
```

---

## 🔍 Test Artifacts & Reports

### Playwright Reports
- Location: `playwright-report/`
- Format: HTML, JSON
- Generated: On test run

### Test Results
- Location: `tests/rocky/test-results.json`
- Format: JSON
- Contains: Test metrics, pass/fail status, error details

### Screenshots
- Location: `playwright-report/`, `tests/test-artifacts/`
- Generated: On test failure (configured in `playwright.config.ts`)

### Videos
- Location: `playwright-report/`
- Generated: On test failure (configured in `playwright.config.ts`)

---

## 📚 References

- **Playwright Docs:** https://playwright.dev
- **Vitest Docs:** https://vitest.dev
- **RockyAI Documentation:** `docs/` directory
- **Edge Function Docs:** `supabase/functions/rocky-chat/README.md` (if exists)

---

**End of Catalog**

