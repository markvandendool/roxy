# 🏰 CITADEL Phase 1 - Foundation Infrastructure Deployment

**Date**: December 31, 2025  
**Status**: ✅ DEPLOYED**

---

## Services Deployed

### 1. ✅ PostgreSQL 16
- **Container**: `roxy-postgres`
- **Port**: 5432
- **Database**: `roxy` (main), `n8n` (for n8n)
- **Status**: Running
- **Health**: Healthy

### 2. ✅ Redis 7
- **Container**: `roxy-redis`
- **Port**: 6379
- **Features**: AOF persistence, 512MB max memory
- **Status**: Running
- **Health**: Healthy

### 3. ✅ n8n Workflow Engine
- **Container**: `roxy-n8n`
- **Port**: 5678
- **Backend**: PostgreSQL
- **Queue**: Redis (Bull)
- **Status**: Running
- **URL**: http://127.0.0.1:5678
- **HTTPS**: https://n8n.jarvis.local (via Caddy)

### 4. ✅ MinIO S3 Storage
- **Container**: `roxy-minio`
- **Ports**: 9000 (API), 9001 (Console)
- **Status**: Running
- **URL**: http://127.0.0.1:9001
- **HTTPS**: https://minio.jarvis.local (via Caddy)

### 5. ✅ ChromaDB Vector Store
- **Container**: `roxy-chromadb`
- **Port**: 8000
- **Purpose**: AI memory/embeddings storage
- **Status**: Running
- **URL**: http://127.0.0.1:8000

### 6. ✅ NATS JetStream
- **Container**: `roxy-nats`
- **Ports**: 4222 (client), 8222 (monitoring)
- **Features**: JetStream enabled, persistent storage
- **Status**: Running
- **URL**: nats://127.0.0.1:4222

### 7. ⏳ Caddy Reverse Proxy
- **Container**: `roxy-caddy`
- **Ports**: 80, 443
- **Status**: Pending (depends on n8n, minio)
- **Purpose**: Auto-SSL for all services

---

## Configuration

### Environment Variables
- **Location**: `/opt/roxy/compose/.env`
- **Contains**: Secure passwords for PostgreSQL and MinIO

### Data Directories
- **Location**: `/opt/roxy/data/`
- **Directories**:
  - `postgres/` - PostgreSQL data
  - `redis/` - Redis AOF files
  - `n8n/files/` - n8n workflow files
  - `minio/` - MinIO object storage
  - `chromadb/` - ChromaDB vector data
  - `nats/` - NATS JetStream data

### Network
- **Name**: `roxy-network` (bridge)
- **All services**: Connected

---

## Quick Commands

### Check Status
```bash
cd /opt/roxy/compose
docker compose -f docker-compose.foundation.yml ps
```

### View Logs
```bash
docker compose -f docker-compose.foundation.yml logs -f [service-name]
```

### Restart Service
```bash
docker compose -f docker-compose.foundation.yml restart [service-name]
```

### Stop All
```bash
docker compose -f docker-compose.foundation.yml down
```

### Start All
```bash
docker compose -f docker-compose.foundation.yml up -d
```

---

## Service URLs

### Direct Access (HTTP)
- **n8n**: http://127.0.0.1:5678
- **MinIO Console**: http://127.0.0.1:9001
- **MinIO API**: http://127.0.0.1:9000
- **ChromaDB**: http://127.0.0.1:8000
- **NATS Monitoring**: http://127.0.0.1:8222
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Via Caddy (HTTPS - when deployed)
- **n8n**: https://n8n.jarvis.local
- **MinIO**: https://minio.jarvis.local
- **S3 API**: https://s3.jarvis.local
- **NATS**: https://nats.jarvis.local

---

## Health Checks

### PostgreSQL
```bash
docker compose -f docker-compose.foundation.yml exec postgres pg_isready -U roxy
```

### Redis
```bash
docker compose -f docker-compose.foundation.yml exec redis redis-cli ping
```

### n8n
```bash
curl http://127.0.0.1:5678/healthz
```

### ChromaDB
```bash
curl http://127.0.0.1:8000/api/v1/heartbeat
```

### NATS
```bash
curl http://127.0.0.1:8222/healthz
```

---

## Next Steps

### Phase 1 Complete ✅
- Foundation services deployed
- All services healthy
- Data persistence configured

### Phase 2: Browser Automation
- Deploy browser-use agent
- Set up Playwright
- Configure gVisor sandbox

### Phase 3: Desktop Automation
- Install dotool
- Configure Wayland automation
- Set up window-calls

---

## Troubleshooting

### Service Not Starting
```bash
# Check logs
docker compose -f docker-compose.foundation.yml logs [service-name]

# Check resource usage
docker stats

# Restart service
docker compose -f docker-compose.foundation.yml restart [service-name]
```

### Database Connection Issues
```bash
# Verify PostgreSQL is ready
docker compose -f docker-compose.foundation.yml exec postgres pg_isready -U roxy

# Check database exists
docker compose -f docker-compose.foundation.yml exec postgres psql -U roxy -l
```

### Port Conflicts
```bash
# Check what's using ports
sudo netstat -tlnp | grep -E "5432|6379|5678|9000|8000|4222"
```

---

**Deployment Complete**: December 31, 2025  
**Epic**: LUNA-000 CITADEL  
**Phase**: PHASE-1 Foundation Infrastructure  
**Status**: ✅ OPERATIONAL
















