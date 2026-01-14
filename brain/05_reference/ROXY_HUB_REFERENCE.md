# ROXY Hub Quick Reference

**Canonical Reference Document - Updated 2026-01-07**

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROXY HUB (Mac Studio)                        │
│                       10.0.0.92                                 │
├─────────────────────────────────────────────────────────────────┤
│  ROXY Core (roxy_core.py)     │  ROXY Proxy (roxy_proxy.py)    │
│  └─ 127.0.0.1:8766 (local)    │  └─ 0.0.0.0:9136 (LAN)         │
│                               │  └─ Injects X-ROXY-Token        │
├─────────────────────────────────────────────────────────────────┤
│  ~/mindsong-juke-hub          │  ~/.roxy/secret.token           │
│  (canonical repository)       │  (auth token, 600 perms)        │
└─────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ ROXY Linux  │ │   Friday    │ │  Any LAN    │
│ 10.0.0.99   │ │ 10.0.0.65   │ │   Client    │
│ (satellite) │ │ (satellite) │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Quick Commands

### Status Check (No Auth)
```bash
curl http://10.0.0.92:9136/api/status
```

### Tool Execution (Requires Token)
```bash
TOKEN=$(cat ~/.roxy/secret.token)

# Read a file
curl -s -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL read_file {\"path\":\"/etc/hosts\"}"}' \
  http://10.0.0.92:9136/api/roxy/run

# Git status of mindsong-juke-hub
curl -s -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL git_status {}"}' \
  http://10.0.0.92:9136/api/roxy/run

# List files
curl -s -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL list_files {\"path\":\"~\"}"}' \
  http://10.0.0.92:9136/api/roxy/run
```

## Available Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `read_file` | Read file contents | `path` |
| `list_files` | List directory contents | `path` |
| `search_code` | Search code in files | `query` |
| `git_status` | Git status of mindsong-juke-hub | (none) |

## Endpoints

| Path | Method | Auth | Description |
|------|--------|------|-------------|
| `/api/status` | GET | No | Health check |
| `/api/roxy/run` | POST | Yes | Execute tool |
| `/health` | GET | No | Core health |

## Forbidden Actions

❌ **DO NOT:**
- Mount sshfs to mindsong-juke-hub (causes D-state/terminal stalls)
- Start SSH tunnels to 8766/9136 (conflicts with hub services)
- Run bun/dev servers on port 9136 (port conflict)
- Store tokens in version control

## Restart Hub Services

```bash
# On Mac Studio
ssh macstudio 'pkill -f roxy_core.py; pkill -f roxy_proxy.py'
ssh macstudio 'cd ~/.roxy && nohup python3 roxy_core.py > ~/opslogs/roxy-core.log 2>&1 &'
ssh macstudio 'cd ~/.roxy && nohup python3 roxy_proxy.py > ~/opslogs/roxy-proxy.log 2>&1 &'
```

## Verify Hub Processes

```bash
ssh macstudio 'lsof -iTCP:8766 -sTCP:LISTEN -nP'  # Should show Python
ssh macstudio 'lsof -iTCP:9136 -sTCP:LISTEN -nP'  # Should show Python
```

## Token Management

```bash
# Check token exists
ls -la ~/.roxy/secret.token

# Verify permissions (should be 600)
stat -c '%a %U %G %n' ~/.roxy/secret.token

# Token is same across all machines (synced from hub)
ssh macstudio 'cat ~/.roxy/secret.token' | sha256sum
cat ~/.roxy/secret.token | sha256sum
```

## Related Documentation

- [FRIDAY_UNIFIED_ONBOARDING.md](file:///home/mark/Desktop/FRIDAY_UNIFIED_ONBOARDING.md)
- [README_CORE.md](file:///home/mark/.roxy/README_CORE.md)
- [QUICK_START.md](file:///home/mark/.roxy/QUICK_START.md)
- [roxy-ui README.md](file:///home/mark/roxy-ui/README.md)

---

**Last Verified:** 2026-01-07 21:00 PST  
**Hub Migration Status:** ✅ COMPLETE
