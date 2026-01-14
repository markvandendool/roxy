# ROXY Root Reconciliation Runbook (Build‑Forward)

**Purpose:** Eliminate split‑brain by migrating to a single ROXY_ROOT with strict src/etc/var separation.

## Target Layout
```
$ROXY_ROOT/
  src/   # Git repo (roxy.git)
  etc/   # config + secrets
  var/   # runtime data/state
  log/   # logs (optional)
```

## Phase 0 — Snapshot (non‑destructive)
- Capture tarballs of existing roots:
  - `/opt/roxy`
  - `/home/mark/.roxy`
  - `/home/mark/roxy` (if present)
  - `/etc/roxy` and `/var/lib/roxy` (if present)

## Phase 1 — Inventory + Classification
- **Code candidates** → move into `$ROXY_ROOT/src` and commit
- **Config/secrets** → move into `$ROXY_ROOT/etc` (never Git)
- **Runtime data** → move into `$ROXY_ROOT/var` (never Git)

Create a manifest that maps each path to its target zone.

## Phase 2 — Systemd Rewire
- Update unit files to reference:
  - `WorkingDirectory=$ROXY_ROOT/src`
  - `EnvironmentFile=$ROXY_ROOT/etc/roxy.env`
  - runtime paths in `$ROXY_ROOT/var`

Reload + restart:
```
systemctl --user daemon-reload
systemctl --user restart roxy-core
```

## Phase 3 — Verification Gates
- `stack_doctor.sh` passes
- `/ready` true
- Orchestrator health 200
- Postgres backend = postgres

## Phase 4 — Retire legacy roots
- Replace `/opt/roxy` with a symlink to `$ROXY_ROOT/src` **only after** verification
- Archive `/home/mark/roxy` if legacy

## Notes
- **No rollback** unless verification gates fail and root cause is identified.
- Prefer **build‑forward**: move and rewire, do not rewrite history.

