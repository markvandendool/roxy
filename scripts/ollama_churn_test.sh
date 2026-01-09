#!/usr/bin/env bash
set -euo pipefail

TS=$(date -u +%Y%m%dT%H%M%SZ)
LOGDIR="$HOME/.roxy/evidence"
MARKERS="$LOGDIR/churn_markers_${TS}.log"
VRAMLOG="$LOGDIR/churn_vram_${TS}.log"
KERNLOG="$LOGDIR/churn_kernel_${TS}.log"
mkdir -p "$LOGDIR" "$HOME/.roxy/pids"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ABORT: ollama not found in PATH" | tee -a "$MARKERS"
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "ABORT: curl not found in PATH" | tee -a "$MARKERS"
  exit 1
fi

OLLAMA_HOST=127.0.0.1
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
BASE="${OLLAMA_BASE:-http://${OLLAMA_HOST}:${OLLAMA_PORT}}"
DUR_MINUTES="${DUR_MINUTES:-45}"
NUM_PREDICT="${OLLAMA_NUM_PREDICT:-2048}"
SLEEP_BETWEEN="${CHURN_SLEEP_SECONDS:-3}"
ALLOW_PULL="${ALLOW_PULL:-0}"

# Ensure ollama is up
PIDFILE="$HOME/.roxy/pids/ollama_serve.pid"
STARTED_OLLAMA=no
cleanup() {
  if [ "$STARTED_OLLAMA" = "yes" ] && [ -f "$PIDFILE" ]; then
    OPID=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$OPID" ]; then
      kill "$OPID" || true
    fi
    rm -f "$PIDFILE"
  fi
}
trap cleanup EXIT

if ! pgrep -af 'ollama serve' >/dev/null 2>&1; then
  nohup ollama serve &> "$LOGDIR/ollama_serve_${TS}.log" &
  echo $! > "$PIDFILE"
  STARTED_OLLAMA=yes
  echo "Started ollama serve pid=$(cat "$PIDFILE")" | tee -a "$MARKERS"
fi

# Wait for readiness (up to 60s)
READY=0
for i in $(seq 1 30); do
  if curl -fsS "$BASE/api/tags" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done
if [ "$READY" -ne 1 ]; then
  echo "ABORT: ollama not ready at $BASE after 60s" | tee -a "$MARKERS"
  exit 1
fi

# Pick two models
get_models_by_size() {
  ollama list 2>/dev/null | awk '
    NR==1 {next}
    {
      name=$1;
      size=$3;
      unit=$4;
      if (unit == "" && $3 ~ /[KMGTP]B$/) {
        unit=substr($3, length($3)-1);
        size=substr($3, 1, length($3)-2);
      }
      gsub(/[^0-9.]/, "", size);
      if (size == "") next;
      mult=0;
      if (unit == "KB") mult=1/1024;
      else if (unit == "MB") mult=1;
      else if (unit == "GB") mult=1024;
      else if (unit == "TB") mult=1024*1024;
      else mult=0;
      if (mult == 0) next;
      printf "%s\t%.6f\n", name, size*mult;
    }
  ' | sort -k2,2nr | awk 'NR<=2 {print $1}'
}

MODELS_ARR=()
if [ -n "${MODELS:-}" ]; then
  IFS=',' read -r -a MODELS_ARR <<< "$MODELS"
else
  mapfile -t MODELS_ARR < <(get_models_by_size)
fi
if [ "${#MODELS_ARR[@]}" -lt 2 ]; then
  mapfile -t MODELS_ARR < <(ollama list 2>/dev/null | awk 'NR>1 {print $1}' | head -n 2)
fi

M1="${MODELS_ARR[0]:-${CHURN_DEFAULT_1:-qwen2.5:32b}}"
M2="${MODELS_ARR[1]:-${CHURN_DEFAULT_2:-qwen2.5:14b}}"

if [ "$M1" = "$M2" ]; then
  echo "ABORT: need two distinct models; set MODELS=..." | tee -a "$MARKERS"
  exit 1
fi

echo "=== CHURN_START $TS ===" | tee -a "$MARKERS"
echo "BASE=$BASE M1=$M1 M2=$M2 DUR_MINUTES=$DUR_MINUTES" | tee -a "$MARKERS"

# Ensure models are present
ensure_model() {
  local model="$1"
  if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$model"; then
    if [ "$ALLOW_PULL" = "1" ]; then
      echo "Pulling model $model" | tee -a "$MARKERS"
      if ! ollama pull "$model" >> "$MARKERS" 2>&1; then
        echo "ABORT: failed to pull model $model" | tee -a "$MARKERS"
        exit 1
      fi
    else
      echo "ABORT: model $model not installed; set MODELS or ALLOW_PULL=1" | tee -a "$MARKERS"
      exit 1
    fi
  fi
}
ensure_model "$M1"
ensure_model "$M2"

# Baselines
PRE_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
PRE_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
PRE_AMDERR=$(sudo journalctl -k --no-pager | egrep -i 'GPU reset|ring.*timeout|vm_fault|VM fault|page fault|amdgpu.*hang|coredump|devcoredump' | wc -l || true)
echo "PRE_AER=$PRE_AER PRE_DEVCD=$PRE_DEVCD PRE_AMDERR=$PRE_AMDERR" | tee -a "$MARKERS"

ABORT_REASON=""
MAX_VRAM=0

PAYLOAD_TEMPLATE='{
  "model":"%s",
  "prompt":"Return a long code output (~1500-2500 tokens): implement a module + tests + comments. Keep output long and continuous.",
  "stream": false,
  "keep_alive": 0,
  "options": { "num_predict": %d, "temperature": 0.2 }
}'

END=$(( $(date +%s) + DUR_MINUTES*60 ))
ITER=0

while [ "$(date +%s)" -lt "$END" ]; do
  for M in "$M1" "$M2"; do
    ITER=$((ITER+1))
    STAMP=$(date -u +%Y%m%dT%H%M%SZ)
    echo "ITER#$ITER MODEL=$M $STAMP" | tee -a "$MARKERS"

    PAYLOAD=$(printf "$PAYLOAD_TEMPLATE" "$M" "$NUM_PREDICT")
    curl -m 90 -sS -H "Content-Type: application/json" \
      -d "$PAYLOAD" "$BASE/api/generate" \
      | head -c 160 >> "$MARKERS" || true
    echo "" >> "$MARKERS"

    for d in /sys/class/drm/card*/device/mem_info_vram_used; do
      [ -e "$d" ] || continue
      v=$(cat "$d" 2>/dev/null || echo 0)
      echo "$STAMP $(basename "$(dirname "$d")") VRAM_USED=$v" >> "$VRAMLOG" || true
      if [[ "$v" =~ ^[0-9]+$ ]] && [ "$v" -gt "$MAX_VRAM" ]; then
        MAX_VRAM="$v"
      fi
    done

    WIN="$(sudo journalctl -k --since '30 seconds ago' --no-pager || true)"
    printf '%s\n' "$WIN" | egrep -i 'amdgpu|workqueue' >> "$KERNLOG" || true

    AER_WIN=$(printf '%s\n' "$WIN" | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
    HARD_GPU_WIN=$(printf '%s\n' "$WIN" | egrep -i 'GPU reset|ring.*timeout|vm_fault|VM fault|page fault|amdgpu.*hang|coredump|devcoredump' | wc -l || true)
    DEVCD_NOW=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)

    if [ "$AER_WIN" -gt 0 ]; then ABORT_REASON="AER_IN_WINDOW"; break 2; fi
    if [ "$HARD_GPU_WIN" -gt 0 ]; then ABORT_REASON="HARD_GPU_FAULT_IN_WINDOW"; break 2; fi
    if [ "$DEVCD_NOW" -gt "$PRE_DEVCD" ]; then ABORT_REASON="DEVCDUMP_INCREASE"; break 2; fi

    sleep "$SLEEP_BETWEEN"
  done
done

# Final counts
FINAL_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
FINAL_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
FINAL_AMDERR=$(sudo journalctl -k --no-pager | egrep -i 'GPU reset|ring.*timeout|vm_fault|VM fault|page fault|amdgpu.*hang|coredump|devcoredump' | wc -l || true)

VERDICT="CLEAN@CHURN"
if [ -n "$ABORT_REASON" ]; then VERDICT="ABORT@CHURN:$ABORT_REASON"; fi

LAST40="$LOGDIR/churn_last40_kernel_${TS}.log"
sudo journalctl -k -n 2000 --no-pager \
  | egrep -i 'amdgpu|AER|BadTLP|pcie|fault|hang|evict|timeout|vm_fault|page fault|coredump|devcoredump' \
  | tail -n 40 > "$LAST40" || true

# Stop ollama if we started it
cleanup

QUEUE_EVICT_COUNT=$(grep -Eci 'queue evicted|Freeing queue vital buffer' "$KERNLOG" 2>/dev/null || true)
QUEUE_EVICT_COUNT=${QUEUE_EVICT_COUNT:-0}
WORKQUEUE_HOG_COUNT=$(grep -Eci 'svm_range_deferred_list_work .*hogged CPU' "$KERNLOG" 2>/dev/null || true)
WORKQUEUE_HOG_COUNT=${WORKQUEUE_HOG_COUNT:-0}
HARD_FAULT_LINES_LOG=$(grep -Eci 'GPU reset|ring.*timeout|vm_fault|VM fault|page fault|amdgpu.*hang|coredump|devcoredump' "$KERNLOG" 2>/dev/null || true)
HARD_FAULT_LINES_LOG=${HARD_FAULT_LINES_LOG:-0}

echo "--- CHURN DELIVERABLE ---" | tee -a "$MARKERS"
echo "VERDICT: $VERDICT" | tee -a "$MARKERS"
echo "AER delta: $PRE_AER -> $FINAL_AER (delta $((FINAL_AER-PRE_AER)))" | tee -a "$MARKERS"
echo "devcoredump delta: $PRE_DEVCD -> $FINAL_DEVCD (delta $((FINAL_DEVCD-PRE_DEVCD)))" | tee -a "$MARKERS"
echo "amdgpu err delta: $PRE_AMDERR -> $FINAL_AMDERR (delta $((FINAL_AMDERR-PRE_AMDERR)))" | tee -a "$MARKERS"
echo "MAX_VRAM: $MAX_VRAM" | tee -a "$MARKERS"
echo "QUEUE_EVICT_COUNT: $QUEUE_EVICT_COUNT" | tee -a "$MARKERS"
echo "WORKQUEUE_HOG_COUNT: $WORKQUEUE_HOG_COUNT" | tee -a "$MARKERS"
echo "HARD_FAULT_LINES_LOG: $HARD_FAULT_LINES_LOG" | tee -a "$MARKERS"
echo "Artifacts: $MARKERS $VRAMLOG $KERNLOG $LAST40" | tee -a "$MARKERS"
echo "DONE $(date -u +%Y%m%dT%H%M%SZ)" | tee -a "$MARKERS"
