# Rocky Magnificent Diagnostic Test Specification

**Tags:** `rocky-governance`, `testing`, `playwright`, `forensic-diagnostics`

**Purpose:** Industry-standard comprehensive stress test for Rocky's entire skill tree, generating actionable diagnostics and intelligence profile.

---

## Executive Summary

The "Magnificent Playwright Diagnostic Test" is a comprehensive test suite that exercises Rocky's entire skill tree in a controlled, predictable manner. It compares **predicted vs actual** results for each function, enabling rapid assessment of Rocky's intelligence profile.

**Key Characteristics:**
- ✅ Industry-standard testing protocols (SMART, Arrange-Act-Assert)
- ✅ Covers all 7 major capability categories
- ✅ Optimized API calls (simulates 2 human users)
- ✅ Behavioral verification (not just output)
- ✅ Multi-user simulation
- ✅ Detailed diagnostic reports

---

## Test Categories

### Category 1: Basic Q&A and Core Knowledge
Simple question-answer pairs to verify Rocky's foundational knowledge and language understanding.

**Tests:**
- 1.1: Basic greeting test
- 1.2: Factual question about music theory
- 1.3: Music theory concept explanation

**Success Criteria:**
- Response contains relevant keywords
- Response time < 10s
- No system errors

### Category 2: Complex Reasoning & Multi-Step Tasks
Queries requiring multi-step reasoning or planning.

**Tests:**
- 2.1: Multi-step progression design
- 2.2: Musical analysis with reasoning

**Success Criteria:**
- Coherent step-by-step response
- Correct tool invocation (if applicable)
- Response time < 30s

### Category 3: Tool/Plugin Usage (Edge Functions)
Tests for each external tool Rocky can invoke.

**Tests:**
- 3.1: Test generateProgression tool
- 3.2: Test showScale tool
- 3.3: Test searchSongs tool

**Success Criteria:**
- Correct tool invoked (behavioral verification)
- Valid tool response
- Response time < 20s

### Category 4: Memory and Context Retention
Multi-turn conversation tests for context maintenance.

**Tests:**
- 4.1: Multi-turn conversation with context retention

**Success Criteria:**
- Follow-up references previous context
- No context confusion
- Response time < 15s

### Category 5: Widget Control & UI Navigation
Tests for Rocky's ability to control UI elements.

**Tests:**
- 5.1: Test piano widget control
- 5.2: Test fretboard widget control

**Success Criteria:**
- Correct widget tool invoked
- UI element becomes visible
- Response time < 15s

### Category 6: Error Handling & Edge Cases
Tests for graceful handling of invalid/ambiguous inputs.

**Tests:**
- 6.1: Invalid key test
- 6.2: Ambiguous request test
- 6.3: Out of scope request test

**Success Criteria:**
- No system crash
- Appropriate error/clarification response
- Response time < 10s

### Category 7: Performance under Load (Light Stress)
Light stress testing with concurrent users.

**Tests:**
- 7.1: Two concurrent users interacting with Rocky
- 7.2: Response time consistency (5 sequential requests)

**Success Criteria:**
- Both users receive independent responses
- No cross-talk between sessions
- Response time variance < 3x
- Average response time < 15s

---

## Predicted vs Actual Comparison

Each test has a **prediction** that defines:
- **expectedBehavior**: What Rocky should do
- **expectedOutput**: What Rocky should say (string or regex)
- **expectedTool**: What tool should be invoked (if applicable)
- **maxDuration**: Maximum acceptable response time

After execution, the **actual** result is compared:
- **outputMatch**: Does response match expected pattern?
- **behaviorMatch**: Does behavior match expected?
- **toolMatch**: Was correct tool invoked?
- **withinTime**: Was response within time limit?

**Pass condition:** All deltas must be true.

---

## Industry Standards Applied

### SMART Criteria
- **Specific**: Each test has well-defined purpose
- **Measurable**: Pass/fail with numeric metrics
- **Attainable**: Realistic thresholds based on user experience
- **Relevant**: Tests actual user scenarios
- **Time-bound**: Maximum durations enforced

### Arrange-Act-Assert Pattern
```typescript
// Arrange
await page.goto(CONFIG.baseUrl + '/theater');
await page.waitForSelector('[data-testid="theater-stage"]');

// Act
const { response, duration } = await sendMessageAndWaitForResponse(page, input);
const toolUsed = await extractToolUsage(page, logs);

// Assert
const result = evaluateResult(testId, { response, duration, toolUsed }, logs);
expect(result.passed).toBe(true);
```

### Behavior Verification
Tests verify **how** Rocky reaches an answer, not just the answer:
```typescript
// Verify tool was actually used (not just output)
if (TEST_PREDICTIONS[scenario.id].expectedTool) {
  expect(toolUsed, 'Expected tool was not invoked').toBe(TEST_PREDICTIONS[scenario.id].expectedTool);
}
```

### Logging and Observability
Every test captures:
- Console logs
- Network requests
- Tool invocations
- Response times
- Error states

---

## API Call Optimization

### Rate Limiting
- `delayBetweenMessages`: 2s (simulates human typing)
- `delayBetweenTests`: 1s
- `maxConcurrentUsers`: 2

### Minimal Redundancy
- Each test case is unique
- No overlapping scenarios
- Every call provides new information

### Multi-User Simulation
- 2 isolated browser contexts
- Independent sessions
- No cross-talk verification

---

## Running the Test

### Full Suite
```bash
pnpm playwright test tests/e2e/rocky-magnificent-diagnostic.spec.ts
```

### Specific Category
```bash
pnpm playwright test tests/e2e/rocky-magnificent-diagnostic.spec.ts --grep "Category 3"
```

### With UI
```bash
pnpm playwright test tests/e2e/rocky-magnificent-diagnostic.spec.ts --ui
```

### Debug Mode
```bash
pnpm playwright test tests/e2e/rocky-magnificent-diagnostic.spec.ts --debug
```

---

## Report Output

### JSON Report
Location: `tests/artifacts/rocky-magnificent/rocky-magnificent-diagnostic-{timestamp}.json`

Contains:
- Summary statistics
- All test results with predictions and actuals
- Category breakdown
- Skill tree coverage
- Recommendations

### Human-Readable Report
Location: `tests/artifacts/rocky-magnificent/rocky-magnificent-diagnostic-{timestamp}.txt`

Contains:
- Summary table
- Category breakdown
- Failed tests with details
- Recommendations

### Sample Report
```
╔══════════════════════════════════════════════════════════════════════════════╗
║   ROCKYAI MAGNIFICENT DIAGNOSTIC REPORT                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Total Tests: 15
Passed: 13 (86.7%)
Failed: 2 (13.3%)
Avg Response Time: 5.23s

CATEGORY BREAKDOWN
BasicQA              3/3 passed (100.0%)
ComplexReasoning     2/2 passed (100.0%)
ToolUsage           2/3 passed (66.7%)
MemoryContext       2/2 passed (100.0%)
WidgetControl       2/2 passed (100.0%)
ErrorHandling       2/3 passed (66.7%)
Performance          2/2 passed (100.0%)

RECOMMENDATIONS
• WARNING: ToolUsage has 33% failure rate. Review failing tests.
• WARNING: ErrorHandling has 33% failure rate. Review failing tests.
```

---

## Integration with Governance

### Cognitive Contract
Failed tests generate violations that integrate with the Cognitive Contract:
- Missing skill capability → `PLANNED_SKILL_CLAIM`
- Tool invocation failure → `DISCONNECTED_TOOL`

### Knowledge Graph
Test coverage mapped to Knowledge Graph nodes:
- Tested skills tracked
- Untested skills identified
- Coverage percentage calculated

### CI/CD
Can be integrated into CI pipeline:
```yaml
- name: Run Rocky Magnificent Diagnostic
  run: pnpm playwright test tests/e2e/rocky-magnificent-diagnostic.spec.ts
  
- name: Upload Diagnostic Report
  uses: actions/upload-artifact@v3
  with:
    name: rocky-magnificent-diagnostic
    path: tests/artifacts/rocky-magnificent/
```

---

## Extending the Test

### Adding New Test Scenarios

1. Add prediction to `TEST_PREDICTIONS`:
```typescript
'new-test-id': {
  expectedBehavior: 'Rocky does X',
  expectedOutput: /regex/i,
  expectedTool: 'toolName',
  maxDuration: 15000,
  category: 'ToolUsage',
},
```

2. Add scenario to appropriate category:
```typescript
toolUsage: [
  // ... existing
  {
    id: 'new-test-id',
    input: 'User message',
    description: 'Test description',
  },
],
```

### Adding New Categories

1. Add category to `TestCategory` type
2. Add prediction entries for category
3. Create new `test.describe` block
4. Add to `generateReport` coverage

---

## Success Metrics

### Per-Test Metrics
- Output match (boolean)
- Tool match (boolean)
- Time within limit (boolean)
- Response duration (ms)

### Aggregate Metrics
- Overall pass rate (%)
- Average response time (ms)
- Category pass rates (%)
- Skill tree coverage (%)

### Quality Thresholds
- Target pass rate: >90%
- Target avg response time: <10s
- Target coverage: >80% of skill tree

---

## Maintenance

### When to Update
- New Rocky capability added
- Tool behavior changed
- UI selectors changed
- Performance requirements changed

### How to Update
1. Run test to identify failures
2. Update predictions if behavior changed intentionally
3. Fix bugs if behavior changed unintentionally
4. Document changes in commit message

---

## References

- **Test File:** `tests/e2e/rocky-magnificent-diagnostic.spec.ts`
- **Artifacts:** `tests/artifacts/rocky-magnificent/`
- **Playwright Docs:** https://playwright.dev
- **Rocky Governance:** `docs/ROCKY_BRAIN.md`
- **Cognitive Contract:** `docs/testing/ROCKY_COGNITIVE_CONTRACT_SPEC.md`

---

**End of Specification**





