#!/usr/bin/env bash
set -euo pipefail

TS=$(date -u +%Y%m%dT%H%M%SZ)
BASE_DIR="$HOME/.roxy/evidence"
OUTDIR="$BASE_DIR/sdma_repro_${TS}"
MARKERS="$OUTDIR/markers.log"
KERNLOG="$OUTDIR/kernel_window.log"
GPU_PROOF_LOG="$OUTDIR/gpu_proof.log"
GPU_BIND_LOG="$OUTDIR/gpu_bind.log"
PRE_STATE="$OUTDIR/pre_state.txt"
VERDICT_FILE="$OUTDIR/verdict.txt"
FAIL_CONTEXT="$OUTDIR/failure_context.log"
POST_STATE="$OUTDIR/post_state.txt"
AER_LOG="$OUTDIR/aer_delta.log"
KERNEL_TAIL="$OUTDIR/kernel_tail.log"
DEVCD_DELTA_LOG="$OUTDIR/devcd_delta.log"

mkdir -p "$OUTDIR"

MODE="${MODE:-A}"
TARGET_BDF="${TARGET_BDF:-0000:09:00.0}"
GPU_PROOF_PATTERN="${GPU_PROOF_PATTERN:-NAVI10|W5700X|Navi 10|Radeon Pro W5700X}"
WINDOW_SECS="${WINDOW_SECS:-30}"
POLL_SECS="${POLL_SECS:-5}"
TB_STATUS="${TB_STATUS:-unknown}"
TB_ATTEST_START="${TB_ATTEST_START:-unknown}"
TB_ATTEST_END="${TB_ATTEST_END:-unknown}"

GPU_TEX_SIZE="${GPU_TEX_SIZE:-8192}"
GPU_UPLOAD="${GPU_UPLOAD:-16}"
GPU_FRAG="${GPU_FRAG:-1}"

STAGES_SPEC="${STAGES_SPEC:-60,300,900}"
ROXY_HEALTH_URL="${ROXY_HEALTH_URL:-}"

# Convert BDF 0000:09:00.0 -> pci-0000_09_00_0
DRI_PRIME_SEL="${DRI_PRIME:-}"
if [ -z "$DRI_PRIME_SEL" ]; then
  DRI_PRIME_SEL="pci-${TARGET_BDF//[:.]/_}"
fi

{
  echo "=== SDMA_REPRO_START $TS ===";
  echo "MODE=$MODE";
  echo "TARGET_BDF=$TARGET_BDF";
  echo "DRI_PRIME=$DRI_PRIME_SEL";
  echo "TB_STATUS=$TB_STATUS";
  echo "TB_ATTEST_START=$TB_ATTEST_START";
  echo "STAGES_SPEC=$STAGES_SPEC";
  echo "WINDOW_SECS=$WINDOW_SECS POLL_SECS=$POLL_SECS";
  echo "GPU_TEX_SIZE=$GPU_TEX_SIZE GPU_UPLOAD=$GPU_UPLOAD GPU_FRAG=$GPU_FRAG";
  if [ -n "$ROXY_HEALTH_URL" ]; then
    echo "ROXY_HEALTH_URL=$ROXY_HEALTH_URL";
  fi
} | tee -a "$MARKERS"

# Log GPU inventory
{
  echo "=== lspci -nnk (GPU) ===";
  lspci -nnk | egrep -A3 -B1 'VGA|Display|AMD' || true;
} >> "$MARKERS"

# Map render nodes to PCI BDF
TARGET_RENDER_NODE=""
RUN_START_UTC=$(date -u '+%Y-%m-%d %H:%M:%S')
{
  echo "=== PRE_STATE ===";
  echo "Timestamp_UTC=$TS";
  echo "RUN_START_UTC=$RUN_START_UTC";
  echo "MODE=$MODE";
  echo "TB_STATUS=$TB_STATUS";
  echo "TB_ATTEST_START=$TB_ATTEST_START";
  echo "TARGET_BDF=$TARGET_BDF";
  echo "DRI_PRIME=$DRI_PRIME_SEL";
  echo "--- DRM render nodes ---";
  for n in /sys/class/drm/renderD*; do
    [ -e "$n/device" ] || continue
    bdf=$(basename "$(readlink -f "$n/device")")
    echo "$(basename "$n") -> $bdf"
    if [ "$bdf" = "$TARGET_BDF" ]; then
      TARGET_RENDER_NODE="/dev/dri/$(basename "$n")"
    fi
  done
  if [ -d /dev/dri/by-path ]; then
    echo "--- /dev/dri/by-path (target matches) ---";
    ls -l /dev/dri/by-path 2>/dev/null | egrep -i "$TARGET_BDF|render" || true;
  fi
  echo "TARGET_RENDER_NODE=$TARGET_RENDER_NODE";
} | tee "$PRE_STATE" >> "$MARKERS"

# Require DISPLAY for GL workload
if [ -z "${DISPLAY:-}" ]; then
  echo "ABORT: DISPLAY not set; GL stress requires an X session." | tee -a "$MARKERS" | tee "$VERDICT_FILE"
  exit 1
fi

# Prove GPU selection
GPU_PROOF_OK=0
{
  echo "=== GPU PROOF ($DRI_PRIME_SEL) ===";
  if command -v glxinfo >/dev/null 2>&1; then
    echo "-- glxinfo -B --";
    DRI_PRIME="$DRI_PRIME_SEL" glxinfo -B 2>/dev/null || true;
  else
    echo "glxinfo not available";
  fi
  if command -v vulkaninfo >/dev/null 2>&1; then
    echo "-- vulkaninfo --summary --";
    DRI_PRIME="$DRI_PRIME_SEL" vulkaninfo --summary 2>/dev/null || true;
  else
    echo "vulkaninfo not available";
  fi
} | tee "$GPU_PROOF_LOG"

if egrep -qi "$GPU_PROOF_PATTERN" "$GPU_PROOF_LOG"; then
  GPU_PROOF_OK=1
fi

if [ "$GPU_PROOF_OK" -ne 1 ]; then
  echo "ABORT: GPU selection proof failed (pattern: $GPU_PROOF_PATTERN)." | tee -a "$MARKERS" | tee "$VERDICT_FILE"
  exit 1
fi

# Baselines
PRE_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
PRE_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)

{
  echo "PRE_DEVCD=$PRE_DEVCD";
  echo "PRE_AER=$PRE_AER";
} | tee -a "$MARKERS"

{
  echo "PRE_DEVCD=$PRE_DEVCD";
  echo "PRE_AER=$PRE_AER";
} >> "$PRE_STATE"

FIRST_FAIL=""
FAIL_REASON=""
FAIL_STAGE=""
NEW_DEVCD=""

sample_gpu_fds() {
  local stage_label="$1"
  local phase="$2"
  local spid="$3"
  {
    echo "=== FD_SAMPLE $stage_label $phase $(date -u +%Y%m%dT%H%M%SZ) ==="
    echo "stress-ng PID=$spid"
    if [ -d "/proc/$spid/fd" ]; then
      sudo ls -l "/proc/$spid/fd" 2>/dev/null | awk '/\/dev\/dri\/(renderD|card)/ {print}' || true
    else
      echo "no /proc/$spid/fd"
    fi
  } >> "$GPU_BIND_LOG"
}

run_stage() {
  local stage_label="$1"
  local stage_secs="$2"
  echo "=== STAGE_START $stage_label ${stage_secs}s $(date -u +%Y%m%dT%H%M%SZ) ===" | tee -a "$MARKERS"

  # Start stress
  DRI_PRIME="$DRI_PRIME_SEL" stress-ng --gpu 1 \
    --gpu-tex-size "$GPU_TEX_SIZE" \
    --gpu-upload "$GPU_UPLOAD" \
    --gpu-frag "$GPU_FRAG" \
    --timeout "${stage_secs}s" --metrics-brief \
    >> "$MARKERS" 2>&1 &
  local spid=$!
  local stage_start
  stage_start=$(date +%s)
  local t_early t_mid t_late
  t_early=$((stage_secs / 10))
  if [ "$t_early" -lt 5 ]; then t_early=5; fi
  t_mid=$((stage_secs / 2))
  t_late=$((stage_secs * 9 / 10))
  local early_done=0 mid_done=0 late_done=0
  sleep 1
  {
    echo "=== STAGE_BIND $stage_label $(date -u +%Y%m%dT%H%M%SZ) ==="
    echo "stress-ng PID=$spid"
    ls -l "/proc/$spid/fd" 2>/dev/null | awk '/\/dev\/dri\/(renderD|card)/ {print}' || true
  } >> "$GPU_BIND_LOG"
  sample_gpu_fds "$stage_label" "start" "$spid"

  while kill -0 "$spid" >/dev/null 2>&1; do
    sleep "$POLL_SECS"
    local ts
    ts=$(date -u +%Y%m%dT%H%M%SZ)
    local win
    win=$(sudo journalctl -k --since "${WINDOW_SECS} seconds ago" --no-pager || true)

    if [ -n "$win" ]; then
      echo "==== $ts stage=$stage_label ====" >> "$KERNLOG"
      printf '%s\n' "$win" | egrep -i 'amdgpu|AER|BadTLP|pcie|sdma|ring timed out|ring.*timeout|gfxhub|vm_fault|page fault|GPU reset|GPU recovery|hang|devcoredump|coredump' >> "$KERNLOG" || true
    fi

    local aer_win hard_win
    aer_win=$(printf '%s\n' "$win" | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)
    hard_win=$(printf '%s\n' "$win" | egrep -i 'sdma|ring timed out|ring.*timeout|gfxhub|vm_fault|page fault|GPU reset|GPU recovery|amdgpu.*hang|devcoredump|coredump' | wc -l || true)
    local devcd_now
    devcd_now=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
    local now elapsed
    now=$(date +%s)
    elapsed=$((now - stage_start))
    if [ "$early_done" -eq 0 ] && [ "$elapsed" -ge "$t_early" ]; then
      sample_gpu_fds "$stage_label" "early" "$spid"
      early_done=1
    fi
    if [ "$mid_done" -eq 0 ] && [ "$elapsed" -ge "$t_mid" ]; then
      sample_gpu_fds "$stage_label" "mid" "$spid"
      mid_done=1
    fi
    if [ "$late_done" -eq 0 ] && [ "$elapsed" -ge "$t_late" ]; then
      sample_gpu_fds "$stage_label" "late" "$spid"
      late_done=1
    fi

    if [ "$aer_win" -gt 0 ]; then
      FAIL_REASON="AER_IN_WINDOW"
      FIRST_FAIL=$(printf '%s\n' "$win" | egrep -i 'AER|BadTLP|Bad TLP' | head -n 1 || true)
      FAIL_STAGE="$stage_label"
      {
        echo "=== FAILURE_CONTEXT $FAIL_REASON $stage_label $(date -u +%Y%m%dT%H%M%SZ) ===" >> "$FAIL_CONTEXT"
        win_ctx=$(sudo journalctl -k --since '2 minutes ago' --no-pager || true)
        if [ -n "$win_ctx" ]; then
          printf '%s\n' "$win_ctx" > "$OUTDIR/_fail_window.log"
          line=$(nl -ba "$OUTDIR/_fail_window.log" | egrep -i 'AER|BadTLP|Bad TLP' | head -n 1 | awk '{print $1}')
          if [ -n "$line" ]; then
            start=$((line-30)); [ "$start" -lt 1 ] && start=1
            end=$((line+30))
            nl -ba "$OUTDIR/_fail_window.log" | awk -v s="$start" -v e="$end" '($1>=s && $1<=e){$1=""; sub(/^ /,""); print}' >> "$FAIL_CONTEXT"
          else
            cat "$OUTDIR/_fail_window.log" >> "$FAIL_CONTEXT"
          fi
        fi
      } || true
      kill "$spid" >/dev/null 2>&1 || true
      wait "$spid" 2>/dev/null || true
      return 1
    fi
    if [ "$hard_win" -gt 0 ]; then
      FAIL_REASON="HARD_GPU_FAULT_IN_WINDOW"
      FIRST_FAIL=$(printf '%s\n' "$win" | egrep -i 'sdma|ring timed out|ring.*timeout|gfxhub|vm_fault|page fault|GPU reset|GPU recovery|amdgpu.*hang|devcoredump|coredump' | head -n 1 || true)
      FAIL_STAGE="$stage_label"
      {
        echo "=== FAILURE_CONTEXT $FAIL_REASON $stage_label $(date -u +%Y%m%dT%H%M%SZ) ===" >> "$FAIL_CONTEXT"
        win_ctx=$(sudo journalctl -k --since '2 minutes ago' --no-pager || true)
        if [ -n "$win_ctx" ]; then
          printf '%s\n' "$win_ctx" > "$OUTDIR/_fail_window.log"
          line=$(nl -ba "$OUTDIR/_fail_window.log" | egrep -i 'sdma|ring timed out|ring.*timeout|gfxhub|vm_fault|page fault|GPU reset|GPU recovery|amdgpu.*hang|devcoredump|coredump' | head -n 1 | awk '{print $1}')
          if [ -n "$line" ]; then
            start=$((line-30)); [ "$start" -lt 1 ] && start=1
            end=$((line+30))
            nl -ba "$OUTDIR/_fail_window.log" | awk -v s="$start" -v e="$end" '($1>=s && $1<=e){$1=""; sub(/^ /,""); print}' >> "$FAIL_CONTEXT"
          else
            cat "$OUTDIR/_fail_window.log" >> "$FAIL_CONTEXT"
          fi
        fi
      } || true
      kill "$spid" >/dev/null 2>&1 || true
      wait "$spid" 2>/dev/null || true
      return 1
    fi
    if [ "$devcd_now" -gt "$PRE_DEVCD" ]; then
      FAIL_REASON="DEVCDUMP_INCREASE"
      NEW_DEVCD=$(ls -1t /var/lib/amdgpu-devcoredumps | head -n 1 || true)
      FAIL_STAGE="$stage_label"
      {
        echo "=== FAILURE_CONTEXT $FAIL_REASON $stage_label $(date -u +%Y%m%dT%H%M%SZ) ===" >> "$FAIL_CONTEXT"
        win_ctx=$(sudo journalctl -k --since '2 minutes ago' --no-pager || true)
        if [ -n "$win_ctx" ]; then
          printf '%s\n' "$win_ctx" > "$OUTDIR/_fail_window.log"
          line=$(nl -ba "$OUTDIR/_fail_window.log" | egrep -i 'sdma|ring timed out|ring.*timeout|gfxhub|vm_fault|page fault|GPU reset|GPU recovery|amdgpu.*hang|devcoredump|coredump' | head -n 1 | awk '{print $1}')
          if [ -n "$line" ]; then
            start=$((line-30)); [ "$start" -lt 1 ] && start=1
            end=$((line+30))
            nl -ba "$OUTDIR/_fail_window.log" | awk -v s="$start" -v e="$end" '($1>=s && $1<=e){$1=""; sub(/^ /,""); print}' >> "$FAIL_CONTEXT"
          else
            cat "$OUTDIR/_fail_window.log" >> "$FAIL_CONTEXT"
          fi
        fi
      } || true
      kill "$spid" >/dev/null 2>&1 || true
      wait "$spid" 2>/dev/null || true
      return 1
    fi

    if [ -n "$ROXY_HEALTH_URL" ]; then
      if ! curl -fsS "$ROXY_HEALTH_URL" >/dev/null 2>&1; then
        FAIL_REASON="ROXY_HEALTH_FAIL"
        FIRST_FAIL="ROXY_HEALTH_URL failed"
        FAIL_STAGE="$stage_label"
        kill "$spid" >/dev/null 2>&1 || true
        wait "$spid" 2>/dev/null || true
        return 1
      fi
    fi
  done

  wait "$spid" 2>/dev/null || true
  echo "=== STAGE_COMPLETE $stage_label $(date -u +%Y%m%dT%H%M%SZ) ===" | tee -a "$MARKERS"
  return 0
}

IFS=',' read -r -a STAGE_LIST <<< "$STAGES_SPEC"
STAGE_IDX=0
for secs in "${STAGE_LIST[@]}"; do
  STAGE_IDX=$((STAGE_IDX+1))
  if ! run_stage "S${STAGE_IDX}" "$secs"; then
    break
  fi
done

FINAL_DEVCD=$(ls -1 /var/lib/amdgpu-devcoredumps 2>/dev/null | wc -l || true)
FINAL_AER=$(sudo journalctl -k --no-pager | egrep -i 'AER|BadTLP|Bad TLP' | wc -l || true)

{
  echo "=== POST_STATE ===";
  echo "Timestamp_UTC=$(date -u +%Y%m%dT%H%M%SZ)";
  echo "RUN_END_UTC=$(date -u '+%Y-%m-%d %H:%M:%S')";
  echo "MODE=$MODE";
  echo "TB_STATUS=$TB_STATUS";
  echo "TB_ATTEST_END=$TB_ATTEST_END";
  echo "TARGET_BDF=$TARGET_BDF";
  echo "DRI_PRIME=$DRI_PRIME_SEL";
  echo "--- DRM render nodes ---";
  for n in /sys/class/drm/renderD*; do
    [ -e "$n/device" ] || continue
    bdf=$(basename "$(readlink -f "$n/device")")
    echo "$(basename "$n") -> $bdf"
  done
  if [ -d /dev/dri/by-path ]; then
    echo "--- /dev/dri/by-path ---";
    ls -l /dev/dri/by-path 2>/dev/null || true;
  fi
} | tee "$POST_STATE" >> "$MARKERS"

{
  echo "PRE_DEVCD=$PRE_DEVCD";
  echo "FINAL_DEVCD=$FINAL_DEVCD";
  ls -lt /var/lib/amdgpu-devcoredumps 2>/dev/null | head -n 10 || true;
} > "$DEVCD_DELTA_LOG"

sudo journalctl -k --since "$RUN_START_UTC" --no-pager | tail -n 200 > "$KERNEL_TAIL" || true
sudo journalctl -k --since "$RUN_START_UTC" --no-pager | egrep -i 'AER|BadTLP|Bad TLP' > "$AER_LOG" || true

VERDICT="PASS"
if [ -n "$FAIL_REASON" ]; then
  VERDICT="FAIL"
fi

{
  echo "VERDICT=$VERDICT";
  if [ -n "$FAIL_REASON" ]; then
    echo "FAIL_REASON=$FAIL_REASON";
    echo "FAIL_STAGE=$FAIL_STAGE";
    echo "FIRST_FAIL_LINE=$FIRST_FAIL";
    if [ -n "$NEW_DEVCD" ]; then
      echo "NEW_DEVCD=$NEW_DEVCD";
    fi
  fi
  echo "PRE_DEVCD=$PRE_DEVCD FINAL_DEVCD=$FINAL_DEVCD";
  echo "PRE_AER=$PRE_AER FINAL_AER=$FINAL_AER";
  echo "Artifacts: $OUTDIR";
  echo "Limitations: stress-ng --gpu is a GL workload; it may not isolate SDMA as purely as a DMA-only test.";
} | tee "$VERDICT_FILE" | tee -a "$MARKERS"

exit 0
