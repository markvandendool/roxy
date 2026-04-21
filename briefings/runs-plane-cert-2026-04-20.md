# Phase 2 Runs Plane Certification

Date: 2026-04-20 local
Scope: `/api/runs` recertification on roxy-local ingress surfaces using `PROD-GATE-NOOUT-001`.

## Verdict

Status: partial pass with remaining gap.

Direct gateway (`:4899`), proxy (`:9136`), and Vite (`:9135`) all produced terminal run records. During certification, a real safety defect was confirmed: the local `CliMainExecutor` path ignored `request.modelOverride` and launched `gpt-5.3-codex` on the main checkout. That defect is now patched and live-verified. Podium operator ingress was not executed in this pass.

## What Broke

- Pre-fix proxy run `run-1776736134768-cf83350c` and Vite run `run-1776736265731-03fec3a4` both enqueued correctly, then executed a real local Codex path instead of the intended invalid-model safe-failure path.
- Worker evidence before the fix: `Model=gpt-5.3-codex`.
- The local path also hit a separate git defect: `Auto-commit failed ... spawnSync git ETIMEDOUT`, followed by terminal failure `No commit was made during execution`.

## What Changed

Patched `/home/mark/mindsong-juke-hub/luno-orchestrator/src/execution/cli-main-executor.ts` so the normal local CLI path honors `request.modelOverride` through `resolveCliMainModel()`. Added a unit test case in `/home/mark/mindsong-juke-hub/luno-orchestrator/tests/unit/cli-main-executor.dispatch.test.ts`.

## Live Validation

Post-fix direct run `run-1776736523101-86572657` used `modelOverride=definitely-not-a-real-model` and the worker log showed `Model=definitely-not-a-real-model`, then failed immediately with `codex exited with code 1`. That restores the safe-failure oracle needed for bounded certification.

Scoped diff check for `src/services/KhronosTimeEngine.ts` was empty after the run.

## Residual Gaps

- Podium operator ingress still needs its own bounded certification run.
- `bun test` is currently blocked by an environment-level `EPERM` reading `src/test-setup.ts`, so the test harness is not trustworthy until that filesystem issue is fixed.
- Generic git operations on the mounted repo can still time out; this is separate from the modelOverride fix and should be treated as its own defect.
