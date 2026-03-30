# ROXY Status Doctrine (Truth & Readiness)

**Purpose:** One-page operational doctrine to keep ROXY truthful, reproducible, and safe across agents and hosts.

## 1) Root Layout Doctrine (Single Truth)

ROXY uses a single umbrella root with strict separation:

```
$ROXY_ROOT/
  src/   # Git-tracked code only (roxy.git)
  etc/   # config + secrets (not Git)
  var/   # runtime data/state (not Git)
  log/   # logs (optional)
```

**Rule:** systemd must reference `$ROXY_ROOT/src` for code and `$ROXY_ROOT/etc` for env.

## 2) Readiness Contract

A system is only “ready” if all are true:
- `roxy-core /ready` returns `ready:true`
- Postgres memory backend is active (no fallback)
- Ollama pools (11434 + 11435) reachable
- Orchestrator `/health/orchestrator` returns HTTP 200 (degraded states must be explicit)

## 3) Truth Gate (Doctor)

**Human:**
```
/home/mark/.roxy/scripts/stack_doctor.sh
```

**Automation (pure JSON, fast):**
```
/home/mark/.roxy/scripts/stack_doctor.sh --json --fast > /tmp/stack_doctor.json
```

Doctrine rules for doctor:
- JSON mode must emit JSON only
- `--fast` must skip any state mutations
- Any slow path must be explicit

## 4) No-Drift Git Doctrine

- No git operations on sshfs mounts.
- No mirrors unless explicitly requested.
- Optional read-only remote git probe allowed only with explicit host + path:

```
ROXY_REMOTE_GIT_PATH=~/mindsong-juke-hub \
  /home/mark/.roxy/scripts/stack_doctor.sh --json --remote-git macstudio
```

## 5) Rebuild Doctrine (SSD Loss)

Rebuild is deterministic:
1. Clone `$ROXY_ROOT/src`
2. Restore `$ROXY_ROOT/etc`
3. Restore `$ROXY_ROOT/var`
4. Enable systemd units
5. Run doctor gates

Reference: `docs/runbooks/RUNBOOK_ROXY_REBUILD.md`

## 6) Change Governance

- Never normalize runtime data in code to bypass validation.
- Schema fixes happen at the source via approved scripts.
- All changes must be reproducible from Git + config + runtime backups.

