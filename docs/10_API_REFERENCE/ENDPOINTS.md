# ROXY API Endpoints

**Base URL:** `http://127.0.0.1:8766`
**Version Prefix:** All endpoints available with `/v1/` prefix
**Last Updated:** 2026-03-20

---

## Authentication

All endpoints require the `X-ROXY-Token` header:

```bash
TOKEN=$(cat ~/.roxy/secret.token)
curl -H "X-ROXY-Token: $TOKEN" http://127.0.0.1:8766/health
```

---

## Health & Status

### GET /health

Service liveness check. Always returns HTTP 200 if service is running.

**Request:**
```bash
curl http://127.0.0.1:8766/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-03-20T12:00:00.000Z",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

---

### GET /qualification/status

Production readiness status from qualification pipeline.

**Request:**
```bash
curl http://127.0.0.1:8766/qualification/status
```

**Response:**
```json
{
  "qualified": true,
  "score": 1.0,
  "gates": {
    "security": {"passed": true, "score": 1.0},
    "evaluation": {"passed": true, "score": 1.0, "tests": "48/48"},
    "authorization": {"passed": true, "score": 1.0},
    "readiness": {"passed": true, "score": 1.0},
    "capability": {"passed": true, "score": 1.0}
  },
  "timestamp": "2026-03-20T12:00:00.000Z"
}
```

---

### POST /qualification/run

Execute the full qualification pipeline.

**Request:**
```bash
curl -X POST http://127.0.0.1:8766/qualification/run
```

**Response:**
```json
{
  "qualified": true,
  "score": 1.0,
  "gates": {...},
  "duration_ms": 5234,
  "artifact_path": "~/.roxy/data/qualification/latest.json"
}
```

---

## Streaming

### GET /stream

Server-Sent Events (SSE) endpoint for streaming prompts.

**Request:**
```bash
curl -N -H "X-ROXY-Token: $TOKEN" \
  "http://127.0.0.1:8766/stream?prompt=hello"
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The prompt to process |
| `session_id` | string | No | Session identifier |
| `temperature` | float | No | Model temperature (0-1) |
| `max_tokens` | int | No | Maximum response tokens |

**Response:** SSE stream

```
event: token
data: {"content": "Hello"}

event: token
data: {"content": " there"}

event: done
data: {"total_tokens": 50}
```

**Error Responses:**

| Code | Body | Cause |
|------|------|-------|
| 400 | `{"error": "Invalid request"}` | Missing prompt |
| 403 | `{"error": "Authentication required"}` | Invalid token |
| 429 | `{"error": "Rate limited"}` | Too many requests |

---

## Memory / RAG

### POST /memory/recall

Semantic search in the RAG brain.

**Request:**
```bash
curl -X POST http://127.0.0.1:8766/memory/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "how to use OBS control", "k": 5}'
```

**Body Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `k` | int | No | 5 | Number of results |
| `collection` | string | No | all | Filter by collection |
| `threshold` | float | No | 0.0 | Minimum similarity score |

**Response:**
```json
{
  "results": [
    {
      "content": "OBS WebSocket Control Guide...",
      "metadata": {
        "source": "OBS_CONTROL_GUIDE.md",
        "chunk_index": 0,
        "knowledge_type": "GUIDE"
      },
      "score": 0.92
    }
  ],
  "count": 5,
  "query_time_ms": 45
}
```

---

## Stories (SKOREQ)

### GET /stories

List all stories across all epics.

**Request:**
```bash
curl http://127.0.0.1:8766/stories
```

**Response:**
```json
{
  "stories": [
    {
      "id": "EXTRACT-001",
      "title": "Create unified chat log parser",
      "priority": "critical",
      "status": "done",
      "epic_id": "ROXY-CHAT-EXTRACTION-V1"
    }
  ],
  "count": 6
}
```

---

### GET /stories/next

Get the next recommended story to work on.

**Request:**
```bash
curl http://127.0.0.1:8766/stories/next
```

**Response:**
```json
{
  "story": {
    "id": "EXTRACT-006",
    "title": "Launch on Mac Studio and monitor",
    "description": "Deploy extraction pipeline...",
    "priority": "high",
    "status": "todo",
    "points": 3,
    "filesInScope": ["~/.roxy/mission_supervisor.py"],
    "acceptanceCriteria": [
      "Scripts synced to Mac Studio",
      "Full extraction run completed"
    ]
  },
  "epic_id": "ROXY-CHAT-EXTRACTION-V1",
  "readiness_score": 0.85
}
```

---

### GET /stories/status

Get status summary across all epics.

**Request:**
```bash
curl http://127.0.0.1:8766/stories/status
```

**Response:**
```json
{
  "total": 6,
  "by_status": {
    "todo": 1,
    "in_progress": 0,
    "done": 5,
    "blocked": 0
  },
  "by_priority": {
    "critical": 3,
    "high": 3,
    "medium": 0,
    "low": 0
  },
  "completion_percentage": 83.3,
  "epics": [
    {
      "id": "ROXY-CHAT-EXTRACTION-V1",
      "completion": 83.3
    }
  ]
}
```

---

## Missions

### GET /missions

List all missions from the ledger.

**Request:**
```bash
curl http://127.0.0.1:8766/missions
```

**Response:**
```json
{
  "missions": [
    {
      "mission_id": "m_abc123",
      "story_id": "EXTRACT-005",
      "status": "complete",
      "started_at": "2026-03-20T06:50:00Z",
      "completed_at": "2026-03-20T06:53:00Z",
      "duration_seconds": 180
    }
  ],
  "count": 5
}
```

---

### GET /missions/active

Get current active mission (if any).

**Request:**
```bash
curl http://127.0.0.1:8766/missions/active
```

**Response (active mission):**
```json
{
  "active": true,
  "mission": {
    "mission_id": "m_def456",
    "story_id": "EXTRACT-006",
    "status": "running",
    "started_at": "2026-03-20T12:00:00Z",
    "lease_expires_at": "2026-03-20T12:05:00Z"
  }
}
```

**Response (no active mission):**
```json
{
  "active": false,
  "mission": null
}
```

---

### POST /missions/run

Trigger immediate mission execution.

**Request:**
```bash
curl -X POST http://127.0.0.1:8766/missions/run \
  -H "Content-Type: application/json" \
  -d '{"story_id": "EXTRACT-006"}'
```

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `story_id` | string | No | Specific story to execute (defaults to /stories/next) |
| `force` | bool | No | Force execution even if another mission active |
| `dry_run` | bool | No | Simulate without executing |

**Response:**
```json
{
  "mission_id": "m_ghi789",
  "story_id": "EXTRACT-006",
  "status": "acquired",
  "lease_expires_at": "2026-03-20T12:05:00Z",
  "trace_path": "~/.roxy/data/mission_traces/m_ghi789.jsonl"
}
```

**Error Responses:**

| Code | Body | Cause |
|------|------|-------|
| 409 | `{"error": "Mission already active"}` | Another mission running |
| 404 | `{"error": "No stories available"}` | No todo stories |
| 503 | `{"error": "Not qualified"}` | Qualification failed |

---

## Error Codes

| HTTP | Code | Description |
|------|------|-------------|
| 400 | `BAD_REQUEST` | Invalid request format |
| 403 | `AUTH_REQUIRED` | Missing or invalid token |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Operation conflicts with current state |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service not ready |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/stream` | 10 req/min per IP |
| `/memory/recall` | 60 req/min per IP |
| `/missions/run` | 1 req/min |
| All others | 120 req/min per IP |

---

## Quick Reference

```
╔═══════════════════════════════════════════════════════════════╗
║                   API QUICK REFERENCE                         ║
╠═══════════════════════════════════════════════════════════════╣
║ Base URL:        http://127.0.0.1:8766                        ║
║ Auth Header:     X-ROXY-Token: $(cat ~/.roxy/secret.token)    ║
║                                                               ║
║ Health:          GET  /health                                 ║
║ Stream:          GET  /stream?prompt=...                      ║
║ Memory:          POST /memory/recall                          ║
║ Stories:         GET  /stories/next                           ║
║ Missions:        POST /missions/run                           ║
║ Qualification:   GET  /qualification/status                   ║
╚═══════════════════════════════════════════════════════════════╝
```

---

*All endpoints support both plain and /v1/ prefixed paths.*
