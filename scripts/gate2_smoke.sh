#!/usr/bin/env bash
# Gate2 HTTP Smoke Test - Pool Normalization Contract
# Always uses dry_run to avoid benchmark conflicts
set -euo pipefail

BASE="http://127.0.0.1:8766"
TOKEN="$(tr -d '\r\n' < "$HOME/.roxy/secret.token")"

echo "=== health ==="
curl -fsS "$BASE/health" >/dev/null && echo "OK"

echo "=== info pools ==="
INFO="$(curl -fsS "$BASE/info")"
echo "$INFO" | python3 -c "
import sys, json
d=json.load(sys.stdin)

ollama = d.get('ollama', {})
pools = ollama.get('pools', {})

# handle either top-level or nested placement
misconfigured = d.get('misconfigured', ollama.get('misconfigured'))
pool_invariants = d.get('pool_invariants', ollama.get('pool_invariants'))

print('pools=', sorted(pools.keys()))
print('misconfigured=', misconfigured)
print('pool_invariants=', pool_invariants)
"

echo "=== bench: BIG alias -> w5700x (dry_run) ==="
curl -fsS -X POST "$BASE/bench/run" \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -d '{"task":"gsm8k","model":"qwen2.5-coder:14b","pool":"BIG","num_fewshot":0,"limit":1,"dry_run":true}' \
| python3 -c "
import sys, json
d=json.load(sys.stdin)
print('pool_requested_raw=', d.get('pool_requested_raw'))
print('pool_requested_canonical=', d.get('pool_requested_canonical'))
print('pool_used=', d.get('pool_used'))
print('gpu_hint=', d.get('gpu_hint'))
"

echo "=== bench: FAST alias -> 6900xt (dry_run) ==="
curl -fsS -X POST "$BASE/bench/run" \
  -H "Content-Type: application/json" \
  -H "X-ROXY-Token: $TOKEN" \
  -d '{"task":"gsm8k","model":"qwen2.5-coder:14b","pool":"FAST","num_fewshot":0,"limit":1,"dry_run":true}' \
| python3 -c "
import sys, json
d=json.load(sys.stdin)
print('pool_requested_raw=', d.get('pool_requested_raw'))
print('pool_requested_canonical=', d.get('pool_requested_canonical'))
print('pool_used=', d.get('pool_used'))
print('gpu_hint=', d.get('gpu_hint'))
"

echo "=== github prs alias routing (expect 403 without token) ==="
code=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/github/prs" || true)
echo "HTTP $code (expected 403)"

echo ""
echo "GATE2_SMOKE_OK"
