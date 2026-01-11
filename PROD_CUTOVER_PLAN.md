# ROXY PROD CUTOVER PLAN v1
**Owner:** Claude Code (autonomous)
**Target:** Tagged RC release within 48 hours
**Status:** EXECUTING

---

## Production Contract (SLOs)

| Endpoint | SLO | Failure Mode |
|----------|-----|--------------|
| GET /health | 99.9% 200 in <100ms | 503 if critical deps down |
| GET /ready | 200 only when ALL pools reachable | 503 + remediation hint |
| GET /info | 200 always (best-effort data) | Never fails |
| GET /metrics | 200 with Prometheus exposition | 503 if prometheus unavailable |
| POST /bench/run | 202 Accepted / 409 Conflict / 400 Error | Never 500 |
| POST /run | 200 with result | 503 on ollama failure |

**Graceful Degradation:** If one pool is down, /ready returns 503 but /health may still return 200 (service alive, not ready for full operation).

---

## Critical Path (5 Gates)

### GateA: Dependency Failure Resilience
**Goal:** Prove /ready correctly detects pool failures and recovers.
**Acceptance Criteria:**
1. Stop ollama-6900xt → /ready returns 503 with pool="6900xt" in error
2. Start ollama-6900xt → /ready returns 200 within 10s
3. Metrics update: roxy_pool_reachable{pool="6900xt"} goes 0→1

**Proof Command:**
```bash
./scripts/gateA_resilience.sh
```

### GateB: Overload Protection
**Goal:** Prevent DOS via concurrent requests.
**Acceptance Criteria:**
1. /bench/run rejects concurrent requests with 409
2. Rate limiter active on /run endpoint
3. No crash under 10 concurrent /health requests

**Proof Command:**
```bash
./scripts/gateB_overload.sh
```

### GateC: Operator Runbook
**Goal:** Single-source operator documentation.
**Acceptance Criteria:**
1. docs/RUNBOOK.md exists with: startup, health checks, failure remediation
2. All commands in runbook are tested and produce expected output
3. Failure scenarios documented with exact remediation steps

**Proof Command:**
```bash
test -f docs/RUNBOOK.md && grep -q "systemctl" docs/RUNBOOK.md && echo "PASS"
```

### GateD: Release Packaging
**Goal:** Versioned, tagged, reproducible release.
**Acceptance Criteria:**
1. GET /version returns {version, git_sha, build_time}
2. Git tag v1.0.0-rc1 created
3. prod_deploy.sh works from clean state

**Proof Command:**
```bash
curl -sS http://127.0.0.1:8766/version | jq -e '.git_sha'
```

### GateE: Observability Verification
**Goal:** Confirm all critical metrics are exported.
**Acceptance Criteria:**
1. /metrics returns roxy_requests_total, roxy_pool_*, roxy_ready_*, roxy_errors_total
2. Metrics stable under repeated scrapes (no crashes)
3. Error counter increments on 4xx/5xx responses

**Proof Command:**
```bash
./scripts/gateE_observability.sh
```

---

## Execution Queue

| Step | Gate | Task | Time Est | Status |
|------|------|------|----------|--------|
| 1 | A | Create gateA_resilience.sh | 15m | PENDING |
| 2 | A | Run gateA, capture proof | 10m | PENDING |
| 3 | B | Verify rate limiting exists | 10m | PENDING |
| 4 | B | Create gateB_overload.sh | 15m | PENDING |
| 5 | B | Run gateB, capture proof | 10m | PENDING |
| 6 | C | Write docs/RUNBOOK.md | 30m | PENDING |
| 7 | D | Add /version endpoint | 15m | PENDING |
| 8 | D | Tag v1.0.0-rc1 | 5m | PENDING |
| 9 | E | Create gateE_observability.sh | 15m | PENDING |
| 10 | E | Run gateE, capture proof | 10m | PENDING |
| 11 | - | Final prod_deploy.sh run | 5m | PENDING |
| 12 | - | Document in CHANGELOG.md | 10m | PENDING |

**Total Estimated Time:** ~2.5 hours

---

## Proof Artifacts Location
All gate proofs stored in: `~/.roxy/proofs/<gate>_<timestamp>.log`

---

## Rollback Plan
If any gate fails:
1. Revert to last known-good commit
2. Re-run prod_deploy.sh
3. Verify Gate2 passes

---

## Sign-off Criteria for v1.0.0-rc1
- [ ] GateA PASS
- [ ] GateB PASS
- [ ] GateC PASS (RUNBOOK.md exists)
- [ ] GateD PASS (/version works, tag exists)
- [ ] GateE PASS
- [ ] prod_deploy.sh exits 0
- [ ] No manual sleeps in any script
