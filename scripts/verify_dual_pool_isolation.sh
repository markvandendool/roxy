#!/usr/bin/env bash
set -euo pipefail

vram() {
  for f in /sys/class/drm/card*/device/mem_info_vram_used; do
    card=$(echo "$f" | grep -oP 'card\d+')
    used=$(cat "$f" | awk '{printf "%.2f", $1/1024/1024/1024}')
    echo "$card:$used"
  done | tr '\n' ' '; echo
}

echo "=== BASELINE VRAM (GB) ==="
B0="$(vram)"; echo "$B0"

echo "=== W5700X pool request (:11434 GPU0) ==="
curl -sS -m 90 -X POST http://127.0.0.1:11434/api/generate \
  -d '{"model":"tinyllama-gpu0","prompt":"fast pool smoke test","stream":false,"options":{"num_predict":32}}' >/dev/null
F1="$(vram)"; echo "$F1"

echo "=== 6900 XT pool request (:11435 GPU1) ==="
curl -sS -m 120 -X POST http://127.0.0.1:11435/api/generate \
  -d '{"model":"qwen3:8b","prompt":"big pool smoke test","stream":false,"options":{"num_predict":32}}' >/dev/null
B1="$(vram)"; echo "$B1"

echo
echo "NOTE: Expect W5700X (port 11434) to increase GPU0/card0 and 6900XT (port 11435) to increase GPU1/card1."
echo "If both increase the same card consistently, service pinning/env is not being honored."
