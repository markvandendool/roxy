# PATH TRUTH CONTRACT
## ROXY Canonical Path Specification v1.0
**Created**: 2026-01-05
**Status**: ENFORCED

---

## 1. DUPLICATED LOCI TABLE

| Thing | Observed Paths | Canonical | Who Writes | Status |
|-------|---------------|-----------|------------|--------|
| **Code Root** | `~/.roxy/` | `~/.roxy/` | Manual/Claude | CANONICAL |
| | `/opt/roxy/services/` | - | Legacy scripts | DEPRECATED |
| | `/opt/roxy/services.LEGACY.*/` | - | Archive | FROZEN |
| **Main Entry** | `~/.roxy/roxy_core.py` (83KB) | `~/.roxy/roxy_core.py` | Development | CANONICAL |
| | `/opt/roxy/services/roxy_core.py` (15KB) | - | Unknown | ORPHAN |
| **Data Root** | `/opt/roxy/data/roxy_memory.db` | `/opt/roxy/data/` | roxy_core.py | CANONICAL |
| | `~/.roxy/data/` | - | - | DOES NOT EXIST |
| **ChromaDB** | `~/.roxy/chroma_db/` | `~/.roxy/chroma_db/` | ChromaDB HTTP | CANONICAL |
| | `/opt/roxy/chroma_data/` | - | Docker volume | DOCKER-MANAGED |
| **Venv** | `~/.roxy/venv/` | `~/.roxy/venv/` | pip | CANONICAL |
| | `/opt/roxy/venv/` | - | Legacy | ORPHAN |
| | `/opt/roxy/.venv/` | - | Legacy | ORPHAN |
| **Evidence** | `~/.roxy/evidence/` | `~/.roxy/evidence/` | Audit scripts | CANONICAL |
| **Logs** | `~/.roxy/logs/` | `~/.roxy/logs/` | roxy_core.py | CANONICAL |
| **Wrapper** | `/usr/local/bin/roxy` | NEEDS FIX | Manual | MISCONFIGURED |
| **systemd** | `mcp-server.service` → `~/.roxy/` | `~/.roxy/` | systemd | CORRECT |

---

## 2. ROOT CAUSE TIMELINE

### Phase 1: JARVIS Era (Pre-2026-01-01)
- **Location**: `/opt/roxy/services/jarvis_core.py`
- **Pattern**: Traditional `/opt/` system service layout
- **Data**: `/opt/roxy/data/roxy_memory.db` (SQLite)

### Phase 2: JARVIS→ROXY Rename (2026-01-01)
- **Trigger**: Manual rename + migration
- **Action**: Created `/opt/roxy/services.LEGACY.20260101_200448/`
- **Problem**: New `roxy_core.py` written to `~/.roxy/` (user home)
- **Cause**: Claude/Copilot defaulted to `~/.roxy/` for "user config"
- **Evidence**: `ls -la /opt/roxy/*.LEGACY*` shows Jan 1 timestamp

### Phase 3: Duplication Begins (2026-01-02 to 2026-01-04)
- **Trigger**: Multiple agents working in parallel
- **Action**: Some edits went to `~/.roxy/roxy_core.py`, some to `/opt/roxy/services/roxy_core.py`
- **Evidence**:
  - `~/.roxy/roxy_core.py` mtime: 2026-01-04 15:46 (83KB, full-featured)
  - `/opt/roxy/services/roxy_core.py` mtime: 2026-01-05 07:12 (15KB, stripped)
- **Cause**: No canonical path contract, agents picked paths based on context

### Phase 4: Wrapper Never Updated (2026-01-01 to now)
- **Problem**: `/usr/local/bin/roxy` still points to `/opt/roxy`
- **Evidence**: Wrapper contains `ROXY_INTERFACE="/opt/roxy/services/roxy_interface.py"`
- **Impact**: Users running `roxy` CLI get wrong (orphan) code

### Phase 5: Evidence Bundle Proliferation (2026-01-02)
- **Trigger**: Multiple audit requests
- **Action**: Created 8 separate bundles in `~/.roxy/evidence/`
- **Problem**: Each bundle claims to be authoritative, no deduplication
- **Evidence**: `ls ~/.roxy/evidence/` shows 8 bundles in 3 days

---

## 3. SCORING FAILURE ANALYSIS

### The Claim
"Redis/Postgres/NATS integrated and used" → contributed to 49/50 score

### The Reality
```bash
# Neither roxy_core.py imports these:
grep "import redis\|import psycopg\|import nats" ~/.roxy/roxy_core.py
# Result: NO MATCHES

grep "import redis\|import psycopg\|import nats" /opt/roxy/services/roxy_core.py
# Result: NO MATCHES
```

### How The Conflation Happened

| What Was Checked | What Should Have Been Checked |
|------------------|------------------------------|
| `docker ps` shows containers healthy | `grep import redis roxy_core.py` |
| Port 6379 listening | `redis-cli PING` from inside roxy_core |
| Port 5432 listening | SQL query executed by roxy_core |
| Port 4222 listening | NATS publish/subscribe in code |

### Root Cause
The scoring rubric accepted **"infrastructure exists"** as proof of **"application uses it"**.

This is like saying "I have a gym membership" proves "I work out daily."

---

## 4. CANONICAL PATH CONTRACT (ENFORCED)

### Code Canonical: `~/.roxy/`
- All Python source files
- All config files (config.json, .env)
- All MCP servers (`~/.roxy/mcp/`)

### Data Canonical: `/opt/roxy/data/`
- `roxy_memory.db` (SQLite)
- Persistent state that survives code updates

### ChromaDB Canonical: Docker-managed
- HTTP API at `http://localhost:8000`
- Persistence in Docker volume `chroma_data`

### Evidence Canonical: `~/.roxy/evidence/`
- One bundle per audit session
- Naming: `YYYYMMDD_HHMMSS_<PURPOSE>/`
- Must include `MANIFEST.txt` with hashes

### Forbidden Roots (DO NOT USE)
- `/opt/roxy/services/` - ORPHAN, will be deleted
- `/opt/roxy/venv/` - ORPHAN
- `/opt/roxy/.venv/` - ORPHAN

---

## 5. MIGRATION STEPS

### Step 1: Kill Orphan Process
```bash
# The orphan /opt/roxy/services/roxy_core.py process
kill 2316356
```

### Step 2: Fix Wrapper
```bash
sudo tee /usr/local/bin/roxy << 'EOF'
#!/bin/bash
# ROXY Command - Quick access to the resident AI
# CANONICAL: Uses ~/.roxy code root

ROXY_HOME="$HOME/.roxy"
ROXY_VENV="$ROXY_HOME/venv"

case "${1:-status}" in
    status)
        curl -s http://localhost:8766/health | jq . || echo "ROXY not running"
        ;;
    start)
        cd "$ROXY_HOME" && source "$ROXY_VENV/bin/activate"
        nohup python3 roxy_core.py > /tmp/roxy-logs/roxy-core.log 2>&1 &
        echo "ROXY starting (PID $!)"
        ;;
    stop)
        pkill -f "roxy_core.py"
        echo "ROXY stopped"
        ;;
    logs)
        tail -f /tmp/roxy-logs/roxy-core.log
        ;;
    *)
        echo "Usage: roxy {status|start|stop|logs}"
        ;;
esac
EOF
sudo chmod +x /usr/local/bin/roxy
```

### Step 3: Archive Orphan Code
```bash
mv /opt/roxy/services /opt/roxy/services.ORPHAN.$(date +%Y%m%d_%H%M%S)
```

### Step 4: Update systemd (if needed)
Ensure any roxy systemd units use `~/.roxy` paths.

---

## 6. SCORING RULE FIX

### Old Rule (BROKEN)
```
Service Integrated = Container Running + Port Listening
```

### New Rule (ENFORCED)
```
Service Integrated =
  1. Import statement in roxy_core.py (grep proof)
  2. Connection initialization in code (line number)
  3. Runtime read+write roundtrip (log evidence or test command)
```

### Proof Template for Each Service
```markdown
## Redis Integration Proof
- [ ] Import: `grep "import redis" ~/.roxy/roxy_core.py` → line XX
- [ ] Init: `grep "Redis(" ~/.roxy/roxy_core.py` → line XX
- [ ] Roundtrip: `curl localhost:8766/test-redis` → {"set": "ok", "get": "ok"}
```

If ANY checkbox is empty → Service NOT integrated.

---

## 7. CURRENT STATE SUMMARY

| Component | Expected | Actual | Fix Required |
|-----------|----------|--------|--------------|
| Running Process | `~/.roxy/roxy_core.py` | `~/.roxy/roxy_core.py` (PID 1961808) | None |
| Port 8766 | PID 1961808 | PID 1961808 | None |
| Orphan Process | None | `/opt/roxy/services/roxy_core.py` (PID 2316356) | Kill it |
| Wrapper | Points to `~/.roxy` | Points to `/opt/roxy` | Fix wrapper |
| Redis | Integrated | NOT imported | Update docs |
| Postgres | Integrated | NOT imported | Update docs |
| NATS | Integrated | NOT imported | Update docs |
