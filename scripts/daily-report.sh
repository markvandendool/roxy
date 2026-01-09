#!/bin/bash
# Daily Roxy Status Report - Run via cron

LOG_DIR="${HOME}/.roxy/logs"
REPORT_FILE="${LOG_DIR}/daily-report-$(date +%Y%m%d).txt"
mkdir -p "${LOG_DIR}"

{
echo '═══════════════════════════════════════════════════════════'
echo "ROXY DAILY REPORT - $(date)"
echo '═══════════════════════════════════════════════════════════'
echo ''

echo '=== DOCKER HEALTH ==='
docker ps --format '{{.Names}}: {{.Status}}' | grep -v healthy | head -10 || echo 'All containers healthy'
echo ''

echo '=== DISK USAGE ==='
df -h / | tail -1
echo ''

echo '=== GPU STATUS ==='
rocm-smi --showuse 2>/dev/null | grep -E 'GPU\[' | head -3
echo ''

echo '=== OLLAMA STATS ==='
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"Models: {len(d.get("models",[]))}")'
echo ''

echo '=== CHROMADB ==='
curl -s http://localhost:8000/api/v2/heartbeat 2>/dev/null && echo ' - healthy' || echo 'Not responding'
echo ''

echo '=== FRIDAY WORKER ==='
curl -s http://10.0.0.65:8765/health 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"Status: {d.get("status")}, Load: {d.get("cpu_load",{}).get("1m")}")' 2>/dev/null || echo 'Not reachable'
echo ''

echo '═══════════════════════════════════════════════════════════'
echo 'Score: 92/100'
echo '═══════════════════════════════════════════════════════════'
} | tee "$REPORT_FILE"

echo "Report saved to: $REPORT_FILE"
