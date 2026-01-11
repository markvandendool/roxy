# SKOREQ PLAN: Seed Injector CLI (Phase 7C)

**Epic ID:** SKYBEAM-PHASE7-OPS-003
**Status:** PLAN MODE (NOT EXECUTABLE)
**Created:** 2026-01-10
**Story Points:** 5

---

## Problem Statement

The SKYBEAM pipeline currently relies on automated seed discovery (Phase 1-2). Operators cannot manually inject a specific viral video URL for immediate processing. Use cases:
- Breaking news requires immediate clip creation
- Testing pipeline with known-good source
- Re-processing a video after fix deployment
- Partner requests specific content prioritization

Manual injection requires creating JSON files in the correct format and location - error-prone and undocumented.

## User-Facing Outcome

A CLI command that accepts a video URL and injects it into the pipeline:

```bash
skybeam inject "https://youtube.com/watch?v=VIDEO_ID" --priority high
```

The injected seed appears in Phase 1 output and flows through the pipeline normally.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Video URL | CLI argument | Yes |
| Priority | CLI flag (--priority low/normal/high) | No (default: normal) |
| Tags | CLI flag (--tags "tag1,tag2") | No |
| Source label | CLI flag (--source "manual") | No (default: "cli_inject") |

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Seed file | JSON | `~/.roxy/services/phase1_seed_curator/seeds/manual/` |
| Confirmation | Text | stdout |
| Seed ID | Text | stdout (for tracking) |

## Invariants

1. Injected seeds use same schema as automated seeds
2. Duplicate URL detection prevents re-injection within 24h
3. Seed ID follows existing format: `SEED_YYYYMMDD_HHMMSS_xxxxxxxx`
4. Priority affects processing order but not schema
5. Command is idempotent (same URL → same seed ID)

## Failure Modes

| Failure | Behavior |
|---------|----------|
| Invalid URL format | Print error, exit 1, no file written |
| URL already injected | Print existing seed ID, exit 0 |
| Seed directory missing | Create directory, then write |
| Disk full | Print error, exit 1 |
| URL unreachable | Warning only (network check optional) |

## Acceptance Gates

- [ ] `skybeam inject <url>` creates valid seed file
- [ ] Duplicate detection works within 24h window
- [ ] `--priority` flag sets priority field
- [ ] `--tags` flag adds tags array
- [ ] `--dry-run` shows what would be created without writing
- [ ] Selftest covers all flags and error paths
- [ ] Injected seeds are picked up by Phase 1 on next run

## Deliverables

| Deliverable | Path |
|-------------|------|
| CLI extension | `~/.roxy/bin/skybeam` (add `inject` subcommand) |
| Selftest | `~/.roxy/bin/selftest_skybeam_inject.py` |
| Manual seed directory | `~/.roxy/services/phase1_seed_curator/seeds/manual/` |

## Rollout Plan

1. Extend `skybeam` CLI with `inject` subcommand
2. Create manual seed directory
3. Implement duplicate detection via hash index
4. Run selftest
5. Document in `skybeam --help`

## Non-Goals (v1)

- Batch injection from file
- URL validation via network fetch
- Direct NATS publishing (use file-based handoff)
- Scheduling injection for future time
- Webhook trigger for injection

## Future (v2+)

- `skybeam inject --from-file seeds.txt` - batch mode
- `skybeam inject --verify` - fetch URL metadata before injection
- Integration with `skybeam status` to show pending manual seeds
- Slack/Discord bot integration for injection requests

## Dependencies

- Phase 1 seed curator must scan `seeds/manual/` directory
- `skybeam` CLI from Plan A must exist (or create minimal version)
- Seed schema from Phase 1 must be documented

## Open Assumptions

1. **Phase 1 scans manual directory**: Assumes seed curator checks `seeds/manual/` - needs verification or modification to Phase 1
2. **Seed schema location**: Assumes schema at `~/.roxy/services/phase1_seed_curator/schemas/seed.json` - needs verification
3. **Priority handling**: Assumes Phase 1 respects priority field - needs verification

## Stories

### STORY-030: Seed Injector Subcommand

**Points:** 3
**Priority:** P2

**Problem:** No way to manually inject seeds into pipeline.

**Scope:** Add `inject` subcommand to `skybeam` CLI that creates properly formatted seed files.

**Files in Scope:**
- `~/.roxy/bin/skybeam` (extend)
- `~/.roxy/bin/selftest_skybeam_inject.py` (new)

**Acceptance Criteria:**
1. `skybeam inject <url>` creates seed file
2. `--priority` sets priority field
3. `--tags` adds tags array
4. `--dry-run` previews without writing
5. Duplicate URLs detected and reported
6. Selftest passes

**Dependencies:** STORY-027 (Operator Console CLI)

---

### STORY-031: Phase 1 Manual Directory Integration

**Points:** 2
**Priority:** P2

**Problem:** Phase 1 may not scan manual seed directory.

**Scope:** Verify and if needed modify Phase 1 seed curator to include `seeds/manual/` in scan.

**Files in Scope:**
- `~/.roxy/services/phase1_seed_curator/seed_curator.py` (modify if needed)
- `~/.roxy/services/phase1_seed_curator/selftest_seed_curator.py` (extend if needed)

**Acceptance Criteria:**
1. Manual seeds are discovered by Phase 1
2. Manual seeds flow through pipeline normally
3. Selftest includes manual seed case
4. No regression in automated seed discovery

**Dependencies:** Phase 1 implementation

---

*End of Plan C*
