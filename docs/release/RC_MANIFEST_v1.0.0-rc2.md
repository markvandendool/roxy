# Release Candidate Manifest: v1.0.0-rc2

**Status:** FROZEN
**Freeze Date:** 2026-01-10T18:05:00-07:00
**Policy:** No modifications to this tag. Changes require v1.0.0-rc3.

---

## Release Identity

| Field | Value |
|-------|-------|
| **Tag** | `v1.0.0-rc2` |
| **Commit SHA** | `3c95fa4de00f8843b1c4f0076f99591d6e3239d9` |
| **Short SHA** | `3c95fa4` |
| **Tag Date** | 2026-01-10 |
| **Tagged By** | Claude Code |

---

## /version Endpoint Output

```json
{
  "version": "1.0.0-rc2",
  "service": "roxy-core",
  "git_sha": "3c95fa4",
  "git_sha_full": "3c95fa4de00f8843b1c4f0076f99591d6e3239d9",
  "build_time": "2026-01-10T17:15:34.301449",
  "python_version": "3.12.3",
  "platform": "Linux"
}
```

---

## Gate Verification Status

All gates passed at freeze time:

| Gate | Status | Proof File |
|------|--------|------------|
| Gate A (Resilience) | PASS | `proofs/gateA_20260110_171519.log` |
| Gate B (Overload) | PASS | `proofs/gateB_20260110_171520.log` |
| Gate E (Observability) | PASS | `proofs/gateE_20260110_171524.log` |

### Gate Verification Command

```bash
~/.roxy/scripts/gateA_resilience.sh
~/.roxy/scripts/gateB_overload.sh
~/.roxy/scripts/gateE_observability.sh
```

---

## Dependency Versions

### Python Runtime

```
Python 3.12.3
```

### Key Python Packages

```
aiohttp==3.13.3
fastapi==0.128.0
prometheus_client==0.23.1
requests==2.32.5
uvicorn==0.40.0
```

### Ollama

```
ollama version 0.13.5
```

### System

```
Platform: Linux 6.18.2-1-t2-noble
Host: macpro-linux
```

---

## Configuration at Freeze

| Config | Value |
|--------|-------|
| Base URL | `http://127.0.0.1:8766` |
| W5700X Pool | `http://127.0.0.1:11434` |
| 6900XT Pool | `http://127.0.0.1:11435` |
| Token File | `~/.roxy/secret.token` |
| Log Path | `~/.roxy/logs/roxy-core.log` |

---

## Files Included in This Release

Core:
- `roxy_core.py` - Main HTTP server
- `benchmark_service.py` - Benchmark orchestration
- `pool_identity.py` - Pool configuration SSOT
- `prometheus_metrics.py` - Metrics exposition

Scripts:
- `scripts/prod_deploy.sh` - Gate0 deploy
- `scripts/wait-for-ready.sh` - Readiness polling
- `scripts/gateA_resilience.sh` - Pool resilience test
- `scripts/gateB_overload.sh` - Overload protection test
- `scripts/gateE_observability.sh` - Metrics verification
- `scripts/git_auth_doctor.sh` - Auth verification

Documentation:
- `docs/RUNBOOK.md` - Operator runbook
- `docs/GIT_AUTH_STANDARD.md` - Git auth standard
- `CHANGELOG.md` - Release changelog
- `PROD_CUTOVER_PLAN.md` - Production plan

CI:
- `.github/workflows/ci.yml` - Syntax checks

---

## Known Limitations

1. SSH key not registered on GitHub (HTTPS with gh CLI works)
2. `git_dirty: true` in /version due to untracked files (not in commit)
3. Systemd unit lacks `ExecStartPost` readiness gate (to be added in v1.0.0)

---

## Upgrade Path

From v1.0.0-rc1:
- Remediation hints now reference RUNBOOK.md section 3
- 217 stale files cleaned up
- Auth standard documented
- Pre-commit hook for nested repo detection

---

## Verification Checklist

Before promoting to v1.0.0:

- [ ] All gates pass (`gateA`, `gateB`, `gateE`)
- [ ] `/ready` returns 200
- [ ] `/version` shows correct SHA
- [ ] `/metrics` exports all required metrics
- [ ] Token auth works on mutating endpoints
- [ ] Restart via `prod_deploy.sh` succeeds

---

## Contact

- Proof artifacts: `~/.roxy/proofs/`
- Logs: `~/.roxy/logs/`
- Config: `~/.roxy/config.json`
