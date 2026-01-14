# RUNBOOK: ROXY Environment (Secrets) Setup

**Purpose:** Define the required environment variables for ROXY + LUNO without committing secrets to Git.

## Canonical locations
- **Env file:** `/home/mark/.roxy/etc/roxy.env`
- **Code:** `/home/mark/.roxy` (repo)

## Required groups

### Breakroom / Supabase (LUNO Orchestrator)
These enable Breakroom connectivity and table checks.

```
SUPABASE_URL=
SUPABASE_ANON_KEY=
# Optional (needed for write/admin operations):
SUPABASE_SERVICE_ROLE_KEY=
# Optional (direct DB checks):
SUPABASE_DB_URL=
```

### ROXY → Podium (Orchestrator bridge)
```
ROXY_PODIUM_BASE_URL=http://127.0.0.1:3847
ROXY_PODIUM_WS=ws://127.0.0.1:3847
# Optional auth
ROXY_PODIUM_TOKEN=
```

### GitHub (ROXY core API)
ROXY uses `~/.roxy/github.token` by default. Optional env override:
```
GITHUB_TOKEN=
```

### Home Assistant
```
HA_URL=http://localhost:8123
HA_TOKEN=
```

## Safety rules
- Do **not** store secrets in Git.
- Keep `/home/mark/.roxy/etc/roxy.env` **chmod 600**.
- Use systemd `EnvironmentFile=-/home/mark/.roxy/etc/roxy.env` (optional file).

## Verification gates
- Orchestrator health: `curl -sS http://127.0.0.1:3847/health/orchestrator`
- ROXY readiness: `curl -sS http://127.0.0.1:8766/ready`
- GitHub status: `curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" http://127.0.0.1:8766/github/status`
- HA test: `/home/mark/.roxy/ha-integration/test-ha.sh`
