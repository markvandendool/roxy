# Container Health Issues - Root Cause & Fixes

**Date**: January 2, 2026  
**Status**: Investigating

---

## Issues Identified

### 1. n8n Restart Loop ✅ ROOT CAUSE FOUND

**Error**:
```
password authentication failed for user "roxy"
There was an error initializing DB
```

**Root Cause**: Password mismatch between:
- PostgreSQL container: Uses `POSTGRES_PASSWORD` from environment
- n8n container: Uses `DB_POSTGRESDB_PASSWORD` (should match `POSTGRES_PASSWORD`)

**Fix Applied**:
- Verified n8n database exists in PostgreSQL
- ChromaDB healthcheck fixed (Python instead of curl)
- Need to verify password consistency

**Action Required**:
1. Check `.env` file for `POSTGRES_PASSWORD`
2. Ensure n8n container uses same password
3. Restart n8n container

### 2. ChromaDB Unhealthy ✅ FIXED

**Error**:
```
exec: "curl": executable file not found in $PATH
```

**Root Cause**: Healthcheck uses `curl` but ChromaDB container doesn't have it.

**Fix Applied**:
```yaml
# Before
test: ["CMD-SHELL", "curl -sf http://localhost:8000/api/v1/heartbeat || exit 1"]

# After
test: ["CMD-SHELL", "python3 -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8000/api/v1/heartbeat\").read()' || exit 1"]
```

**Status**: ✅ Fixed in docker-compose.foundation.yml

---

## Next Steps

1. **Verify n8n password**:
   ```bash
   # Check .env file
   grep POSTGRES_PASSWORD .env
   
   # Test connection
   docker exec roxy-postgres psql -U roxy -d n8n -c "SELECT 1;"
   ```

2. **Restart containers**:
   ```bash
   cd /opt/roxy/compose
   docker-compose -f docker-compose.foundation.yml restart n8n chromadb
   ```

3. **Verify health**:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

---

**Status**: ChromaDB fixed, n8n password verification needed


