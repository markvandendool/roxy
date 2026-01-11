# ROXY Operator Runbook

**Version:** 1.0.0-rc2
**Last Updated:** 2026-01-10

---

## Quick Reference

| Action | Command |
|--------|---------|
| Deploy/Restart | `./scripts/prod_deploy.sh` |
| Check Ready | `curl http://127.0.0.1:8766/ready` |
| Check Health | `curl http://127.0.0.1:8766/health` |
| View Logs | `journalctl _COMM=python -f` or `tail -f ~/.roxy/logs/roxy-core.log` |
| View Metrics | `curl http://127.0.0.1:8766/metrics` |

---

## 1. Service Management

### Start/Restart Service
```bash
# Full production deploy (recommended)
~/.roxy/scripts/prod_deploy.sh

# Or manual restart
systemctl --user restart roxy-core.service
~/.roxy/scripts/wait-for-ready.sh 30
```

### Stop Service
```bash
systemctl --user stop roxy-core.service
```

### Check Status
```bash
systemctl --user status roxy-core.service
```

---

## 2. Health Checks

### /health - Service Alive
Returns 200 if core service is running. May return 200 even if pools are down.
```bash
curl -sS http://127.0.0.1:8766/health | jq
```
**Expected output:**
```json
{
  "status": "ok",
  "service": "roxy-core",
  "checks": {
    "auth_token": "ok",
    "rate_limiter": "ok",
    "chromadb": "ok",
    "ollama": {"ok": true, ...}
  }
}
```

### /ready - Production Ready
Returns 200 ONLY if all pools are reachable. Use for load balancer health checks.
```bash
curl -sS http://127.0.0.1:8766/ready | jq
```
**Expected output (healthy):**
```json
{
  "ready": true,
  "message": "All pools configured and reachable",
  "checks": {
    "pool_invariants": {
      "ok": true,
      "pools": {
        "w5700x": {"reachable": true, "latency_ms": 0.4},
        "6900xt": {"reachable": true, "latency_ms": 0.3}
      }
    }
  }
}
```

**Failure output (HTTP 503):**
```json
{
  "ready": false,
  "error_code": "POOLS_UNREACHABLE",
  "message": "Pools not reachable: ['6900xt']",
  "remediation_hint": "Verify ollama responding: 6900xt (port 11435). See RUNBOOK.md section 3."
}
```

---

## 3. Common Issues & Remediation

### Issue: /ready returns 503

**Symptoms:**
- HTTP 503 from /ready
- `error_code: POOLS_UNREACHABLE`

**Diagnosis:**
```bash
curl http://127.0.0.1:8766/ready | jq '.message'
curl http://127.0.0.1:11434/api/version  # Check w5700x pool
curl http://127.0.0.1:11435/api/version  # Check 6900xt pool
```

**Remediation:**
1. Check which pool is down from the error message
2. Verify ollama processes: `pgrep -a ollama`
3. Check port bindings: `ss -tlnp | grep -E "11434|11435"`
4. Restart the affected ollama instance

### Issue: Service won't start

**Symptoms:**
- `systemctl --user status roxy-core` shows failed

**Diagnosis:**
```bash
journalctl --user -u roxy-core -n 50
cat ~/.roxy/logs/roxy-core.log | tail -50
```

**Remediation:**
1. Check Python syntax: `python3 -m py_compile ~/.roxy/roxy_core.py`
2. Check dependencies: `~/.roxy/venv/bin/pip check`
3. Verify token file: `test -f ~/.roxy/secret.token && echo OK`

### Issue: Benchmark stuck/running

**Symptoms:**
- /bench/status shows "running" indefinitely
- New benchmarks return 409 Conflict

**Diagnosis:**
```bash
curl -sS http://127.0.0.1:8766/bench/status | jq
```

**Remediation:**
```bash
TOKEN=$(cat ~/.roxy/secret.token)
curl -X POST http://127.0.0.1:8766/bench/cancel \
  -H "X-ROXY-Token: $TOKEN"
```

### Issue: High latency / slow responses

**Symptoms:**
- Requests taking >5s
- Pool latency >10ms

**Diagnosis:**
```bash
curl http://127.0.0.1:8766/metrics | grep latency
curl http://127.0.0.1:8766/ready | jq '.checks.pool_invariants.pools'
```

**Remediation:**
1. Check GPU load: `rocm-smi` or `nvidia-smi`
2. Check model loading: Large models may need unloading
3. Consider restarting ollama instances

---

## 4. Endpoints Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /health | GET | No | Service liveness |
| /ready | GET | No | Production readiness |
| /info | GET | No | Server info, pool status |
| /metrics | GET | No | Prometheus metrics |
| /bench/run | POST | Yes | Start benchmark |
| /bench/status | GET | No | Benchmark status |
| /bench/cancel | POST | Yes | Cancel running benchmark |
| /run | POST | Yes | Execute command |

---

## 5. Logs & Monitoring

### Log Locations
- **File log:** `~/.roxy/logs/roxy-core.log`
- **Journald:** `journalctl _COMM=python` (filter by PID for precision)

### Key Log Patterns
```bash
# Errors
grep -E "ERROR|FAIL" ~/.roxy/logs/roxy-core.log | tail -20

# Warnings
grep "WARNING" ~/.roxy/logs/roxy-core.log | tail -20

# Pool deprecation warnings (BIG/FAST usage)
grep "deprecated" ~/.roxy/logs/roxy-core.log | tail -10
```

### Prometheus Metrics
```bash
# Pool reachability
curl -sS http://127.0.0.1:8766/metrics | grep roxy_pool_reachable

# Ready check counts
curl -sS http://127.0.0.1:8766/metrics | grep roxy_ready_checks

# Request counts
curl -sS http://127.0.0.1:8766/metrics | grep roxy_requests_total
```

---

## 6. Emergency Procedures

### Full Service Recovery
```bash
# 1. Stop everything
systemctl --user stop roxy-core.service

# 2. Clear any stuck state
rm -f /tmp/roxy_*.lock 2>/dev/null

# 3. Verify dependencies
curl -sS http://127.0.0.1:11434/api/version
curl -sS http://127.0.0.1:11435/api/version

# 4. Full deploy
~/.roxy/scripts/prod_deploy.sh
```

### Rollback to Last Known Good
```bash
cd ~/.roxy
git log --oneline -5  # Find last good commit
git checkout <commit_sha>
~/.roxy/scripts/prod_deploy.sh
```

---

## 7. Gate Verification

Run all gates to verify system health:
```bash
~/.roxy/scripts/gateA_resilience.sh   # Dependency resilience
~/.roxy/scripts/gateB_overload.sh     # Overload protection
~/.roxy/scripts/gate2_smoke.sh        # Functional smoke test
~/.roxy/scripts/prod_deploy.sh        # Full deploy gate
```

All gates should end with `PASS`.

---

## 8. Contact & Escalation

- **Proof artifacts:** `~/.roxy/proofs/`
- **Evidence bundles:** `~/ROXY_EVIDENCES/`
- **Config:** `~/.roxy/config.json`
