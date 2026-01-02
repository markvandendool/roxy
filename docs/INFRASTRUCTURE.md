# ROXY Infrastructure Documentation

## Overview

ROXY infrastructure consists of:
- **ROXY Core**: Main HTTP IPC service (systemd user service)
- **PostgreSQL**: Shared database
- **Redis**: Queue and cache
- **ChromaDB**: Vector store for AI memory
- **n8n**: Workflow automation
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization

## Resource Limits

All services have resource limits configured in `docker-compose.foundation.yml`:

| Service | CPU Limit | Memory Limit | CPU Reservation | Memory Reservation |
|---------|----------|--------------|-----------------|-------------------|
| PostgreSQL | 2 cores | 2GB | 0.5 cores | 512MB |
| Redis | 0.5 cores | 512MB | 0.25 cores | 256MB |
| ChromaDB | 2 cores | 4GB | 0.5 cores | 1GB |
| n8n | 1 core | 1GB | 0.5 cores | 512MB |

## Health Checks

### Manual Health Check

Run the health check script:
```bash
/opt/roxy/scripts/health_check.sh
```

### Service Health Endpoints

- **ROXY Core**: `http://localhost:8766/health`
- **PostgreSQL**: `pg_isready -U roxy`
- **Redis**: `redis-cli ping`
- **ChromaDB**: `http://localhost:8000/api/v1/heartbeat`
- **n8n**: `http://localhost:5678/healthz`
- **Prometheus**: `http://localhost:9090/-/healthy`
- **Grafana**: `http://localhost:3000/api/health`

## Volumes

All volumes are named explicitly (not anonymous):

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis persistence files
- `n8n_data`: n8n workflow data
- `minio_data`: MinIO object storage
- `chromadb_data`: ChromaDB vector store
- `nats_data`: NATS JetStream data
- `prometheus_data`: Prometheus metrics storage
- `grafana_data`: Grafana dashboards and config

## Backup Strategy

See `docs/DISASTER_RECOVERY.md` for backup procedures.

## Troubleshooting

### n8n Restart Loop

If n8n is constantly restarting:
1. Check PostgreSQL connection: `docker exec roxy-postgres psql -U roxy -d n8n -c "SELECT 1;"`
2. Verify password consistency in `.env` file
3. Check n8n logs: `docker logs roxy-n8n --tail 50`

### ChromaDB Unhealthy

If ChromaDB healthcheck fails:
1. Check if container is running: `docker ps | grep chromadb`
2. Check logs: `docker logs roxy-chromadb --tail 50`
3. Verify port 8000 is accessible: `curl http://localhost:8000/api/v1/heartbeat`

### Resource Exhaustion

If services are being killed:
1. Check system resources: `docker stats`
2. Review resource limits in `docker-compose.foundation.yml`
3. Increase limits if needed (ensure host has capacity)

