# ROXY Config Freeze

- Captured: `2026-03-19T15:37:40.390893-06:00`
- Host: `macpro-linux`
- Platform: `Linux-6.18.2-1-t2-noble-x86_64-with-glibc2.39`
- Python: `3.12.3`
- Base URL: `http://127.0.0.1:8766`

## Service States
- `roxy-core.service`: `active`
- `ollama.service`: `inactive`
- `ollama-fast.service`: `inactive`
- `ollama-6900xt.service`: `inactive`
- `ollama-w5700x.service`: `inactive`

## Frozen Environment
- `ROXY_USER_ID`: `<unset>`
- `ROXY_DEFAULT_USER_ID`: `<unset>`
- `ROXY_CANONICAL_USER_ID`: `<unset>`
- `ROXY_MEMORY_RECALL_ITEMS`: `<unset>`
- `ROXY_MEMORY_RECALL_MIN_SCORE`: `<unset>`
- `ROXY_MEMORY_RECALL_MIN_SIMILARITY`: `<unset>`
- `ROXY_MEMORY_RECALL_MIN_LEXICAL`: `<unset>`
- `ROXY_MEMORY_CONTEXT_MAX_CHARS`: `<unset>`
- `ROXY_MEMORY_SNIPPET_CHARS`: `<unset>`
- `ROXY_REFLECTION_RETRY_THRESHOLD`: `<unset>`
- `ROXY_REFLECTION_MAX_RETRIES`: `<unset>`
- `ROXY_ENABLE_REFLECTION_RETRY`: `<unset>`
- `ROXY_EVAL_PASS_THRESHOLD`: `<unset>`
- `ROXY_ENABLE_AGENTIC_PIPELINE`: `<unset>`
- `ROXY_ENABLE_PROACTIVE_HINTS`: `<unset>`
- `ROXY_IDENTITY_ENFORCE_CANONICAL`: `<unset>`
- `ROXY_OLLAMA_6900XT_URL`: `http://127.0.0.1:11435`
- `ROXY_OLLAMA_W5700X_URL`: `http://127.0.0.1:11435`
- `OLLAMA_HOST`: `http://127.0.0.1:11435`
- `OLLAMA_BASE_URL`: `http://127.0.0.1:11435`
- `POSTGRES_HOST`: `127.0.0.1`
- `POSTGRES_PORT`: `5432`
- `POSTGRES_DB`: `roxy`
- `POSTGRES_USER`: `roxy`

## Health Snapshot
```json
{
  "checks": {
    "auth_token": "ok",
    "chromadb": "ok",
    "infra_event_stream": "ok",
    "infra_expert_router": "ok",
    "infra_feedback": "ok",
    "infra_postgres_memory": "ok",
    "infra_redis_cache": "ok",
    "infrastructure": {
      "initialized": true
    },
    "ollama": {
      "base_url": "http://127.0.0.1:11435",
      "last_error": null,
      "last_ok_ts": 1773956260,
      "latency_ms": 7.22,
      "ok": true
    },
    "rate_limiter": "ok"
  },
  "service": "roxy-core",
  "status": "ok",
  "timestamp": "2026-03-19T15:37:40.513852"
}
```

## Ready Snapshot
```json
{
  "checks": {
    "auth_token": {
      "ok": true
    },
    "http_server": {
      "ok": true
    },
    "memory_postgres": {
      "backend": "postgres",
      "details": {
        "backend": "postgres",
        "details": {
          "pgvector": true
        },
        "healthy": true
      },
      "ok": true
    },
    "ping_direct": {
      "ok": true
    },
    "pool_invariants": {
      "checked_at": "2026-03-19T15:37:40.563803",
      "ok": true,
      "pools": {
        "6900xt": {
          "error": null,
          "gpu": "6900XT",
          "latency_ms": 0.75,
          "port": 11435,
          "reachable": true,
          "service": "ollama-6900xt.service"
        },
        "w5700x": {
          "error": null,
          "gpu": "W5700X",
          "latency_ms": 0.74,
          "port": 11434,
          "reachable": true,
          "service": "ollama-w5700x.service"
        }
      },
      "warning": null
    },
    "roxy_commands_import": {
      "ok": true
    },
    "time_direct": {
      "ok": true
    }
  },
  "message": "Core command fast-paths available",
  "ollama_ok": true,
  "ready": true,
  "status": "ready",
  "timestamp": "2026-03-19T15:37:40.541281"
}
```

## Infrastructure Snapshot
```json
{
  "components": {
    "event_stream": {
      "connected": true,
      "details": {
        "server": "nats://localhost:4222"
      },
      "healthy": true,
      "jetstream": true
    },
    "expert_router": {
      "classifier_available": true,
      "details": {
        "available_count": 6
      },
      "experts_available": [
        "qwen2.5-coder:14b",
        "deepseek-coder:6.7b",
        "wizard-math:7b",
        "llama3:8b",
        "qwen2.5:32b",
        "phi:2.7b"
      ],
      "healthy": true
    },
    "feedback": {
      "healthy": true,
      "stats": {
        "corrections": 0,
        "thumbs_down": 0,
        "thumbs_up": 0,
        "total": 0
      }
    },
    "postgres_memory": {
      "backend": "postgres",
      "details": {
        "pgvector": true
      },
      "healthy": true
    },
    "redis_cache": {
      "backend": "redis",
      "details": {
        "used_memory": "1.29M",
        "vector_search": false
      },
      "healthy": true
    }
  },
  "initialized": true
}
```

## Qualification Commands
```bash
cd ~/.roxy
./scripts/capture_eval_baseline.sh
./venv/bin/python scripts/eval_harness.py
./venv/bin/python scripts/freeze_config_snapshot.py
```
