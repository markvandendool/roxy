#!/usr/bin/env bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# stack_doctor.sh - Full stack doctor (ROXY + Orchestrator + Pools + Postgres)
set -euo pipefail

JSON_MODE=0
FAST_MODE=0
REMOTE_GIT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON_MODE=1; shift ;;
    --fast) FAST_MODE=1; shift ;;
    --remote-git=*) REMOTE_GIT="${1#*=}"; shift ;;
    --remote-git) REMOTE_GIT="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

PASS=0
FAIL=0
WARN=0
RESULTS_FILE=$(mktemp)
JSON_OUT=$(mktemp)
EMITTED=0

cleanup() {
  if [ "$JSON_MODE" -eq 1 ] && [ "$EMITTED" -eq 0 ]; then
    printf '{"pass":0,"fail":1,"warn":0,"results":[{"status":"fail","name":"doctor crashed or exited early"}]}\n'
  fi
  rm -f "$RESULTS_FILE" "$JSON_OUT"
}
trap cleanup EXIT

add_result() {
  local status="$1" name="$2" detail="$3" fix="$4"
  printf '%s\t%s\t%s\t%s\n' "$status" "$name" "$detail" "$fix" >> "$RESULTS_FILE"
}

check_pass() {
  local msg="$1"
  PASS=$((PASS+1))
  add_result "pass" "$msg" "" ""
  if [ "$JSON_MODE" -eq 0 ]; then
    echo "  [PASS] $msg"
  fi
}

check_fail() {
  local msg="$1" fix="$2"
  FAIL=$((FAIL+1))
  add_result "fail" "$msg" "" "$fix"
  if [ "$JSON_MODE" -eq 0 ]; then
    echo "  [FAIL] $msg"
    echo "         Fix: $fix"
  fi
}

check_warn() {
  local msg="$1" note="$2"
  WARN=$((WARN+1))
  add_result "warn" "$msg" "$note" ""
  if [ "$JSON_MODE" -eq 0 ]; then
    echo "  [WARN] $msg"
    echo "         Note: $note"
  fi
}

section() {
  if [ "$JSON_MODE" -eq 0 ]; then
    echo ""
    echo "=== $1 ==="
  fi
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    if [ "$JSON_MODE" -eq 1 ]; then
      printf '{"pass":0,"fail":1,"warn":0,"results":[{"status":"fail","name":"missing dependency","detail":"%s"}]}\n' "$1"
      EMITTED=1
    else
      echo "Missing dependency: $1" >&2
    fi
    exit 1
  }
}

# Minimal dependency checks (before muting stderr).
need curl
need rg
need python3

# Ensure JSON mode never emits non-JSON noise.
if [ "$JSON_MODE" -eq 1 ]; then
  exec 2>/dev/null
  exec 3>/dev/null
  CURL_STDERR_FD=3
else
  CURL_STDERR_FD=2
fi

port_owner() {
  local port="$1"
  local line
  line=$(ss -ltnp 2>/dev/null | rg ":${port}\\b" || true)
  if [ -z "$line" ]; then
    echo ""
    return
  fi
  local pid
  pid=$(echo "$line" | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n 1)
  if [ -z "$pid" ]; then
    echo ""
    return
  fi
  local cmd
  cmd=$(ps -p "$pid" -o cmd= 2>/dev/null | head -n 1)
  echo "pid=${pid} cmd=${cmd}"
}

section "ROXY readiness"
if curl -sS --max-time 3 http://127.0.0.1:8766/ready 2>&$CURL_STDERR_FD | rg -q '"ready"\s*:\s*true'; then
  check_pass "roxy-core /ready true"
else
  check_fail "roxy-core /ready not true" "curl http://127.0.0.1:8766/ready"
fi

section "Ollama pools"
for p in 11434 11435; do
  if curl -sS --max-time 2 "http://127.0.0.1:$p/api/version" >/dev/null 2>&$CURL_STDERR_FD; then
    check_pass "Ollama port $p reachable"
  else
    check_fail "Ollama port $p unreachable" "systemctl status ollama-w5700x.service / ollama-6900xt.service"
  fi
  if [ "$FAST_MODE" -eq 1 ]; then
    check_warn "Port $p owner skipped (--fast)" "Run without --fast for owner details"
  else
    owner=$(port_owner "$p")
    if [ -n "$owner" ]; then
      check_pass "Port $p owner: $owner"
    else
      check_warn "Port $p owner unknown" "ss -ltnp or sudo ss -ltnp"
    fi
  fi
  done

section "Orchestrator health"
http_code="000"
health_json=""
latency_ms=""
for _ in 1 2 3; do
  start_ms=$(date +%s%3N)
  health_json=$(curl -sS --max-time 3 -w "\nHTTP:%{http_code}\n" http://127.0.0.1:3847/health/orchestrator 2>&$CURL_STDERR_FD || true)
  end_ms=$(date +%s%3N)
  latency_ms=$((end_ms - start_ms))
  http_code=$(echo "$health_json" | tail -n 1 | sed 's/HTTP://')
  if [ "$http_code" != "000" ]; then
    break
  fi
  sleep 0.5
done
if [ "$http_code" = "200" ]; then
  add_result "pass" "orchestrator /health 200" "http_code=${http_code} latency_ms=${latency_ms}" ""
  if [ "$JSON_MODE" -eq 0 ]; then
    echo "  [PASS] orchestrator /health 200"
    echo "         http_code=${http_code} latency_ms=${latency_ms}"
  fi
elif [ "$http_code" = "503" ]; then
  add_result "warn" "orchestrator /health degraded (503)" "http_code=${http_code} latency_ms=${latency_ms}" "Check /health/orchestrator JSON for causes"
  if [ "$JSON_MODE" -eq 0 ]; then
    echo "  [WARN] orchestrator /health degraded (503)"
    echo "         http_code=${http_code} latency_ms=${latency_ms}"
    echo "         Note: Check /health/orchestrator JSON for causes"
  fi
else
  add_result "fail" "orchestrator /health unreachable" "http_code=${http_code} latency_ms=${latency_ms}" "systemctl --user restart luno-orchestrator"
  if [ "$JSON_MODE" -eq 0 ]; then
    echo "  [FAIL] orchestrator /health unreachable"
    echo "         http_code=${http_code} latency_ms=${latency_ms}"
    echo "         Fix: systemctl --user restart luno-orchestrator"
  fi
fi
if [ "$FAST_MODE" -eq 1 ]; then
  check_warn "Port 3847 owner skipped (--fast)" "Run without --fast for owner details"
else
  owner=$(port_owner 3847)
  if [ -n "$owner" ]; then
    check_pass "Port 3847 owner: $owner"
  else
    check_warn "Port 3847 owner unknown" "systemctl --user status luno-orchestrator"
  fi
fi

section "Postgres memory"
source "$HOME/.roxy/venv/bin/activate"
ROXY_MEMORY_DISABLE_EMBEDDINGS=1 python - <<'PY' > /tmp/roxy_mem_health.json
import json, sys
sys.path.insert(0, "/home/mark/.roxy")
from memory_postgres import PostgresMemory
m = PostgresMemory()
print(json.dumps(m.health_check()))
PY
if rg -q '"backend"\s*:\s*"postgres"' /tmp/roxy_mem_health.json; then
  check_pass "memory backend = postgres"
else
  check_fail "memory backend not postgres" "check Postgres creds/env and roxy-core drop-ins"
fi

if [ "$FAST_MODE" -eq 0 ]; then
  ROXY_MEMORY_DISABLE_EMBEDDINGS=1 python - <<'PY' > /tmp/roxy_mem_smoke.json
import json, sys
sys.path.insert(0, "/home/mark/.roxy")
from memory_postgres import PostgresMemory
m = PostgresMemory()
pre = m.get_stats().get("total_memories")
mid = m.remember("doctor-smoke", "ok", session_id="doctor")
post = m.get_stats().get("total_memories")
print(json.dumps({"pre": pre, "post": post, "memory_id": mid}))
PY
  if rg -q '"memory_id"\s*:\s*[0-9]+' /tmp/roxy_mem_smoke.json; then
    check_pass "memory write/read smoke"
  else
    check_warn "memory smoke inconclusive" "Inspect /tmp/roxy_mem_smoke.json"
  fi
else
  check_warn "memory smoke skipped (--fast)" "Run without --fast to include write/read smoke"
fi

section "Disk / SSHFS hazard"
if df -T /home/mark/mindsong-juke-hub 2>/dev/null | rg -q 'sshfs'; then
  usep=$(df -T /home/mark/mindsong-juke-hub | awk 'NR==2{print $6}' | tr -d '%')
  if [ "${usep:-0}" -ge 95 ]; then
    check_warn "mindsong-juke-hub is SSHFS and >95% full" "Use local clone or set ROXY_GIT_REPO"
  else
    check_warn "mindsong-juke-hub is SSHFS" "Prefer local clone for git ops"
  fi
else
  check_pass "mindsong-juke-hub not on SSHFS"
fi

if [ -n "$REMOTE_GIT" ]; then
  section "Remote Git (optional)"
  if [ -z "${ROXY_REMOTE_GIT_PATH:-}" ]; then
    check_warn "remote git path not set" "Set ROXY_REMOTE_GIT_PATH and re-run with --remote-git <host>"
  elif [ "$FAST_MODE" -eq 1 ]; then
    check_warn "remote git skipped (--fast)" "Run without --fast to include remote git status"
  else
    remote_out=$(timeout 10s ssh -o BatchMode=yes -o ConnectTimeout=3 "$REMOTE_GIT" "cd \"${ROXY_REMOTE_GIT_PATH}\" && git status -sb && git diff --stat | head -n 20" 2>&$CURL_STDERR_FD || true)
    if [ -n "$remote_out" ]; then
      summary=$(echo "$remote_out" | head -n 5 | tr '\n' '; ')
      add_result "pass" "remote git status (${REMOTE_GIT})" "$summary" ""
      if [ "$JSON_MODE" -eq 0 ]; then
        echo "$remote_out" | sed 's/^/  /'
      fi
    else
      check_warn "remote git status unavailable" "ssh ${REMOTE_GIT} \"cd ${ROXY_REMOTE_GIT_PATH} && git status -sb\""
    fi
  fi
fi

section "Summary"
if [ "$JSON_MODE" -eq 0 ]; then
  echo "Passed: $PASS  Failed: $FAIL  Warn: $WARN"
fi

if [ "$JSON_MODE" -eq 1 ]; then
  python3 - <<'PY' "$RESULTS_FILE" $PASS $FAIL $WARN > "$JSON_OUT"
import json, sys
path = sys.argv[1]
pass_n = int(sys.argv[2])
fail_n = int(sys.argv[3])
warn_n = int(sys.argv[4])
results = []
with open(path, 'r') as f:
  for line in f:
    status, name, detail, fix = line.rstrip('\n').split('\t')
    results.append({"status": status, "name": name, "detail": detail or None, "fix": fix or None})
print(json.dumps({"pass": pass_n, "fail": fail_n, "warn": warn_n, "results": results}, indent=2))
PY
  cat "$JSON_OUT"
  EMITTED=1
fi

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0