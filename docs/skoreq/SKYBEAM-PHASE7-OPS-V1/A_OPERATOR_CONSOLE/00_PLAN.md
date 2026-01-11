# SKOREQ PLAN: SKYBEAM Operator Console (Phase 7A)

**Epic ID:** SKYBEAM-PHASE7-OPS-001
**Status:** PLAN MODE (NOT EXECUTABLE)
**Created:** 2026-01-10
**Story Points:** 5

---

## Problem Statement

Operators currently lack a single command to view SKYBEAM pipeline health. Checking status requires:
- Reading multiple JSON files in `~/.roxy/services/*/`
- Manually inspecting systemd timer states
- Cross-referencing heartbeat files across phases

This friction delays incident response and makes daily monitoring tedious.

## User-Facing Outcome

A single command `skybeam status` prints a compact dashboard showing:
- All 21 systemd timers with last-run and next-run times
- Health gate status (approved/warning/critical)
- Active alerts count
- Queue depth and stuck items
- Consecutive heartbeat count per phase

Operators can assess pipeline health in under 5 seconds.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Timer states | `systemctl --user list-timers` | Yes |
| Health gate | `~/.roxy/services/publish/health/health_latest.json` | Yes |
| Alerts | `~/.roxy/services/publish/health/alerts_latest.json` | Yes |
| Queue state | `~/.roxy/services/publish/queue/queue_latest.json` | Yes |
| Heartbeats | `~/.roxy/services/**/.*heartbeat*.json` | Optional |

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Console dashboard | ANSI-colored text | stdout |
| Machine-readable | JSON (--json flag) | stdout |

## Invariants

1. Command completes in < 2 seconds on local filesystem
2. Missing files produce degraded output, not errors
3. Exit code 0 if healthy, 1 if warnings, 2 if critical
4. No network calls required (local state only)
5. Works without Python venv active (uses shebang)

## Failure Modes

| Failure | Behavior |
|---------|----------|
| Health file missing | Show "UNKNOWN" status, exit 1 |
| Timer query fails | Show "systemd unavailable", exit 1 |
| Partial heartbeats | Show available, mark others "?" |
| Permission denied | Print error, exit 1 |

## Acceptance Gates

- [ ] `skybeam status` runs without arguments
- [ ] Dashboard fits in 80x24 terminal
- [ ] `--json` outputs valid JSON to stdout
- [ ] Exit codes match health state
- [ ] Selftest covers all display branches
- [ ] No external dependencies beyond Python stdlib

## Deliverables

| Deliverable | Path |
|-------------|------|
| CLI script | `~/.roxy/bin/skybeam` |
| Selftest | `~/.roxy/bin/selftest_skybeam.py` |
| Symlink setup | Add `~/.roxy/bin` to PATH instructions |

## Rollout Plan

1. Create `~/.roxy/bin/` directory
2. Write `skybeam` CLI with `status` subcommand
3. Run selftest
4. Add PATH instructions to README

## Non-Goals (v1)

- Remote monitoring / HTTP endpoint
- Historical trend graphs
- Push notifications
- Config file for thresholds
- Subcommands beyond `status`

## Future (v2+)

- `skybeam logs` - tail recent pipeline logs
- `skybeam restart <phase>` - restart specific phase timers
- `skybeam inject <url>` - manual seed injection (see Plan C)
- Web dashboard via localhost server

## Dependencies

- Phase 6 health gate outputs must exist
- systemd user timers must be running
- Python 3.8+ available at `/usr/bin/python3`

## Stories

### STORY-027: Operator Console CLI

**Points:** 5
**Priority:** P2

**Problem:** No unified status view exists.

**Scope:** Create `skybeam status` command that aggregates timer states, health gate, alerts, and queue into compact dashboard.

**Files in Scope:**
- `~/.roxy/bin/skybeam` (new)
- `~/.roxy/bin/selftest_skybeam.py` (new)

**Acceptance Criteria:**
1. `skybeam status` prints formatted dashboard
2. `skybeam status --json` outputs JSON
3. Exit code reflects health state
4. Selftest passes all branches
5. Works without venv activation

**Dependencies:** STORY-026 (Health Gate)

---

*End of Plan A*
