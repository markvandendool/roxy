# ROXY 7-Day Hardening - Day 1 Baseline Report

**Date:** 2026-03-19
**Time:** 2026-03-19T14:47:51-06:00
**Status:** BASELINE LOCKED

---

## Executive Summary

Baseline evidence captured. All infrastructure healthy. One failing test identified: `memory_identity`.

**Root Cause:** Conflicting identity records in learned_preferences table:
- `name=Sarah` (confidence 0.98, updated 2026-03-19 00:04:52)
- `name=Mark` (confidence 0.98, updated 2026-03-18 23:56:21)

Sarah is newer, causing ROXY to pick Sarah over Mark.

---

## Infrastructure Status

### Health Check
```json
{"status": "ok", "service": "roxy-core", "timestamp": "2026-03-19T14:47:51.308982", "checks": {"auth_token": "ok", "rate_limiter": "ok", "chromadb": "ok", "ollama": {"ok": true, "base_url": "http://127.0.0.1:11435", "latency_ms": 8.61, "last_ok_ts": 1773953271, "last_error": null}, "infrastructure": {"initialized": true}, "infra_redis_cache": "ok", "infra_postgres_memory": "ok", "infra_expert_router": "ok", "infra_event_stream": "ok", "infra_feedback": "ok"}}
```

### Ready Check
- `/ready.ready`: `true`
- All components: OK

### Infrastructure Components
| Component | Status |
|-----------|--------|
| Redis Cache | ✅ OK (1.28M used) |
| Postgres Memory | ✅ OK (pgvector enabled) |
| Expert Router | ✅ OK (6 experts available) |
| Event Stream | ✅ OK (NATS connected) |
| Ollama 6900XT | ✅ OK (0.86ms latency) |
| Ollama W5700X | ✅ OK (0.97ms latency) |

---

## Eval Harness Results

### Overall Score
- **Total Tests:** 7
- **Passed:** 6
- **Failed:** 1
- **Pass Rate:** 85.7%
- **Meets Threshold (85%):** ✅ YES

### By Category
| Category | Pass Rate | Details |
|----------|-----------|---------|
| memory | 67% (2/3) | ❌ memory_identity failed |
| confidence | 100% (2/2) | ✅ All passed |
| quality | 100% (2/2) | ✅ All passed |

### Detailed Results
```
✅ [memory] memory_production
✅ [memory] memory_preferences
❌ [memory] memory_identity (FAILED)
✅ [confidence] confidence_known
✅ [confidence] confidence_unknown
✅ [quality] quality_technical
✅ [quality] quality_production
```

---

## Failing Test Analysis

### memory_identity

**Query:** "Who am I?"

**Expected:** Response contains "mark" (canonical name)

**Actual:** Response contains "Sarah" (from conflicting test data)

**Root Cause:**
```
category | preference | confidence | updated_at         
----------+------------+------------+----------------------------
 name     | Sarah      |       0.98 | 2026-03-19 00:04:52
 name     | Mark       |       0.98 | 2026-03-18 23:56:21
```

Both records have equal confidence (0.98). ROXY uses recency, picking Sarah.

**Solution Required:**
1. Add user_id isolation to prevent cross-user identity leakage
2. Clean conflicting legacy identity records for canonical user
3. Update eval harness to use canonical profile assertion (not hardcoded name)

---

## Available Models

```
"deepcoder:14b"
"deepseek-r1:14b"
"qwen3:14b"
"qwen2.5-coder:14b"
"wizard-math:7b"
"deepseek-coder:6.7b"
"phi:2.7b"
"qwen2.5:32b"
"llama3:8b"
```

---

## Active Services

```
roxy-core.service                 loaded active running ROXY Core
roxy-proxy.service               loaded active running ROXY Proxy
roxy-content-handler.service     loaded active running SKYBEAM Content Handler
roxy-panel-daemon.service        loaded active running ROXY Panel Feed Daemon
roxy-skybeam-worker.service      loaded active running SKYBEAM Worker
```

---

## Day 1 Pass Criteria

| Criteria | Status |
|----------|--------|
| Baseline evidence file exists | ✅ |
| Baseline evidence complete | ✅ |
| Failure mode documented | ✅ |
| Identity conflict evidence captured | ✅ |

---

## Next Steps (Day 2)

1. Add user_id isolation in memory retrieval
2. Clean conflicting identity records
3. Re-run eval harness 3 times
4. Verify memory_identity passes all 3 runs

---

## Evidence Files

- `/home/mark/.roxy/briefings/eval-baseline-2026-03-19.txt` - Eval output
- This file - Full baseline report

---

*Baseline locked. No mutations before evidence capture complete.*
*Day 1 complete.*
