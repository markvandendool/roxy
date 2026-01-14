# ADR-004: Unified ROXY_ROOT with Code/Config/Runtime Separation

**Status:** Accepted
**Date:** 2026-01-14

## Context
ROXY has suffered repeated split-brain failures caused by mixed roots and mixed concerns:

- Code edits landing in one path while systemd runs another.
- Runtime data and secrets mixed into Git trees.
- "Move everything" efforts that collapse code, data, and config into a single tree, breaking reproducibility.

The team decision is to keep **everything under `.roxy`** as the umbrella root. Ops reality requires **rebuildable systems** if the SSD dies. These are compatible only if `.roxy` is an umbrella with **strict internal zones**.

## Decision
Adopt a **single root layout** with **strict separation of concerns**:

```
$ROXY_ROOT/
  src/   # Git-tracked code only (roxy.git)
  etc/   # Config + secrets (not Git)
  var/   # Runtime data/state (not Git)
  log/   # Logs (optional, not Git)
```

**Canonical rules:**

1. **Only `$ROXY_ROOT/src` is a Git repo.**
2. **`$ROXY_ROOT/etc` never enters Git** (secrets, env files, tokens).
3. **`$ROXY_ROOT/var` never enters Git** (RAG indexes, DB files, caches, recordings).
4. systemd **must reference `$ROXY_ROOT/src`** for code, and `$ROXY_ROOT/etc` for env files.

### Default root
- **Linux:** `/home/mark/.roxy`
- **Mac Studio:** `/Users/markvandendool/.roxy`

If a legacy `/opt/roxy` exists, it must be retired or symlinked to `$ROXY_ROOT/src` to prevent split-brain.

### Transitional reality (current state safety)
If the git repo still lives at `$ROXY_ROOT` (no `src/` yet), **do not move it ad‑hoc**. Use one of:

- Create a **symlink**: `$ROXY_ROOT/src -> $ROXY_ROOT` (temporary bridge), or
- Keep systemd pointing directly at the current repo root and **schedule a controlled migration**.

This prevents breaking running services while the new layout is rolled out.

## Consequences
**Positive:**
- SSD rebuild is deterministic and fast.
- Clean Git history, no secrets in repo.
- Runtime state is backed up independently and safely.

**Tradeoffs:**
- Requires explicit backup/restore of `etc/` and `var/`.
- Requires systemd unit alignment to the new layout.

## Implementation Guidance
**Systemd wiring:**

- `WorkingDirectory=$ROXY_ROOT/src`
- `EnvironmentFile=$ROXY_ROOT/etc/roxy.env`
- Runtime/data paths point to `$ROXY_ROOT/var` (explicitly in env or config).

**Backups:**
- Code: Git tags/commits.
- Config: encrypted backup of `$ROXY_ROOT/etc`.
- Runtime: backup of `$ROXY_ROOT/var`.

## Migration (Build-Forward, Non-Destructive)
1. Snapshot `/opt/roxy`, `/home/mark/.roxy`, `/var/lib/roxy`, `/etc/roxy`.
2. Inventory and classify files as code vs config vs runtime.
3. Move code into `$ROXY_ROOT/src` (Git), runtime into `$ROXY_ROOT/var`, config into `$ROXY_ROOT/etc`.
4. Update systemd units to reference `$ROXY_ROOT` paths.
5. Run doctor gates (see runbook).

## Compliance Gates
- `git -C $ROXY_ROOT/src status -sb` must be clean.
- No `.env` or secrets in Git history.
- `stack_doctor.sh` must pass with JSON output in automation mode.

## Alternatives Considered
- **Push everything into Git:** rejected due to secrets leakage, unbounded runtime churn, and non-reproducibility.
- **Split across /opt and /home:** rejected due to split-brain and drift.
