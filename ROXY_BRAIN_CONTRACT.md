# ROXY Brain Contract

**Version:** 1.0.0
**Status:** Active

## Purpose

This document codifies the rules that keep ROXY grounded in reality. When ROXY answers questions, these rules ensure she doesn't hallucinate, confuse historical data with current state, or lose her identity.

## The TruthPacket Principle

**TruthPacket is the single source of truth for real-world state.**

The TruthPacket is generated from actual system calls at request time:
- `datetime.now()` for current time
- `socket.gethostname()` for hostname
- `git rev-parse HEAD` for repository state
- `os.getenv()` for environment

When TruthPacket says it's January 10, 2026 at 14:30:00, that IS the current time. Period.

## Prompt Architecture

Every ROXY prompt MUST follow this exact structure:

```
A) SYSTEM PROMPT (identity + hard rules)
   - Loaded from ROXY_IDENTITY.md
   - Contains personality, competencies, response guidelines
   - Includes session rules about TruthPacket authority

B) TRUTH PACKET (authoritative reality)
   - Generated fresh via generate_truth_packet()
   - Contains current date/time, hostname, git state
   - Marked as "AUTHORITATIVE - OVERRIDES ALL OTHER SOURCES"

C) USER QUERY
   - The actual question being asked
   - Delimited with clear markers

D) REFERENCE MATERIAL (optional, historical)
   - RAG context from ChromaDB
   - MUST be marked as "HISTORICAL - MAY BE STALE"
   - Dates in reference material are NOT current dates
```

## Time/Date Queries

Queries about current time MUST skip RAG entirely:
- "What time is it?" -> Skip RAG, use TruthPacket
- "What's today's date?" -> Skip RAG, use TruthPacket
- "Is it Monday?" -> Skip RAG, use TruthPacket

The `is_time_date_query()` classifier detects these patterns and bypasses RAG to prevent confusion.

## Identity Preservation

ROXY must always know:
- She is ROXY (Robust Operations eXpert for Your systems)
- She was created by Mark for MindSong operations
- She is left-brain focused (operations, systems, coding)
- Her personality is warm, witty, efficient (like JARVIS)

Identity is loaded from `ROXY_IDENTITY.md` at the start of every prompt.

## Verification

The `gateBRAIN.sh` script verifies brain integrity:
1. TruthPacket generates correctly
2. Identity document loads
3. Time/date classifier works
4. Time queries return current (not historical) dates

Run regularly:
```bash
~/.roxy/scripts/gateBRAIN.sh
```

## Failure Modes to Prevent

1. **RAG Poisoning**: Historical dates in indexed docs confusing time answers
   - Solution: Time queries skip RAG; TruthPacket comes before RAG context

2. **Identity Drift**: ROXY forgetting who she is
   - Solution: Identity loaded from canonical ROXY_IDENTITY.md

3. **Hallucinated Facts**: Making up specific details
   - Solution: Hard rule to acknowledge uncertainty; prefer "I'm not sure"

4. **Stale State**: Using cached/old data for current state
   - Solution: TruthPacket generated fresh each request

## Files Involved

| File | Purpose |
|------|---------|
| `truth_packet.py` | TruthPacket generation, identity loading |
| `ROXY_IDENTITY.md` | Canonical identity document |
| `streaming.py` | Prompt construction with correct ordering |
| `roxy_core.py` | Time/date classifier integration |
| `scripts/gateBRAIN.sh` | Verification script |
| `ROXY_BRAIN_CONTRACT.md` | This document |

## Change Log

- **1.0.0** (2026-01-10): Initial brain contract established
  - TruthPacket pattern implemented
  - Prompt ordering codified
  - Time/date classifier added
  - gateBRAIN.sh verification script created

---

*This contract is binding. Any code that constructs prompts for ROXY MUST follow this architecture.*
