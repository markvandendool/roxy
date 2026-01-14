# ROXY ADR Index (Namespace)

**Status:** Active
**Last Updated:** 2026-01-14
**Purpose:** Provide a ROXY-only ADR index and prevent cross-repo numbering conflicts.

## Namespace Rule
ROXY ADR numbers are **repo-scoped**. Do **not** apply Juke Hub ADR numbers to ROXY. When referencing an ADR across repos, always include the full ROXY path.

## ROXY ADRs

| ADR | File | Topic |
| --- | ---- | ----- |
| ADR-001 | ADR-001-circle-of-fifths-consolidation.md | Circle of Fifths consolidation |
| ADR-002 | ADR-002-polar-coordinate-system.md | Polar coordinate system |
| ADR-003 | ADR-003-circle-collaboration.md | Circle collaboration |
| ADR-004 | ADR-004-roxy-root-layout.md | Unified ROXY_ROOT layout (src/etc/var/log) |

## Cross-Repo Citation Format (Required)
- ROXY: `/home/mark/.roxy/docs/docs/architecture/<ADR-FILE>.md`
- Juke Hub: `/home/mark/mindsong-juke-hub/docs/architecture/<ADR-FILE>.md`

## Notes
If ADR numbering collisions are confusing in cross-repo reports, prefix ROXY ADRs as `ROXY-ADR-###` when summarizing to humans.
