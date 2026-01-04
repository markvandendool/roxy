# Cognitive Contract CI Integration Guide

**Purpose:** Guide for integrating cognitive contract tests into CI/CD pipelines.

---

## Overview

Cognitive contract tests validate Rocky's authority boundaries and must run **before** E2E tests and deployments. This ensures violations are caught early and prevent capability drift.

---

## CI Workflow Integration

### GitHub Actions

The workflow file `.github/workflows/cognitive-contract.yml` is already configured:

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Manual dispatch
- Changes to Rocky-related files

**Steps:**
1. Run cognitive contract tests
2. Generate violation report
3. Upload report as artifact
4. Evaluate CI gating (strict mode: fail on any violation)
5. Comment PR with summary

### Enforcement Modes

**Strict Mode (Default):**
- Fail build on **any** violation
- Use for: `main` branch, production deployments

**Warning Mode:**
- Log violations but don't fail build
- Use for: `develop` branch, feature branches

**Permissive Mode:**
- Only fail on critical violations
- Use for: experimental branches, WIP

### Configuration

Edit `tests/forensic/.ci-config.ts` to change enforcement:

```ts
export const DEFAULT_CI_CONFIG: CIGatingConfig = {
  enforcementMode: 'strict', // Change to 'warning' or 'permissive'
  // ... thresholds
};
```

---

## Local Development

### Run Tests
```bash
# Run all forensic tests
pnpm test tests/forensic/

# Run specific test file
pnpm test tests/forensic/rocky-cognitive-contract.spec.ts

# Run with coverage
pnpm test tests/forensic/ --coverage
```

### View Reports

Reports are automatically generated in:
```
tests/artifacts/cognitive-contract/
  ├── cognitive-contract-report-{timestamp}.json
  └── cognitive-contract-report-{timestamp}.txt
```

### Pre-commit Hook (Recommended)

Add to `.husky/pre-commit`:

```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

echo "🧠 Running cognitive contract tests..."
pnpm test tests/forensic/rocky-cognitive-contract.spec.ts

if [ $? -ne 0 ]; then
  echo "❌ Cognitive contract violations detected. Fix before committing."
  exit 1
fi
```

---

## Violation Artifacts

### JSON Report Structure

```json
{
  "metadata": {
    "generatedAt": "2025-12-12T...",
    "testSuiteVersion": "1.0.0",
    "totalNodes": 5821,
    "totalEdges": 15000
  },
  "summary": {
    "totalViolations": 3,
    "bySeverity": {
      "critical": 0,
      "high": 2,
      "medium": 1,
      "low": 0
    },
    "byCategory": {
      "TOOL_AUTHORITY": 2,
      "SKILL_AUTHORITY": 1
    }
  },
  "violations": [
    {
      "id": "violation_DISCONNECTED_TOOL_TOOL_AUTHORITY_...",
      "type": "DISCONNECTED_TOOL",
      "category": "TOOL_AUTHORITY",
      "severity": "high",
      "description": "Tool 'analyzeImage' is not connected to any active skills",
      "affectedNodes": ["tool:analyzeImage"],
      "recommendedFix": "Connect tool 'analyzeImage' to at least one active skill",
      "detectedAt": "2025-12-12T...",
      "detectedBy": "rocky-cognitive-contract.spec.ts"
    }
  ],
  "execution": {
    "duration": 1234,
    "testsRun": 15,
    "testsPassed": 12,
    "testsFailed": 3
  }
}
```

### Human-Readable Summary

The `.txt` report provides a formatted summary:

```
═══════════════════════════════════════════════════════════════════
ROCKY COGNITIVE CONTRACT VIOLATION REPORT
═══════════════════════════════════════════════════════════════════

Generated: 2025-12-12T...
Graph: 5821 nodes, 15000 edges

EXECUTION SUMMARY
───────────────────────────────────────────────────────────────────
Tests Run: 15
Tests Passed: 12
Tests Failed: 3
Duration: 1.23s

VIOLATION SUMMARY
───────────────────────────────────────────────────────────────────
Total Violations: 3

By Severity:
  Critical: 0
  High:    2
  Medium:  1
  Low:     0

VIOLATIONS
───────────────────────────────────────────────────────────────────

HIGH SEVERITY (2)

1. [DISCONNECTED_TOOL] Tool "analyzeImage" is not connected to any active skills
   Affected Nodes: tool:analyzeImage
   Recommended Fix: Connect tool "analyzeImage" to at least one active skill
   Detected By: rocky-cognitive-contract.spec.ts
```

---

## Dashboard Integration

### Violation Trends

Track violations over time:

```ts
import { cognitiveContractReporter } from '@/services/rocky/CognitiveContractReporter';

const report = cognitiveContractReporter.generateReport();
// Use report.summary.bySeverity for trend tracking
```

### Auto-Ticketing

Generate tickets from violations:

```ts
const fixes = cognitiveContractReporter.generateFixes(report.violations);
// Create tickets for each fix
```

---

## Best Practices

### 1. Fix Violations Before Merging

**Never merge PRs with violations** (unless in permissive mode for experimental work).

### 2. Review Violations Regularly

Check reports weekly to identify:
- Recurring violations
- Capability drift
- Missing connections

### 3. Update Tests When Adding Features

When adding new tools/skills:
- Ensure they pass authority tests
- Connect them properly in the graph
- Mark knowledge as canonical

### 4. Use Violations as Design Feedback

If violations keep appearing:
- Review graph structure
- Consider refactoring
- Update authority model

---

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Node.js version matches CI
- Ensure dependencies are installed (`pnpm install`)
- Clear cache: `pnpm test tests/forensic/ --no-cache`

### Report Not Generated

- Check `tests/artifacts/cognitive-contract/` directory exists
- Ensure tests complete (even if they fail)
- Check file permissions

### False Positives

- Review violation details in report
- Check if graph structure needs updating
- Consider adjusting severity thresholds

---

## Next Steps

1. ✅ CI integration complete
2. ⏳ Add pre-commit hook (recommended)
3. ⏳ Build violation dashboard
4. ⏳ Set up auto-ticketing from violations
5. ⏳ Add trend tracking

---

**End of Guide**





