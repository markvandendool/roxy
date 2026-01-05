#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# ROXY UNIVERSE LAUNCHER - One Command to Rule Them All
# ═══════════════════════════════════════════════════════════════════════════════
# Usage:
#   ./start-universe.sh              # Start everything (interactive)
#   ./start-universe.sh status       # Show what's running
#   ./start-universe.sh minimal      # Just the essentials
#   ./start-universe.sh full         # Everything including dev servers
#   ./start-universe.sh stop         # Stop all managed services
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Paths
ROXY_HOME="$HOME/.roxy"
MINDSONG_HOME="$HOME/mindsong-juke-hub"
COMPOSE_DIR="$MINDSONG_HOME/luno-orchestrator/citadel/compose"
VENV="$ROXY_HOME/venv/bin/python"
LOG_DIR="/tmp/roxy-logs"

mkdir -p "$LOG_DIR"

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

print_header() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
}

check_port() {
    local port=$1
    local name=$2
    if ss -tlnp 2>/dev/null | grep -q ":$port "; then
        echo -e "  ${GREEN}✓${NC} $name (port $port)"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name (port $port)"
        return 1
    fi
}

wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=${3:-30}
    local count=0

    while ! ss -tlnp 2>/dev/null | grep -q ":$port "; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge $max_wait ]; then
            echo -e "  ${RED}✗${NC} $name failed to start (timeout)"
            return 1
        fi
    done
    echo -e "  ${GREEN}✓${NC} $name ready (${count}s)"
    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# STATUS COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

show_status() {
    print_header "🌍 ROXY UNIVERSE STATUS"

    echo -e "${BOLD}TIER 1: Core Python Services${NC}"
    check_port 8766 "ROXY Core API"
    check_port 8765 "MCP Server"
    check_port 8767 "P3_TORCHCREPE WS"
    check_port 9767 "P3 Metrics"
    check_port 8768 "P4_SWIFTF0 WS"
    check_port 9768 "P4 Metrics"

    echo -e "\n${BOLD}TIER 2: Voice Stack${NC}"
    check_port 10300 "Whisper STT"
    check_port 10200 "Piper TTS"
    check_port 10400 "Wake Word"
    check_port 8004 "Chatterbox TTS"

    echo -e "\n${BOLD}TIER 3: Docker Infrastructure${NC}"
    check_port 5432 "PostgreSQL"
    check_port 6379 "Redis"
    check_port 5678 "n8n Workflows"
    check_port 9000 "MinIO S3"
    check_port 8000 "ChromaDB"
    check_port 4222 "NATS Event Bus"

    echo -e "\n${BOLD}TIER 4: Monitoring${NC}"
    check_port 9099 "Prometheus"
    check_port 3030 "Grafana"
    check_port 9093 "AlertManager"

    echo -e "\n${BOLD}TIER 5: AI/LLM${NC}"
    check_port 11434 "Ollama"
    check_port 8123 "Home Assistant"

    echo -e "\n${BOLD}TIER 6: Dev Servers (Optional)${NC}"
    check_port 9135 "MindSong Vite Dev"
    check_port 3847 "Podium WebSocket"
    check_port 3000 "Orchestrator API"

    # Docker container count
    echo -e "\n${BOLD}Docker Summary:${NC}"
    local running=$(docker ps -q 2>/dev/null | wc -l)
    echo -e "  Containers running: ${GREEN}$running${NC}"

    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# START FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

start_docker_foundation() {
    print_header "🐳 Starting Docker Foundation"

    cd "$COMPOSE_DIR"
    docker compose -f docker-compose.foundation.yml up -d 2>/dev/null || \
    docker-compose -f docker-compose.foundation.yml up -d

    echo "Waiting for services..."
    wait_for_port 5432 "PostgreSQL" 30
    wait_for_port 6379 "Redis" 10
    wait_for_port 8000 "ChromaDB" 30
}

start_docker_monitoring() {
    print_header "📊 Starting Monitoring Stack"

    cd "$COMPOSE_DIR"
    docker compose -f docker-compose.monitoring.yml up -d 2>/dev/null || \
    docker-compose -f docker-compose.monitoring.yml up -d

    wait_for_port 9099 "Prometheus" 20
    wait_for_port 3030 "Grafana" 20
}

start_roxy_core() {
    print_header "🧠 Starting ROXY Core Services"

    # Check if already running
    if ss -tlnp 2>/dev/null | grep -q ":8766 "; then
        echo -e "  ${YELLOW}→${NC} ROXY Core already running"
    else
        echo "  Starting ROXY Core..."
        cd "$ROXY_HOME"
        nohup "$VENV" roxy_core.py > "$LOG_DIR/roxy-core.log" 2>&1 &
        wait_for_port 8766 "ROXY Core" 15
    fi

    # MCP Server (systemd managed, but check anyway)
    if ss -tlnp 2>/dev/null | grep -q ":8765 "; then
        echo -e "  ${GREEN}✓${NC} MCP Server already running (systemd)"
    else
        echo "  Starting MCP Server..."
        sudo systemctl start mcp-server 2>/dev/null || \
        (cd "$ROXY_HOME/mcp" && nohup "$VENV" mcp_server.py > "$LOG_DIR/mcp-server.log" 2>&1 &)
        wait_for_port 8765 "MCP Server" 10
    fi
}

start_pitch_detector() {
    print_header "🎸 Starting Pitch Detection Swarm"

    # P3: TorchCrepe (GPU-accelerated, 6ms)
    if ss -tlnp 2>/dev/null | grep -q ":8767 "; then
        echo -e "  ${YELLOW}→${NC} P3_TORCHCREPE already running"
    else
        echo "  Starting P3_TORCHCREPE (GPU)..."
        cd "$ROXY_HOME/audio"
        source "$ROXY_HOME/venv/bin/activate"
        nohup python pitch_detector.py --device 12 > "$LOG_DIR/p3-torchcrepe.log" 2>&1 &
        wait_for_port 8767 "P3 WebSocket" 30
        wait_for_port 9767 "P3 Metrics" 5
    fi

    # P4: SwiftF0 (ONNX, 10ms, 95K params)
    if ss -tlnp 2>/dev/null | grep -q ":8768 "; then
        echo -e "  ${YELLOW}→${NC} P4_SWIFTF0 already running"
    else
        echo "  Starting P4_SWIFTF0 (ONNX)..."
        cd "$ROXY_HOME/audio"
        source "$ROXY_HOME/venv/bin/activate"
        nohup python swiftf0_detector.py --device 12 > "$LOG_DIR/p4-swiftf0.log" 2>&1 &
        wait_for_port 8768 "P4 WebSocket" 15
        wait_for_port 9768 "P4 Metrics" 5
    fi
}

start_voice_stack() {
    print_header "🎤 Checking Voice Stack"

    # These are typically managed by Home Assistant or systemd
    check_port 10300 "Whisper STT" || echo "    (Start via Home Assistant)"
    check_port 10200 "Piper TTS" || echo "    (Start via Home Assistant)"
    check_port 10400 "Wake Word" || echo "    (Start via Home Assistant)"
}

start_dev_servers() {
    print_header "💻 Starting Dev Servers"

    if ss -tlnp 2>/dev/null | grep -q ":9135 "; then
        echo -e "  ${YELLOW}→${NC} Vite dev server already running"
    else
        echo "  Starting MindSong Vite..."
        cd "$MINDSONG_HOME"
        nohup pnpm dev > "$LOG_DIR/vite-dev.log" 2>&1 &
        wait_for_port 9135 "Vite Dev Server" 30
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# STOP FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

stop_all() {
    print_header "🛑 Stopping ROXY Universe"

    echo "Stopping Python services..."
    pkill -f "roxy_core.py" 2>/dev/null && echo "  Stopped ROXY Core" || true
    pkill -f "pitch_detector.py" 2>/dev/null && echo "  Stopped P3_TORCHCREPE" || true
    pkill -f "swiftf0_detector.py" 2>/dev/null && echo "  Stopped P4_SWIFTF0" || true
    pkill -f "pnpm dev" 2>/dev/null && echo "  Stopped Vite" || true

    echo "Stopping Docker containers..."
    cd "$COMPOSE_DIR"
    docker compose -f docker-compose.foundation.yml -f docker-compose.monitoring.yml down 2>/dev/null || \
    docker-compose -f docker-compose.foundation.yml -f docker-compose.monitoring.yml down

    echo -e "\n${GREEN}✓${NC} Universe stopped"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

case "${1:-status}" in
    status)
        show_status
        ;;
    minimal)
        print_header "🚀 MINIMAL STARTUP"
        echo "Starting only essential services..."
        start_docker_foundation
        start_roxy_core
        start_pitch_detector
        echo -e "\n${GREEN}${BOLD}✓ Minimal universe ready!${NC}"
        show_status
        ;;
    full)
        print_header "🌟 FULL STARTUP"
        echo "Starting ALL services..."
        start_docker_foundation
        start_docker_monitoring
        start_roxy_core
        start_pitch_detector
        start_voice_stack
        start_dev_servers
        echo -e "\n${GREEN}${BOLD}✓ Full universe ready!${NC}"
        show_status
        ;;
    stop)
        stop_all
        ;;
    *)
        echo "Usage: $0 {status|minimal|full|stop}"
        echo ""
        echo "  status  - Show what's currently running"
        echo "  minimal - Start essential services only (Docker + ROXY Core + Pitch)"
        echo "  full    - Start everything including dev servers"
        echo "  stop    - Stop all managed services"
        exit 1
        ;;
esac
