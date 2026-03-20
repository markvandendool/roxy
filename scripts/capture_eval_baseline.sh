#!/usr/bin/env bash
set -euo pipefail

ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
OUT="${1:-$ROXY_ROOT/briefings/eval-baseline-$(date +%F).txt}"

mkdir -p "$(dirname "$OUT")"

{
  echo "ROXY BASELINE CAPTURE"
  echo "timestamp=$(date -Is)"
  echo
  echo "[service-status]"
  systemctl --user is-active roxy-core.service || true
  systemctl --user is-active ollama.service || true
  systemctl --user is-active ollama-fast.service || true
  echo
  echo "[health]"
  curl -s http://127.0.0.1:8766/health | jq .
  echo
  echo "[ready]"
  curl -s http://127.0.0.1:8766/ready | jq .
  echo
  echo "[infrastructure]"
  curl -s http://127.0.0.1:8766/infrastructure | jq .
  echo
  echo "[eval]"
  "$ROXY_ROOT/venv/bin/python" "$ROXY_ROOT/scripts/eval_harness.py"
} | tee "$OUT"

echo "WROTE=$OUT"
