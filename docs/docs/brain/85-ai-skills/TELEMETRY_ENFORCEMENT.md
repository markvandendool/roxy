# Telemetry Enforcement

**Purpose:** Guidelines for ensuring skill telemetry is properly used and validated in development workflows.

## CI/CD Integration

### GitHub Actions
The repository includes automated validation of Claude Skills integration:

- **Workflow:** `.github/workflows/claude-skills-validation.yml`
- **Triggers:** PRs and pushes affecting docs, `.claude/`, or skill scripts
- **Validations:**
  - Integration script (`pnpm validate:claude-skills`)
  - Integration tests (`pnpm test:claude-skills`)

### Pre-commit Hooks
While not currently enforced, consider adding:

```bash
# .husky/pre-commit
pnpm validate:claude-skills || exit 1
```

## Testing Telemetry

### Manual Testing
1. Enable telemetry: `/enable-skill-telemetry`
2. Perform actions that should trigger skills
3. Verify telemetry output appears in responses
4. Check that correct skills are activated

### Automated Testing
See `tests/claude-skills/integration.test.mjs` for validation tests.

## Telemetry Validation Checklist

When reviewing PRs that affect skills:

- [ ] Telemetry can be enabled/disabled
- [ ] Skill activations are logged correctly
- [ ] Context sources are tracked
- [ ] Trigger phrases are detected
- [ ] Response metrics are captured

## Enforcement Levels

### Level 1: Documentation (Current)
- Telemetry guide exists
- Commands documented
- Usage examples provided

### Level 2: Validation (Current)
- Integration tests validate structure
- CI checks run on PRs
- Scripts verify file existence

### Level 3: Runtime Enforcement (Future)
- Telemetry must be enabled in CI
- Skill activations logged to monitoring
- Metrics dashboard integration

## Related Documentation

- [TELEMETRY_GUIDE.md](./TELEMETRY_GUIDE.md) - How to use telemetry
- [IMPROVEMENT_WORKFLOW.md](./IMPROVEMENT_WORKFLOW.md) - Continuous improvement
- [EXCELLENCE_FRAMEWORK.md](./EXCELLENCE_FRAMEWORK.md) - Metrics framework




























