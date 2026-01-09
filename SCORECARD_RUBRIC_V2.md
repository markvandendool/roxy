# ROXY SCORECARD RUBRIC v2.0
## Runtime Proof Requirements

**Created**: 2026-01-05
**Replaces**: Implicit "it exists" scoring

---

## Core Principle

**NO CREDIT for "exists" — ONLY CREDIT for "proven in runtime"**

---

## Service Integration Scoring

### OLD RULE (BROKEN - DO NOT USE)
```
Service Score = Container Running + Port Listening
```

### NEW RULE (ENFORCED)
```
Service Score = Import Proof + Init Proof + Roundtrip Proof
```

---

## Proof Requirements Per Service

### Redis Integration
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "import redis\|from redis" ~/.roxy/roxy_core.py` | Line number |
| Init | `grep "Redis(\|StrictRedis(" ~/.roxy/roxy_core.py` | Line number |
| Roundtrip | `curl localhost:8766/debug/redis-test` | `{"set": "ok", "get": "ok"}` |

**Score**: 0/3, 1/3, 2/3, or 3/3

### PostgreSQL Integration
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "import psycopg\|import asyncpg" ~/.roxy/roxy_core.py` | Line number |
| Init | `grep "connect(\|create_pool(" ~/.roxy/roxy_core.py` | Line number |
| Roundtrip | `curl localhost:8766/debug/postgres-test` | `{"query": "ok", "rows": N}` |

**Score**: 0/3, 1/3, 2/3, or 3/3

### NATS Integration
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "import nats\|from nats" ~/.roxy/roxy_core.py` | Line number |
| Init | `grep "nats.connect\|NATS(" ~/.roxy/roxy_core.py` | Line number |
| Roundtrip | `curl localhost:8766/debug/nats-test` | `{"publish": "ok", "subscribe": "ok"}` |

**Score**: 0/3, 1/3, 2/3, or 3/3

### ChromaDB Integration
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "import chromadb\|from chromadb" ~/.roxy/roxy_core.py` | Line number |
| Init | `grep "chromadb.HttpClient\|PersistentClient" ~/.roxy/roxy_core.py` | Line number |
| Roundtrip | `curl localhost:8766/debug/chroma-test` | `{"collections": N, "query": "ok"}` |

**Score**: 0/3, 1/3, 2/3, or 3/3

---

## Feature Scoring

### Rate Limiting
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "rate_limit\|RateLimiter\|TokenBucket" ~/.roxy/roxy_core.py` | Line number |
| Call Site | `grep "check_rate_limit\|rate_limiter\." ~/.roxy/roxy_core.py` | Line number |
| Runtime | Send 50 requests in 1 second | At least one `429 Too Many Requests` |

**Score**: 0/3, 1/3, 2/3, or 3/3

### Truth Gate
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "truth_gate\|TruthGate" ~/.roxy/roxy_core.py` | Line number |
| Call Site | `grep "validate_response\|truth_gate\." ~/.roxy/roxy_core.py` | Line number |
| Runtime | Ask "open Firefox for me" | Response acknowledges inability, no hallucination |

**Score**: 0/3, 1/3, 2/3, or 3/3

### OBS Control
| Checkpoint | Command | Required Output |
|------------|---------|-----------------|
| Import | `grep "obs_skill\|obs_controller\|obsws" ~/.roxy/roxy_core.py ~/.roxy/roxy_commands.py` | Line number |
| Call Site | `grep "run_script.*obs\|obs_skill" ~/.roxy/roxy_commands.py` | Line number |
| Runtime | `curl -X POST localhost:8766/run -d '{"command": "obs status"}'` | OBS status or "OBS not running" |

**Score**: 0/3, 1/3, 2/3, or 3/3

---

## Aggregate Scoring Formula

```
Total Score = Sum of all feature scores
Max Possible = Number of features × 3

Percentage = (Total Score / Max Possible) × 100
```

### Grade Thresholds
| Percentage | Grade | Meaning |
|------------|-------|---------|
| 90-100% | A | Production ready |
| 75-89% | B | Functional with gaps |
| 60-74% | C | Partial implementation |
| 40-59% | D | Scaffolding only |
| 0-39% | F | Claims unsubstantiated |

---

## Evidence Bundle Requirements

Every scorecard MUST include:

1. **`MANIFEST.txt`** - List of all evidence files with SHA256 hashes
2. **`grep_proofs.txt`** - Output of all grep commands
3. **`runtime_proofs.txt`** - Output of all curl/test commands
4. **`path_doctor.txt`** - Output of `roxy-path-doctor.sh`
5. **`timestamp.txt`** - ISO8601 timestamp of evidence collection

### Bundle Naming
```
~/.roxy/evidence/YYYYMMDD_HHMMSS_SCORECARD/
```

### Forbidden Practices
- Copying evidence from previous bundles without `REUSED_FROM: <path>` marker
- Claiming "integration" based on container status alone
- Inferring functionality from documentation without runtime proof
- Partial scores without explicit checkpoint failures noted

---

## Checklist for Auditors

Before submitting any scorecard:

- [ ] Ran `roxy-path-doctor.sh` and included output
- [ ] All grep proofs show actual line numbers
- [ ] All runtime proofs show actual API responses
- [ ] No "container up" claims without import+roundtrip proof
- [ ] Evidence bundle has MANIFEST.txt with hashes
- [ ] Timestamp is within 1 hour of submission

---

## Current State (2026-01-05)

| Feature | Import | Init | Roundtrip | Score |
|---------|--------|------|-----------|-------|
| Redis | NO | NO | NO | 0/3 |
| PostgreSQL | NO | NO | NO | 0/3 |
| NATS | NO | NO | NO | 0/3 |
| ChromaDB | YES | YES | YES | 3/3 |
| Rate Limiting | YES | YES | UNTESTED | 2/3 |
| Truth Gate | YES | YES | UNTESTED | 2/3 |
| OBS Control | YES | YES | Conditional | 2/3 |

**Total**: 9/21 = **43%** = Grade **D**

This is the honest score. The previous 49/50 (98%) was inflated by counting "container exists" as "integrated."
