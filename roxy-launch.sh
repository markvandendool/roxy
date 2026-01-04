#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ROXY Command Center - Launch Script
# Part of ROCKY-ROXY-ROCKIN-V1: Sprint 4 - Polish & Launch
#
# Story: RRR-017
#
# Usage:
#   ./roxy-launch.sh start    - Start all services
#   ./roxy-launch.sh stop     - Stop all services
#   ./roxy-launch.sh status   - Check service status
#   ./roxy-launch.sh restart  - Restart all services
#   ./roxy-launch.sh logs     - Tail all logs
# ═══════════════════════════════════════════════════════════════

set -e

ROXY_HOME="${HOME}/.roxy"
LOG_DIR="${ROXY_HOME}/logs"
PID_DIR="${ROXY_HOME}/pids"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Ensure directories exist
mkdir -p "$LOG_DIR" "$PID_DIR"

# ─────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────

print_banner() {
    echo -e "${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   ____   _____  __   ____   __                                ║"
    echo "║  |  _ \\ / _ \\ \\/ /\\ \\ / / | | |                               ║"
    echo "║  | |_) | | | |\\  /  \\ V /| |_| |                               ║"
    echo "║  |  _ <| |_| |/  \\   | | |  _  |                               ║"
    echo "║  |_| \\_\\\\___//_/\\_\\  |_| |_| |_|  Command Center               ║"
    echo "║                                                               ║"
    echo "║  🎸 Rocky + 🔧 ROXY = Unified Command Center                  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ─────────────────────────────────────────────────────────────────
# Service Definitions
# ─────────────────────────────────────────────────────────────────

declare -A SERVICES=(
    ["roxy-core"]="python3 ${ROXY_HOME}/roxy_core.py"
    ["roxy-mcp"]="python3 ${ROXY_HOME}/mcp_server.py"
    ["webhook"]="python3 ${ROXY_HOME}/webhook_receiver.py"
    ["settings-ui"]="python3 ${ROXY_HOME}/settings_ui.py"
)

declare -A SERVICE_PORTS=(
    ["roxy-core"]=8766
    ["roxy-mcp"]=8765
    ["webhook"]=8767
    ["settings-ui"]=8768
)

# ─────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

is_running() {
    local service=$1
    local pid_file="${PID_DIR}/${service}.pid"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

get_pid() {
    local service=$1
    local pid_file="${PID_DIR}/${service}.pid"
    
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file"
    fi
}

check_port() {
    local port=$1
    nc -z 127.0.0.1 "$port" 2>/dev/null
}

wait_for_port() {
    local port=$1
    local timeout=${2:-30}
    local count=0
    
    while ! check_port "$port"; do
        sleep 1
        ((count++))
        if [[ $count -ge $timeout ]]; then
            return 1
        fi
    done
    return 0
}

# ─────────────────────────────────────────────────────────────────
# Service Management
# ─────────────────────────────────────────────────────────────────

start_service() {
    local service=$1
    local cmd=${SERVICES[$service]}
    local port=${SERVICE_PORTS[$service]}
    
    if is_running "$service"; then
        log_warn "$service is already running (PID: $(get_pid $service))"
        return 0
    fi
    
    log_info "Starting $service..."
    
    # Start the service
    cd "$ROXY_HOME"
    nohup $cmd > "${LOG_DIR}/${service}.log" 2>&1 &
    local pid=$!
    echo $pid > "${PID_DIR}/${service}.pid"
    
    # Wait for port
    if [[ -n "$port" ]]; then
        if wait_for_port "$port" 10; then
            log_success "$service started (PID: $pid, Port: $port)"
        else
            log_error "$service failed to start (port $port not responding)"
            return 1
        fi
    else
        sleep 2
        if is_running "$service"; then
            log_success "$service started (PID: $pid)"
        else
            log_error "$service failed to start"
            return 1
        fi
    fi
}

stop_service() {
    local service=$1
    local pid_file="${PID_DIR}/${service}.pid"
    
    if ! is_running "$service"; then
        log_warn "$service is not running"
        return 0
    fi
    
    local pid=$(get_pid "$service")
    log_info "Stopping $service (PID: $pid)..."
    
    kill "$pid" 2>/dev/null || true
    
    # Wait for graceful shutdown
    local count=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        ((count++))
        if [[ $count -ge 10 ]]; then
            log_warn "Force killing $service..."
            kill -9 "$pid" 2>/dev/null || true
            break
        fi
    done
    
    rm -f "$pid_file"
    log_success "$service stopped"
}

status_service() {
    local service=$1
    local port=${SERVICE_PORTS[$service]}
    
    if is_running "$service"; then
        local pid=$(get_pid "$service")
        local port_status=""
        
        if [[ -n "$port" ]]; then
            if check_port "$port"; then
                port_status="${GREEN}:$port ✓${NC}"
            else
                port_status="${RED}:$port ✗${NC}"
            fi
        fi
        
        echo -e "  ${GREEN}●${NC} $service ${BLUE}(PID: $pid)${NC}${port_status}"
    else
        echo -e "  ${RED}○${NC} $service ${YELLOW}(stopped)${NC}"
    fi
}

# ─────────────────────────────────────────────────────────────────
# External Services Check
# ─────────────────────────────────────────────────────────────────

check_external_services() {
    echo ""
    echo -e "${BLUE}External Services:${NC}"
    
    local external_services=(
        "Luno Orchestrator:3000"
        "n8n:5678"
        "ChromaDB:8000"
        "Ollama:11434"
        "Whisper STT:10300"
        "Piper TTS:10200"
    )
    
    for svc in "${external_services[@]}"; do
        local name="${svc%%:*}"
        local port="${svc##*:}"
        
        if check_port "$port"; then
            echo -e "  ${GREEN}●${NC} $name ${BLUE}(:$port)${NC}"
        else
            echo -e "  ${RED}○${NC} $name ${YELLOW}(:$port offline)${NC}"
        fi
    done
    
    # Check Friday (remote)
    if nc -z -w2 10.0.0.65 8765 2>/dev/null; then
        echo -e "  ${GREEN}●${NC} Friday/Citadel ${BLUE}(10.0.0.65:8765)${NC}"
    else
        echo -e "  ${RED}○${NC} Friday/Citadel ${YELLOW}(unreachable)${NC}"
    fi
}

# ─────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────

cmd_start() {
    print_banner
    log_info "Starting ROXY Command Center..."
    echo ""
    
    for service in "${!SERVICES[@]}"; do
        start_service "$service"
    done
    
    echo ""
    log_success "ROXY Command Center started!"
    echo ""
    echo -e "  Dashboard:      ${BLUE}http://127.0.0.1:8766${NC}"
    echo -e "  MCP Server:     ${BLUE}http://127.0.0.1:8765${NC}"
    echo -e "  Webhook:        ${BLUE}http://127.0.0.1:8767${NC}"
    echo -e "  Settings UI:    ${BLUE}http://127.0.0.1:8768${NC}"
    echo ""
    echo -e "  Press ${YELLOW}⌘K${NC} to open Omnibar"
    echo -e "  Press ${YELLOW}F1${NC} to toggle mode"
}

cmd_stop() {
    log_info "Stopping ROXY Command Center..."
    echo ""
    
    for service in "${!SERVICES[@]}"; do
        stop_service "$service"
    done
    
    echo ""
    log_success "ROXY Command Center stopped"
}

cmd_restart() {
    cmd_stop
    echo ""
    sleep 2
    cmd_start
}

cmd_status() {
    print_banner
    echo -e "${BLUE}ROXY Services:${NC}"
    
    for service in "${!SERVICES[@]}"; do
        status_service "$service"
    done
    
    check_external_services
    
    echo ""
    
    # Overall health
    local running=0
    local total=${#SERVICES[@]}
    
    for service in "${!SERVICES[@]}"; do
        if is_running "$service"; then
            ((running++))
        fi
    done
    
    if [[ $running -eq $total ]]; then
        echo -e "${GREEN}Status: All systems operational${NC}"
    elif [[ $running -gt 0 ]]; then
        echo -e "${YELLOW}Status: Partially operational ($running/$total)${NC}"
    else
        echo -e "${RED}Status: All services stopped${NC}"
    fi
}

cmd_logs() {
    local service=${1:-"all"}
    
    if [[ "$service" == "all" ]]; then
        tail -f "${LOG_DIR}"/*.log
    else
        if [[ -f "${LOG_DIR}/${service}.log" ]]; then
            tail -f "${LOG_DIR}/${service}.log"
        else
            log_error "No log file for $service"
            exit 1
        fi
    fi
}

cmd_health() {
    echo -e "${BLUE}Running health checks...${NC}"
    echo ""
    
    # Check ROXY Core API
    if curl -s --max-time 5 http://127.0.0.1:8766/health > /dev/null 2>&1; then
        local health=$(curl -s http://127.0.0.1:8766/health | head -c 100)
        echo -e "${GREEN}✓${NC} ROXY Core API responding"
        echo "  $health"
    else
        echo -e "${RED}✗${NC} ROXY Core API not responding"
    fi
    
    echo ""
    
    # Check MCP tools
    if curl -s --max-time 5 http://127.0.0.1:8766/mcp/tools > /dev/null 2>&1; then
        local tool_count=$(curl -s http://127.0.0.1:8766/mcp/tools | grep -o '"name"' | wc -l)
        echo -e "${GREEN}✓${NC} MCP Tools available: $tool_count"
    else
        echo -e "${YELLOW}?${NC} MCP Tools endpoint not available"
    fi
}

# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

case "${1:-status}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$2"
        ;;
    health)
        cmd_health
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health}"
        exit 1
        ;;
esac
