#!/usr/bin/env bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
set -euo pipefail
RUNBOOK=~/.roxy/runbooks/warmup_studio.yaml
EXEC=~/.roxy/tools/runbook_executor.py

usage(){
  cat <<EOF
Usage: $0 [--dry-run|--live]
  --dry-run  (default) show actions
  --live --yes  perform actions (use with care)
EOF
}

if [ "$#" -eq 0 ]; then
  python3 "$EXEC" --run "$RUNBOOK"
  exit 0
fi

if [ "$1" = "--live" ]; then
  if [ "$2" != "--yes" ]; then
    echo "Live mode requires --yes to confirm"
    exit 1
  fi
  python3 "$EXEC" --run "$RUNBOOK" --live --yes
else
  usage
fi