#!/usr/bin/env bash
set -euo pipefail

export ROXY_TIMEOUT_SHORT=5 ROXY_TIMEOUT=12 ROXY_TIMEOUT_LONG=45
cget(){ curl -fsS --max-time "$ROXY_TIMEOUT" "$@"; }
cget5(){ curl -fsS --max-time "$ROXY_TIMEOUT_SHORT" "$@"; }
cget45(){ curl -fsS --max-time "$ROXY_TIMEOUT_LONG" "$@"; }

t(){ timeout "$ROXY_TIMEOUT" bash -lc "$*"; }
t5(){ timeout "$ROXY_TIMEOUT_SHORT" bash -lc "$*"; }
t45(){ timeout "$ROXY_TIMEOUT_LONG" bash -lc "$*"; }

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
BASE="/tmp/roxy_forensics/$RUN_ID"
mkdir -p "$BASE"

echo "RUN_ID=$RUN_ID" > "$BASE/proof_env.txt"

token_file="$HOME/.roxy/secret.token"
if [[ ! -f "$token_file" ]]; then
  echo "Missing token at $token_file" >&2
  exit 1
fi
TOKEN=$(cat "$token_file")

# A) Run path
run_payload='{"command":"Explain in two sentences why the sky is blue."}'
run_code=$(curl -sS --max-time "$ROXY_TIMEOUT_LONG" \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/run_response.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/run \
  -d "$run_payload")

# B) Logs + actions
logs_code=$(curl -sS --max-time "$ROXY_TIMEOUT" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/logs_response.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/logs)

actions_code=$(curl -sS --max-time "$ROXY_TIMEOUT" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/actions_response.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/actions)

# C) Memory persist test
memory_phrase="ROXY_MEMORY_TEST_${RUN_ID}"
remember_payload=$(printf '{"command":"Remember this phrase exactly: %s"}' "$memory_phrase")
remember_code=$(curl -sS --max-time "$ROXY_TIMEOUT_LONG" \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/remember_response.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/run \
  -d "$remember_payload")

# Restart roxy-core
restart_start=$(date +%s)
restart_code=$(timeout 45s systemctl --user restart roxy-core >/dev/null 2>&1; echo $?)

# Wait for health (retry)
health_code="000"
ready_seconds=""
for _ in {1..10}; do
  health_code=$(curl -sS --max-time "$ROXY_TIMEOUT" \
    -H "X-ROXY-Token: $TOKEN" \
    -o "$BASE/health_response.json" \
    -w "%{http_code}" \
    http://127.0.0.1:9136/api/roxy/status || true)
  if [[ "$health_code" == "200" ]]; then
    now=$(date +%s)
    ready_seconds=$((now - restart_start))
    break
  fi
  sleep 0.5
done

recall_payload=$(printf '{"query":"Remember this phrase exactly: %s", "k": 20}' "$memory_phrase")
recall_code=$(curl -sS --max-time "$ROXY_TIMEOUT_LONG" \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/recall_response.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/memory/recall \
  -d "$recall_payload")

# D) Feedback
feedback_payload=$(printf '{"query":"%s","response":"ok","type":"thumbs_up"}' "$memory_phrase")
feedback_code=$(curl -sS --max-time "$ROXY_TIMEOUT" \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/feedback_response.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/feedback \
  -d "$feedback_payload")

feedback_stats_code=$(curl -sS --max-time "$ROXY_TIMEOUT" \
  -H "X-ROXY-Token: $TOKEN" \
  -o "$BASE/feedback_stats.json" \
  -w "%{http_code}" \
  http://127.0.0.1:9136/api/roxy/feedback/stats)

python3 - <<PY
import json, pathlib
base = pathlib.Path("$BASE")

def load_json(name):
    p = base / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return p.read_text()

run_resp = load_json('run_response.json')
recall_resp = load_json('recall_response.json')
feedback_resp = load_json('feedback_response.json')

memory_phrase = "$memory_phrase"
recall_text = json.dumps(recall_resp) if recall_resp is not None else ""
found_phrase = memory_phrase in recall_text
model_used = None
gpu_lane = None
selected_model = None
if isinstance(run_resp, dict):
    meta = run_resp.get("metadata", {}) if isinstance(run_resp.get("metadata"), dict) else {}
    model_used = meta.get("model_used")
    selected_model = meta.get("selected_model")
    gpu_lane = meta.get("gpu_lane")

proof = {
    "run_id": "$RUN_ID",
    "run_code": int("$run_code"),
    "logs_code": int("$logs_code"),
    "actions_code": int("$actions_code"),
    "remember_code": int("$remember_code"),
    "restart_code": int("$restart_code"),
    "health_code": int("$health_code"),
    "ready_seconds": int("$ready_seconds") if "$ready_seconds" else None,
    "recall_code": int("$recall_code"),
    "feedback_code": int("$feedback_code"),
    "feedback_stats_code": int("$feedback_stats_code"),
    "memory_phrase": memory_phrase,
    "memory_phrase_found": found_phrase,
    "model_used": model_used,
    "selected_model": selected_model,
    "gpu_lane": gpu_lane,
    "run_result": run_resp,
    "feedback_result": feedback_resp,
}

(base / 'proof.json').write_text(json.dumps(proof, indent=2))
print(json.dumps(proof, indent=2))
PY

# Manifest
(
  cd "$BASE"
  find . -type f ! -name 'MANIFEST.sha256' -print0 | xargs -0 sha256sum
) > "$BASE/MANIFEST.sha256"

echo "Proof artifacts written to $BASE"
