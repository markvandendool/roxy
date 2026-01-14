# Breakroom Update — ROXY Root Architecture + Rebuild Runbook (2026-01-14)

Concise summary:
- Decision locked: `.roxy` is the umbrella root with strict internal zones:
  - `src/` = Git-tracked code only
  - `etc/` = config + secrets (not Git)
  - `var/` = runtime data/state (not Git)
- This resolves the "move everything to .roxy" vs "rebuildable system" conflict.
- Systemd must reference `ROXY_ROOT/src` for code and `ROXY_ROOT/etc` for env.
- Backups are now structured: Git tags (code), encrypted backups (etc), runtime backups (var).

New docs:
- ADR (architecture decision):
  - `/home/mark/.roxy/docs/docs/architecture/ADR-004-roxy-root-layout.md`
- Rebuild Runbook:
  - `/home/mark/.roxy/docs/runbooks/RUNBOOK_ROXY_REBUILD.md`

Related docs:
- `/home/mark/.roxy/docs/ROXY_RUNBOOK_CORE.md`
- `/home/mark/.roxy/docs/ROXY_RUNTIME_PORTS.md`
- `/home/mark/.roxy/docs/ROXY_DUAL_POOL_CONTRACT.md`
- `/home/mark/.roxy/docs/ROXY_STATUS_DOCTRINE.md`

Related operational tooling:
- Doctor command (truth gate):
  - `/home/mark/.roxy/scripts/stack_doctor.sh`
  - Automation: `--json --fast`

Next actions for teams:
- Align systemd units to ROXY_ROOT layout.
- Inventory and classify `/home/mark/.roxy` into src/etc/var zones.
- Stop any ad‑hoc edits in runtime paths that should be in Git.

Update (2026-01-14):
- Added env setup runbook for secrets (no Git):
  - `/home/mark/.roxy/docs/runbooks/RUNBOOK_ROXY_ENV_SETUP.md`
- Added transitional note in ADR-004: if repo still lives at $ROXY_ROOT, use a symlink or schedule a controlled migration.
- Git ops safety: ROXY git tooling now skips SSHFS unless `ROXY_GIT_REPO` is explicitly set.
