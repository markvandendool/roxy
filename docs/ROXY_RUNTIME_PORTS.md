# ROXY Runtime Ports

Quick reference for all ROXY service ports.

## Core Services

| Port | Service | GPU/Pool | Description |
|------|---------|----------|-------------|
| 8766 | roxy-core | N/A | Main ROXY daemon (SSE streaming) |
| 8765 | MCP Server | N/A | Model Context Protocol server |

## Ollama Pools

| Port | Pool Name | GPU | Canonical Name | Models |
|------|-----------|-----|----------------|--------|
| 11434 | BIG | W5700X | w5700x | qwen2.5-coder:14b, deepseek-coder |
| 11435 | FAST | 6900XT | 6900xt | llama3:8b |

## Monitoring

| Port | Service | Description |
|------|---------|-------------|
| 3030 | Grafana | Metrics dashboard |
| 9099 | Prometheus | Metrics collection |

## Voice Services

| Port | Service | Description |
|------|---------|-------------|
| 8767 | Pitch WS | Pitch detection WebSocket (5.6ms latency) |

## Environment Variables

```bash
# Pool URLs
OLLAMA_BIG_URL=http://127.0.0.1:11434
OLLAMA_FAST_URL=http://127.0.0.1:11435
ROXY_OLLAMA_W5700X_URL=http://127.0.0.1:11434
ROXY_OLLAMA_6900XT_URL=http://127.0.0.1:11435

# Core service
ROXY_CORE_PORT=8766
ROXY_MCP_PORT=8765
```

## Port Conflicts

If ports conflict:
1. Check with `lsof -i :PORT`
2. Kill conflicting process or change port
3. Update corresponding systemd service

## Firewall Rules

Ports 8765-8767 should be accessible from localhost only for security.
Ports 11434-11435 (Ollama) may need LAN access for multi-host setups.
