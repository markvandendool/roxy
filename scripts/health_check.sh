#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Health check script for ROXY infrastructure
# Checks all services and reports status

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "ROXY Infrastructure Health Check"
echo "=================================="
echo ""

# Check Docker services
check_service() {
    local service=$1
    local url=$2
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service: Healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $service: Unhealthy"
        return 1
    fi
}

# Check ROXY Core
if systemctl --user is-active --quiet roxy-core 2>/dev/null; then
    echo -e "${GREEN}✓${NC} ROXY Core: Running"
else
    echo -e "${RED}✗${NC} ROXY Core: Not running"
fi

# Check Docker containers
if command -v docker &> /dev/null; then
    echo ""
    echo "Docker Services:"
    
    # PostgreSQL
    if docker exec roxy-postgres pg_isready -U roxy > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} PostgreSQL: Healthy"
    else
        echo -e "${RED}✗${NC} PostgreSQL: Unhealthy"
    fi
    
    # Redis
    if docker exec roxy-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis: Healthy"
    else
        echo -e "${RED}✗${NC} Redis: Unhealthy"
    fi
    
    # ChromaDB
    check_service "ChromaDB" "http://localhost:8000/api/v1/heartbeat"
    
    # n8n
    check_service "n8n" "http://localhost:5678/healthz"
    
    # Prometheus
    check_service "Prometheus" "http://localhost:9090/-/healthy"
    
    # Grafana
    check_service "Grafana" "http://localhost:3000/api/health"
fi

echo ""
echo "Health check complete"





