#!/usr/bin/env bash
set -euo pipefail

TS=$(date -u +%Y%m%dT%H%M%SZ)
LOGDIR="$HOME/.roxy/evidence"
MARKERS="$LOGDIR/gpu_force_markers_${TS}.log"
VRAMLOG="$LOGDIR/vram_samples_${TS}.log"
PMLOG="$LOGDIR/pm_info_samples_${TS}.log"
KERNLOG="$LOGDIR/kernel_window_${TS}.log"

mkdir -p "$LOGDIR" "$HOME/.roxy/pids"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ABORT: ollama not found in PATH" | tee -a "$MARKERS"
  exit 1
fi

OLLAMA_HOST=127.0.0.1
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_BASE="http://${OLLAMA_HOST}:${OLLAMA_PORT}"
MODEL="${OLLAMA_MODEL:-}"
FALLBACK_MODEL="${OLLAMA_FALLBACK_MODEL:-llama3.1:8b}"
NUM_PREDICT="${OLLAMA_NUM_PREDICT:-2048}"

# Baselines
PRE_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
PRE_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
PRE_AMDERR=$(sudo journalctl -k --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|page fault|evict|vm_fault' | wc -l || true)

echo "=== GPU_FORCE_START $TS ===" | tee -a "$MARKERS"
echo "OLLAMA_BASE=$OLLAMA_BASE" | tee -a "$MARKERS"
echo "PRE_AER=$PRE_AER PRE_DEVCD=$PRE_DEVCD PRE_AMDERR=$PRE_AMDERR" | tee -a "$MARKERS"

# Start ollama serve only if none
STARTED_OLLAMA=no
if ! pgrep -af 'ollama serve' >/dev/null 2>&1; then
  echo "Starting ollama serve..." | tee -a "$MARKERS"
  nohup ollama serve &> "$LOGDIR/ollama_serve_${TS}.log" &
  echo $! > "$HOME/.roxy/pids/ollama_serve.pid"
  STARTED_OLLAMA=yes
fi

# Wait for readiness (up to 60s)
READY=0
for i in $(seq 1 30); do
  if curl -fsS "$OLLAMA_BASE/api/tags" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done
if [ "$READY" -ne 1 ]; then
  echo "ABORT: ollama not ready at $OLLAMA_BASE after 60s" | tee -a "$MARKERS"
  exit 1
fi

echo "ollama ready" | tee -a "$MARKERS"

# Pick a model if not set
if [ -z "$MODEL" ]; then
  MODEL=$(ollama list 2>/dev/null | awk 'NR==2 {print $1}')
fi
if [ -z "$MODEL" ]; then
  MODEL="$FALLBACK_MODEL"
fi

NEED_PULL=0
if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$MODEL"; then
  NEED_PULL=1
fi
if [ "$NEED_PULL" -eq 1 ]; then
  echo "Model $MODEL not found locally; pulling..." | tee -a "$MARKERS"
  if ! ollama pull "$MODEL" >> "$MARKERS" 2>&1; then
    echo "ABORT: failed to pull model $MODEL" | tee -a "$MARKERS"
    exit 1
  fi
fi

echo "MODEL=$MODEL NUM_PREDICT=$NUM_PREDICT" | tee -a "$MARKERS"

PAYLOAD=$(cat <<JSON
{
  "model": "${MODEL}",
  "prompt": "Write a long Python module (>=2000 tokens) that implements: (1) a small neural net training loop with synthetic data, (2) dataclass-based config, (3) three unit tests, (4) detailed comments. Keep output long and continuous.",
  "stream": false,
  "keep_alive": "30m",
  "options": { "num_predict": ${NUM_PREDICT}, "temperature": 0.2 }
}
JSON
)

ABORT_REASON=""
MAX_VRAM=0
PHASE_MINUTES="${GPU_FORCE_MINUTES:-15}"
EXTEND_MINUTES="${GPU_FORCE_EXTEND_MINUTES:-45}"
REQ=0
ABORT_PHASE=""

echo "=== GPU_FORCE_RUN ${PHASE_MINUTES}m START $(date -u +%Y%m%dT%H%M%SZ) ===" | tee -a "$MARKERS"
END=$(( $(date +%s) + PHASE_MINUTES*60 ))
while [ "$(date +%s)" -lt "$END" ]; do
  REQ=$((REQ+1))
  STAMP=$(date -u +%Y%m%dT%H%M%SZ)
  echo "REQ#$REQ $STAMP" | tee -a "$MARKERS"

  curl -m 120 -sS -H "Content-Type: application/json" \
    -d "$PAYLOAD" "$OLLAMA_BASE/api/generate" \
    | head -c 200 >> "$MARKERS" || true
  echo "" >> "$MARKERS"

  # VRAM sample
  for d in /sys/class/drm/card*/device/mem_info_vram_used; do
    [ -e "$d" ] || continue
    v=$(cat "$d" 2>/dev/null || echo 0)
    echo "$STAMP $(basename "$(dirname "$d")") VRAM_USED=$v" >> "$VRAMLOG" || true
    if [[ "$v" =~ ^[0-9]+$ ]] && [ "$v" -gt "$MAX_VRAM" ]; then
      MAX_VRAM="$v"
    fi
  done

  # pm_info sample (best-effort)
  if [ -r /sys/kernel/debug/dri/0/amdgpu_pm_info ]; then
    echo "=== $STAMP ===" >> "$PMLOG"
    head -n 25 /sys/kernel/debug/dri/0/amdgpu_pm_info >> "$PMLOG" 2>/dev/null || true
  fi

  # windowed kernel check (last 20s)
  sudo journalctl -k --since '20 seconds ago' --no-pager \
    | egrep -i 'AER|BadTLP|amdgpu|GPU reset|ring.*timeout|vm_fault|evict|page fault' \
    >> "$KERNLOG" || true

  AER_WIN=$(sudo journalctl -k --since '20 seconds ago' --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
  AMD_WIN=$(sudo journalctl -k --since '20 seconds ago' --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|vm_fault|evict|page fault' | wc -l || true)
  DEVCD_NOW=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)

  if [ "$AER_WIN" -gt 0 ]; then ABORT_REASON="AER_IN_WINDOW"; break; fi
  if [ "$AMD_WIN" -gt 0 ]; then ABORT_REASON="AMDGPU_ERR_IN_WINDOW"; break; fi
  if [ "$DEVCD_NOW" -gt "$PRE_DEVCD" ]; then ABORT_REASON="DEVCDUMP_INCREASE"; break; fi

  sleep 5
done

if [ -z "$ABORT_REASON" ] && [ "$PHASE_MINUTES" -lt 60 ] && [ "$EXTEND_MINUTES" -gt 0 ]; then
  echo "=== GPU_FORCE_RUN EXTEND ${EXTEND_MINUTES}m START $(date -u +%Y%m%dT%H%M%SZ) ===" | tee -a "$MARKERS"
  END=$(( $(date +%s) + EXTEND_MINUTES*60 ))
  while [ "$(date +%s)" -lt "$END" ]; do
    REQ=$((REQ+1))
    STAMP=$(date -u +%Y%m%dT%H%M%SZ)
    echo "REQ#$REQ $STAMP" | tee -a "$MARKERS"

    curl -m 120 -sS -H "Content-Type: application/json" \
      -d "$PAYLOAD" "$OLLAMA_BASE/api/generate" \
      | head -c 200 >> "$MARKERS" || true
    echo "" >> "$MARKERS"

    for d in /sys/class/drm/card*/device/mem_info_vram_used; do
      [ -e "$d" ] || continue
      v=$(cat "$d" 2>/dev/null || echo 0)
      echo "$STAMP $(basename "$(dirname "$d")") VRAM_USED=$v" >> "$VRAMLOG" || true
      if [[ "$v" =~ ^[0-9]+$ ]] && [ "$v" -gt "$MAX_VRAM" ]; then
        MAX_VRAM="$v"
      fi
    done

    if [ -r /sys/kernel/debug/dri/0/amdgpu_pm_info ]; then
      echo "=== $STAMP ===" >> "$PMLOG"
      head -n 25 /sys/kernel/debug/dri/0/amdgpu_pm_info >> "$PMLOG" 2>/dev/null || true
    fi

    sudo journalctl -k --since '20 seconds ago' --no-pager \
      | egrep -i 'AER|BadTLP|amdgpu|GPU reset|ring.*timeout|vm_fault|evict|page fault' \
      >> "$KERNLOG" || true

    AER_WIN=$(sudo journalctl -k --since '20 seconds ago' --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
    AMD_WIN=$(sudo journalctl -k --since '20 seconds ago' --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|vm_fault|evict|page fault' | wc -l || true)
    DEVCD_NOW=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)

    if [ "$AER_WIN" -gt 0 ]; then ABORT_REASON="AER_IN_WINDOW"; ABORT_PHASE="EXTEND"; break; fi
    if [ "$AMD_WIN" -gt 0 ]; then ABORT_REASON="AMDGPU_ERR_IN_WINDOW"; ABORT_PHASE="EXTEND"; break; fi
    if [ "$DEVCD_NOW" -gt "$PRE_DEVCD" ]; then ABORT_REASON="DEVCDUMP_INCREASE"; ABORT_PHASE="EXTEND"; break; fi

    sleep 5
  done
fi

# Final counts
FINAL_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
FINAL_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
FINAL_AMDERR=$(sudo journalctl -k --no-pager | egrep -i 'amdgpu|GPU reset|ring.*timeout|page fault|evict|vm_fault' | wc -l || true)

VERDICT="CLEAN@${PHASE_MINUTES}M"
if [ -n "$ABORT_REASON" ]; then
  if [ -n "$ABORT_PHASE" ]; then
    VERDICT="ABORT@${ABORT_PHASE}:$ABORT_REASON"
  else
    VERDICT="ABORT@${PHASE_MINUTES}M:$ABORT_REASON"
  fi
elif [ "$EXTEND_MINUTES" -gt 0 ]; then
  VERDICT="CLEAN@$((PHASE_MINUTES + EXTEND_MINUTES))M"
fi

LAST40="$LOGDIR/gpu_force_last40_kernel_${TS}.log"
sudo journalctl -k -n 2000 --no-pager \
  | egrep -i 'amdgpu|AER|BadTLP|pcie|fault|hang|evict|timeout|vm_fault|page fault' \
  | tail -n 40 > "$LAST40" || true

# Stop ollama if we started it
if [ "$STARTED_OLLAMA" = "yes" ] && [ -f "$HOME/.roxy/pids/ollama_serve.pid" ]; then
  OPID=$(cat "$HOME/.roxy/pids/ollama_serve.pid" 2>/dev/null || true)
  if [ -n "$OPID" ]; then
    kill "$OPID" || true
  fi
  rm -f "$HOME/.roxy/pids/ollama_serve.pid"
fi

echo "--- GPU_FORCE DELIVERABLE ---" | tee -a "$MARKERS"
echo "VERDICT: $VERDICT" | tee -a "$MARKERS"
echo "AER delta: $PRE_AER -> $FINAL_AER (delta $((FINAL_AER-PRE_AER)))" | tee -a "$MARKERS"
echo "devcoredump delta: $PRE_DEVCD -> $FINAL_DEVCD (delta $((FINAL_DEVCD-PRE_DEVCD)))" | tee -a "$MARKERS"
echo "amdgpu err delta: $PRE_AMDERR -> $FINAL_AMDERR (delta $((FINAL_AMDERR-PRE_AMDERR)))" | tee -a "$MARKERS"
echo "MAX_VRAM: $MAX_VRAM" | tee -a "$MARKERS"
echo "Artifacts: $VRAMLOG $PMLOG $KERNLOG $LAST40" | tee -a "$MARKERS"

echo "DONE $(date -u +%Y%m%dT%H%M%SZ)" | tee -a "$MARKERS"
