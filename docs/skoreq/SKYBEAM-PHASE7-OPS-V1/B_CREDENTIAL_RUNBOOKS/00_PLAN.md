# SKOREQ PLAN: Credential Onboarding Runbooks (Phase 7B)

**Epic ID:** SKYBEAM-PHASE7-OPS-002
**Status:** PLAN MODE (NOT EXECUTABLE)
**Created:** 2026-01-10
**Story Points:** 3

---

## Problem Statement

Phase 6 publishers (YouTube, TikTok) operate in dry-run mode without credentials. Operators need step-by-step instructions to:
- Create OAuth apps on each platform
- Generate and store tokens securely
- Validate credentials before enabling live publishing
- Rotate credentials when they expire

No documentation currently exists for this workflow.

## User-Facing Outcome

Two markdown runbooks that guide operators from zero to working credentials:
- `RUNBOOK_YOUTUBE_OAUTH.md` - Google Cloud Console → OAuth → token.json
- `RUNBOOK_TIKTOK_API.md` - TikTok Developer Portal → Client credentials

Each runbook includes screenshots paths, validation commands, and troubleshooting.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Platform docs | External (YouTube/TikTok API docs) | Reference only |
| Existing publisher code | `youtube_publisher.py`, `tiktok_publisher.py` | Yes |

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| YouTube runbook | Markdown | `~/.roxy/docs/runbooks/RUNBOOK_YOUTUBE_OAUTH.md` |
| TikTok runbook | Markdown | `~/.roxy/docs/runbooks/RUNBOOK_TIKTOK_API.md` |
| Validation script | Python | `~/.roxy/bin/validate_credentials.py` |

## Invariants

1. Runbooks do not contain actual secrets
2. All paths reference `~/.roxy/` structure
3. Validation script returns 0 if all creds valid, 1 otherwise
4. Runbooks work for fresh installs (no assumed state)
5. Each runbook is self-contained (no cross-references required)

## Failure Modes

| Failure | Behavior |
|---------|----------|
| Platform UI changes | Note "last verified" date, update when detected |
| Token expired | Validation script detects and reports |
| Missing scopes | Validation script lists required scopes |

## Acceptance Gates

- [ ] YouTube runbook covers: project creation, OAuth consent, credential download, token generation
- [ ] TikTok runbook covers: app registration, sandbox testing, production approval
- [ ] Validation script checks both platforms
- [ ] Runbooks tested on clean Ubuntu 24.04
- [ ] No actual API calls made during runbook (until validation step)

## Deliverables

| Deliverable | Path |
|-------------|------|
| YouTube runbook | `~/.roxy/docs/runbooks/RUNBOOK_YOUTUBE_OAUTH.md` |
| TikTok runbook | `~/.roxy/docs/runbooks/RUNBOOK_TIKTOK_API.md` |
| Credential validator | `~/.roxy/bin/validate_credentials.py` |

## Rollout Plan

1. Create `~/.roxy/docs/runbooks/` directory
2. Write YouTube runbook with placeholder screenshot paths
3. Write TikTok runbook
4. Create validation script
5. Test validation against dry-run mode

## Non-Goals (v1)

- Automated credential rotation
- GUI for credential management
- Multi-account support
- Encrypted credential storage (rely on filesystem permissions)

## Future (v2+)

- Credential rotation reminders via health gate
- Integration with secret managers (1Password CLI, etc.)
- Automated OAuth refresh token handling

## Dependencies

- Phase 6 publishers must define expected credential paths
- Google Cloud Console access for YouTube
- TikTok Developer Portal access

## Stories

### STORY-028: YouTube OAuth Runbook

**Points:** 2
**Priority:** P2

**Problem:** No documentation for YouTube credential setup.

**Scope:** Step-by-step markdown guide from Google Cloud Console to working OAuth token.

**Files in Scope:**
- `~/.roxy/docs/runbooks/RUNBOOK_YOUTUBE_OAUTH.md` (new)

**Acceptance Criteria:**
1. Covers Google Cloud project creation
2. Covers OAuth consent screen setup
3. Covers credential download and placement
4. Covers token generation via `google-auth-oauthlib`
5. Includes validation command

**Dependencies:** STORY-023 (YouTube Publisher)

---

### STORY-029: TikTok API Runbook

**Points:** 1
**Priority:** P2

**Problem:** No documentation for TikTok credential setup.

**Scope:** Step-by-step markdown guide for TikTok Developer Portal setup.

**Files in Scope:**
- `~/.roxy/docs/runbooks/RUNBOOK_TIKTOK_API.md` (new)
- `~/.roxy/bin/validate_credentials.py` (new)

**Acceptance Criteria:**
1. Covers TikTok app registration
2. Covers sandbox vs production modes
3. Covers credential file format
4. Validation script checks both platforms
5. Includes troubleshooting section

**Dependencies:** STORY-024 (TikTok Publisher)

---

*End of Plan B*
