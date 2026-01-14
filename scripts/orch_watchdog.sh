#!/usr/bin/env bash
set -euo pipefail

resp=$(curl -sS --max-time 2 http://127.0.0.1:3847/api/metrics || true)
if [ -z "$resp" ]; then
  exit 0
fi

printf '%s' "$resp" | python3 - <<'PY'
import sys, json, time, datetime, os
raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)
last = data.get('lastUpdated')
if not last:
    sys.exit(0)
try:
    last_ts = datetime.datetime.fromisoformat(last.replace('Z', '+00:00')).timestamp()
except Exception:
    sys.exit(0)
age = time.time() - last_ts
if age > 90:
    os.system('systemctl --user restart luno-orchestrator.service')
PY
