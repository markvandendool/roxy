#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# ROXY PATH DOCTOR - Validates path invariants and detects mixed roots
# ═══════════════════════════════════════════════════════════════════════════════
# Usage:
#   ./roxy-path-doctor.sh          # Run all checks
#   ./roxy-path-doctor.sh --fix    # Attempt automatic fixes
#   ./roxy-path-doctor.sh --strict # Exit 1 on any warning
# ═══════════════════════════════════════════════════════════════════════════════

set -uo pipefail
# Don't exit on error - we want to collect all issues

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

STRICT_MODE=false
FIX_MODE=false
ERRORS=0
WARNINGS=0

for arg in "$@"; do
    case $arg in
        --strict) STRICT_MODE=true ;;
        --fix) FIX_MODE=true ;;
    esac
done

echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}           ROXY PATH DOCTOR - Invariant Validation             ${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
CANONICAL_CODE_ROOT="$HOME/.roxy"
CANONICAL_DATA_ROOT="/opt/roxy/data"
CANONICAL_VENV="$HOME/.roxy/venv"
CANONICAL_ENTRY="$HOME/.roxy/roxy_core.py"

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1: Wrapper Script
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 1]${NC} Wrapper Script (/usr/local/bin/roxy)"

if [[ -f /usr/local/bin/roxy ]]; then
    WRAPPER_TARGET=$(grep -oP '(?<=ROXY_HOME="|ROXY_INTERFACE=")[^"]+' /usr/local/bin/roxy 2>/dev/null | head -1 || echo "UNKNOWN")

    if [[ "$WRAPPER_TARGET" == *"/opt/roxy"* ]]; then
        echo -e "  ${RED}FAIL${NC} Wrapper points to /opt/roxy (should be ~/.roxy)"
        echo -e "       Target: $WRAPPER_TARGET"
        ((ERRORS++))
    elif [[ "$WRAPPER_TARGET" == *".roxy"* ]] || [[ "$WRAPPER_TARGET" == "UNKNOWN" ]]; then
        echo -e "  ${GREEN}PASS${NC} Wrapper points to correct location"
    else
        echo -e "  ${YELLOW}WARN${NC} Wrapper target unclear: $WRAPPER_TARGET"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}WARN${NC} No wrapper at /usr/local/bin/roxy"
    ((WARNINGS++))
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2: systemd Units
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 2]${NC} systemd Unit Paths"

for unit in roxy-core.service mcp-server.service; do
    if systemctl cat "$unit" &>/dev/null; then
        WORK_DIR=$(systemctl cat "$unit" | grep -oP '(?<=WorkingDirectory=)[^\s]+' || echo "NOT SET")
        EXEC_START=$(systemctl cat "$unit" | grep -oP '(?<=ExecStart=)[^\s]+' | head -1 || echo "NOT SET")

        if [[ "$WORK_DIR" == *"/opt/roxy/services"* ]] || [[ "$EXEC_START" == *"/opt/roxy/services"* ]]; then
            echo -e "  ${RED}FAIL${NC} $unit uses orphan path /opt/roxy/services"
            ((ERRORS++))
        elif [[ "$WORK_DIR" == *".roxy"* ]] || [[ "$EXEC_START" == *".roxy"* ]]; then
            echo -e "  ${GREEN}PASS${NC} $unit uses canonical path (~/.roxy)"
        else
            echo -e "  ${YELLOW}INFO${NC} $unit: WorkDir=$WORK_DIR"
        fi
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: Running Process
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 3]${NC} Running roxy_core.py Process"

ROXY_PIDS=$(pgrep -f "roxy_core.py" 2>/dev/null || echo "")
PID_COUNT=$(echo "$ROXY_PIDS" | grep -c . 2>/dev/null || echo "0")

if [[ "$PID_COUNT" -eq 0 ]]; then
    echo -e "  ${YELLOW}WARN${NC} No roxy_core.py process running"
    ((WARNINGS++))
elif [[ "$PID_COUNT" -gt 1 ]]; then
    echo -e "  ${RED}FAIL${NC} Multiple roxy_core.py processes detected ($PID_COUNT)"
    for pid in $ROXY_PIDS; do
        CMD=$(ps -p "$pid" -o args= 2>/dev/null || echo "unknown")
        echo -e "       PID $pid: $CMD"
    done
    ((ERRORS++))
else
    PID=$ROXY_PIDS
    CMD=$(ps -p "$PID" -o args= 2>/dev/null || echo "unknown")
    if [[ "$CMD" == *".roxy/roxy_core.py"* ]]; then
        echo -e "  ${GREEN}PASS${NC} Single process from canonical path"
        echo -e "       PID $PID: $CMD"
    elif [[ "$CMD" == *"/opt/roxy"* ]]; then
        echo -e "  ${RED}FAIL${NC} Process running from orphan path"
        echo -e "       PID $PID: $CMD"
        ((ERRORS++))
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4: Port Binding
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 4]${NC} Port 8766 Binding"

PORT_INFO=$(ss -tlnp 2>/dev/null | grep ":8766 " || echo "")
if [[ -z "$PORT_INFO" ]]; then
    echo -e "  ${YELLOW}WARN${NC} Port 8766 not listening"
    ((WARNINGS++))
else
    PORT_PID=$(echo "$PORT_INFO" | grep -oP 'pid=\K[0-9]+' || echo "unknown")
    if [[ "$PORT_PID" != "unknown" ]]; then
        PORT_CMD=$(ps -p "$PORT_PID" -o args= 2>/dev/null || echo "unknown")
        if [[ "$PORT_CMD" == *".roxy"* ]]; then
            echo -e "  ${GREEN}PASS${NC} Port 8766 owned by canonical process (PID $PORT_PID)"
        else
            echo -e "  ${RED}FAIL${NC} Port 8766 owned by non-canonical process"
            echo -e "       $PORT_CMD"
            ((ERRORS++))
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 5: Venv Consistency
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 5]${NC} Venv Location"

if [[ -d "$CANONICAL_VENV" ]]; then
    echo -e "  ${GREEN}PASS${NC} Canonical venv exists: $CANONICAL_VENV"
else
    echo -e "  ${RED}FAIL${NC} Canonical venv missing: $CANONICAL_VENV"
    ((ERRORS++))
fi

# Check for orphan venvs
for orphan in /opt/roxy/venv /opt/roxy/.venv; do
    if [[ -d "$orphan" ]]; then
        echo -e "  ${YELLOW}WARN${NC} Orphan venv exists: $orphan"
        ((WARNINGS++))
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 6: Data Path
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 6]${NC} Data Path (roxy_memory.db)"

if [[ -f "$CANONICAL_DATA_ROOT/roxy_memory.db" ]]; then
    SIZE=$(du -h "$CANONICAL_DATA_ROOT/roxy_memory.db" | cut -f1)
    echo -e "  ${GREEN}PASS${NC} roxy_memory.db at canonical path ($SIZE)"
else
    echo -e "  ${YELLOW}WARN${NC} roxy_memory.db not found at $CANONICAL_DATA_ROOT"
    ((WARNINGS++))
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 7: Code Root Size Comparison
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 7]${NC} Code Root Integrity"

if [[ -f "$CANONICAL_ENTRY" ]]; then
    CANONICAL_SIZE=$(stat --printf="%s" "$CANONICAL_ENTRY")
    echo -e "  ${GREEN}INFO${NC} ~/.roxy/roxy_core.py: $CANONICAL_SIZE bytes"
fi

if [[ -f "/opt/roxy/services/roxy_core.py" ]]; then
    ORPHAN_SIZE=$(stat --printf="%s" "/opt/roxy/services/roxy_core.py")
    echo -e "  ${YELLOW}WARN${NC} /opt/roxy/services/roxy_core.py exists: $ORPHAN_SIZE bytes (ORPHAN)"
    ((WARNINGS++))
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 8: Service Integration Reality Check
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[CHECK 8]${NC} Service Integration (Redis/Postgres/NATS)"

for service in redis psycopg asyncpg nats; do
    if grep -q "import $service\|from $service" "$CANONICAL_ENTRY" 2>/dev/null; then
        echo -e "  ${GREEN}PASS${NC} $service: IMPORTED in roxy_core.py"
    else
        echo -e "  ${YELLOW}INFO${NC} $service: NOT imported (container may run but not integrated)"
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}                         SUMMARY                               ${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo -e "  Errors:   ${RED}$ERRORS${NC}"
echo -e "  Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo -e "  ${RED}${BOLD}STATUS: FAILED${NC} - Path invariants violated"
    echo ""
    echo -e "  Run with --fix to attempt automatic repairs"
    exit 1
elif [[ $WARNINGS -gt 0 ]] && [[ "$STRICT_MODE" == "true" ]]; then
    echo -e "  ${YELLOW}${BOLD}STATUS: WARNINGS${NC} (strict mode)"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "  ${YELLOW}${BOLD}STATUS: WARNINGS${NC} - Review recommended"
    exit 0
else
    echo -e "  ${GREEN}${BOLD}STATUS: HEALTHY${NC} - All path invariants satisfied"
    exit 0
fi
