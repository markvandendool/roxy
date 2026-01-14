#!/usr/bin/env bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOGDIR=~/.roxy/evidence
MARKERS="$LOGDIR/gate3_repro_markers_${TS}.log"
mkdir -p ~/.roxy/pids "$LOGDIR"
ln -sf "$MARKERS" "$LOGDIR/gate3_repro_markers.log"
PROBE_LONG='{"command":"Write a substantial Python module (~1000 tokens) that defines a small neural network training loop (synthetic data), includes comments, type hints, and prints a short summary at the end about expected VRAM usage. Keep output long to force sustained GPU work."}'
OLLAMA_HOST=127.0.0.1
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_BASE="http://${OLLAMA_HOST}:${OLLAMA_PORT}"

# Baselines
PRE_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
PRE_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps | wc -l || true)
PRE_AMDERR=$(sudo journalctl -k --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|page fault|evict|vm_fault' | wc -l || true)

# VRAM baseline
for d in /sys/class/drm/card*/device/mem_info_vram_used 2>/dev/null; do
  echo "BASELINE VRAM $(basename $(dirname $d))=$(cat $d)" >> "$LOGDIR/vram_samples_${TS}.log" || true
done

# Mark start
echo "=== GATE3_REPRO_BACKGROUND_START $TS ===" >> "$MARKERS"
echo "PRE_AER=$PRE_AER PRE_DEVCD=$PRE_DEVCD PRE_AMDERR=$PRE_AMDERR" >> "$MARKERS"
echo "OLLAMA_BASE=$OLLAMA_BASE" >> "$MARKERS"

# Start ollama serve if none
STARTED_OLLAMA=no
if ! pgrep -af 'ollama serve' >/dev/null; then
  echo "Starting ollama serve..." >> "$MARKERS"
  nohup ollama serve &> "$LOGDIR/ollama_serve_${TS}.log" &
  OLLAMA_PID=$!
  echo $OLLAMA_PID > ~/.roxy/pids/ollama_serve.pid
  echo "OLLAMA_PID=$OLLAMA_PID" >> "$MARKERS"
  STARTED_OLLAMA=yes
else
  echo "ollama serve already running" >> "$MARKERS"
fi
READY=0
for i in $(seq 1 30); do
  if curl -fsS "$OLLAMA_BASE/api/tags" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done
if [ "$READY" -ne 1 ]; then
  echo "ABORT: ollama not ready at $OLLAMA_BASE after 60s" >> "$MARKERS"
  exit 1
fi

# Run 60-minute repro: 15m initial, then continue to 60m if no aborts
END=$(( $(date +%s) + 60*60 ))
ABORT_REASON=""
while [ $(date +%s) -lt $END ]; do
  NOW=$(date -u +%Y%m%dT%H%M%SZ)
  # Send heavy request
  curl -sS -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" -H "Content-Type: application/json" -d "$PROBE_LONG" http://127.0.0.1:8766/run >> "$LOGDIR/gate3_repro_output_${TS}.log" 2>&1 || true
  # sample VRAM
  for d in /sys/class/drm/card*/device/mem_info_vram_used 2>/dev/null; do
    echo "$NOW $(basename $(dirname $d)) VRAM_USED=$(cat $d)" >> "$LOGDIR/vram_samples_${TS}.log" || true
  done
  # sample pm_info
  if [ -r /sys/kernel/debug/dri/0/amdgpu_pm_info ]; then
    head -n 40 /sys/kernel/debug/dri/0/amdgpu_pm_info >> "$LOGDIR/pm_info_samples_${TS}.log" 2>/dev/null || true
  fi
  # windowed kernel checks last 30s
  AER_NOW=$(sudo journalctl -k --since '30 seconds ago' --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
  DEVCD_NOW=$(ls -1 /var/lib/amdgpu-devcoredumps | wc -l || true)
  AMDERR_NOW=$(sudo journalctl -k --since '30 seconds ago' --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|page fault|evict|vm_fault' | wc -l || true)
  echo "$NOW SAMPLE AER+$AER_NOW DEVCD+$DEVCD_NOW AMDERR+$AMDERR_NOW" >> "$LOGDIR/gate3_repro_samples_${TS}.log"
  if [ "$AER_NOW" -gt 0 ]; then ABORT_REASON="AER_IN_WINDOW"; break; fi
  if [ "$DEVCD_NOW" -gt "$PRE_DEVCD" ]; then ABORT_REASON="DEVCDUMP_INCREASE"; break; fi
  if [ "$AMDERR_NOW" -gt 0 ]; then ABORT_REASON="AMDGPU_ERR_IN_WINDOW"; break; fi
  sleep 2
done

# If aborted, snapshot
if [ -n "$ABORT_REASON" ]; then
  echo "ABORT: $ABORT_REASON" >> "$MARKERS"
  sudo journalctl -k --since '5 minutes ago' -n 200 > "$LOGDIR/gate3_repro_abort_journal_${TS}.log" || true
  ls -lt /var/lib/amdgpu-devcoredumps | head -n 20 > "$LOGDIR/gate3_repro_abort_devcd_${TS}.log" || true
  VERDICT="ABORT"
else
  VERDICT="CLEAN"
fi

# stop ollama if we started it
if [ "$STARTED_OLLAMA" = "yes" ] && [ -f ~/.roxy/pids/ollama_serve.pid ]; then
  pid=$(cat ~/.roxy/pids/ollama_serve.pid)
  if ps -p $pid > /dev/null 2>&1; then
    kill $pid || true
  fi
  rm -f ~/.roxy/pids/ollama_serve.pid
fi

# final numbers
FINAL_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
FINAL_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps | wc -l || true)
FINAL_AMDERR=$(sudo journalctl -k --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|page fault|evict|vm_fault' | wc -l || true)
MAX_VRAM=$(awk -F'VRAM_USED=' 'NF==2 {print $2}' "$LOGDIR/vram_samples_${TS}.log" 2>/dev/null | sort -n | tail -n1 || true)
LAST40="$LOGDIR/gate3_repro_last40_kernel_${TS}.log"
sudo journalctl -k -n 2000 --no-pager \
  | egrep -i 'amdgpu|AER|BadTLP|pcie|fault|hang|evict|timeout|vm_fault|page fault' \
  | tail -n 40 > "$LAST40" || true

echo "VERDICT=$VERDICT" >> "$MARKERS"
echo "AER_DELTA=${PRE_AER} -> ${FINAL_AER}" >> "$MARKERS"
echo "DEVCD_DELTA=${PRE_DEVCD} -> ${FINAL_DEVCD}" >> "$MARKERS"
echo "AMDERR_DELTA=${PRE_AMDERR} -> ${FINAL_AMDERR}" >> "$MARKERS"
echo "MAX_VRAM_OBSERVED=$MAX_VRAM" >> "$MARKERS"
echo "LAST40_KERNEL=$LAST40" >> "$MARKERS"

echo "Gate3 repro finished at $(date -u +%Y%m%dT%H%M%SZ)" >> "$MARKERS"