# Quick Start: ROXY System

**Updated: 2026-01-07 (Hub Migration Complete)**

## ⚠️ CRITICAL: Hub Architecture

**ROXY Hub runs on Mac Studio (10.0.0.92), not locally.**

| Component | Host | Endpoint |
|-----------|------|----------|
| ROXY Core | Mac Studio | 127.0.0.1:8766 |
| ROXY Proxy | Mac Studio | 0.0.0.0:9136 |

**From any LAN machine:**
```bash
curl http://10.0.0.92:9136/api/status
```

---

## Prerequisites Check
```bash
# Check hub is reachable
curl -s http://10.0.0.92:9136/api/status | python3 -m json.tool

# Check token exists locally
cat ~/.roxy/secret.token

# Check SSH to Mac Studio works
ssh macstudio 'hostname'
```

## Step 1: Install Dependencies
```bash
cd /home/mark/.roxy
pip install -r requirements.txt
```

## Step 2: Run Tests
```bash
# Make test runner executable
chmod +x run_tests.sh

# Run all tests with coverage
./run_tests.sh

# Run specific test file
./run_tests.sh tests/test_security.py

# Run with verbose output
./run_tests.sh -vv

# Skip slow tests
./run_tests.sh -m "not slow"
```

## Step 3: Generate API Documentation
```bash
python3 generate_openapi.py

# View the generated spec
cat docs/openapi.yaml

# Upload to Swagger Editor: https://editor.swagger.io/
```

## Step 4: Set Up Automated Backups
```bash
# Make backup scripts executable
chmod +x backup.sh restore.sh

# Test backup manually
./backup.sh

# Add to crontab for daily backups at 2 AM
crontab -e
# Add this line:
# 0 2 * * * /home/mark/.roxy/backup.sh >> /home/mark/.roxy/logs/backup.log 2>&1
```

## Step 5: View Metrics (Optional)
```bash
# If Prometheus client is installed, metrics are exposed on port 9091
curl http://localhost:9091/metrics | grep roxy_

# Key metrics:
# - roxy_requests_total
# - roxy_request_duration_seconds
# - roxy_cache_hits_total
# - roxy_errors_total
```

## Test the System

### Test Hub Health
```bash
# No auth required for status
curl http://10.0.0.92:9136/api/status
```

### Test Tool Execution
```bash
# Load token
TOKEN=$(cat ~/.roxy/secret.token)

# Test read_file tool
curl -s -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL read_file {\"path\":\"/etc/hosts\"}"}' \
  http://10.0.0.92:9136/api/roxy/run

# Test git_status tool
curl -s -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL git_status {}"}' \
  http://10.0.0.92:9136/api/roxy/run

# Test list_files tool
curl -s -H "X-ROXY-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL list_files {\"path\":\"~\"}"}' \
  http://10.0.0.92:9136/api/roxy/run
```

### Available Tools
- `read_file` - Read file contents (requires `path`)
- `list_files` - List directory contents (requires `path`)
- `search_code` - Search code in files
- `git_status` - Git status of mindsong-juke-hub (read-only, no args)

### Test Without Auth (Should Fail)
```bash
# This should return 403 Forbidden
curl -s -H "Content-Type: application/json" \
  -d '{"command":"RUN_TOOL read_file {\"path\":\"/etc/hosts\"}"}' \
  http://10.0.0.92:9136/api/roxy/run
```
  curl -X POST http://127.0.0.1:8766/run \
    -H "X-ROXY-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"command\": \"test $i\"}" &
done
# Should see some 429 (rate limited) responses
```

### Test Streaming
```bash
curl http://127.0.0.1:8766/stream?q=hello \
  -H "X-ROXY-Token: $TOKEN"
```

## Verify Test Coverage
```bash
# Run tests with coverage
./run_tests.sh

# Open HTML coverage report
firefox htmlcov/index.html
# or
chromium htmlcov/index.html
```

## Check System Health

### Container Health
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### ROXY Core Logs
```bash
journalctl --user -u roxy-core -f
```

### Test Observability
```bash
# Check if observability is logging
ls -lh /home/mark/.roxy/logs/observability/

# View recent requests
cat /home/mark/.roxy/logs/observability/requests_$(date +%Y%m%d).jsonl | tail -5

# View recent errors
cat /home/mark/.roxy/logs/observability/errors_$(date +%Y%m%d).jsonl | tail -5
```

## Backup & Restore Testing

### Create Test Backup
```bash
./backup.sh
```

### List Available Backups
```bash
./restore.sh
```

### Test Restore (CAREFUL - this overwrites data!)
```bash
# Only run if you want to test restore
# ./restore.sh YYYYMMDD_HHMMSS
```

## Troubleshooting

### Tests Failing
```bash
# Check Python path
echo $PYTHONPATH

# Install missing dependencies
pip install -r requirements.txt

# Run tests with verbose output
./run_tests.sh -vv --tb=long
```

### Metrics Not Available
```bash
# Install Prometheus client
pip install prometheus-client

# Check if metrics are being collected
curl http://localhost:9091/metrics 2>/dev/null | head -20
```

### ROXY Core Not Running
```bash
# Check status
systemctl --user status roxy-core

# View logs
journalctl --user -u roxy-core -n 50

# Restart
systemctl --user restart roxy-core
```

### Container Issues
```bash
# Check container logs
docker logs roxy-chromadb --tail 50
docker logs roxy-postgres --tail 50
docker logs roxy-n8n --tail 50

# Restart unhealthy containers
docker restart roxy-chromadb
```

## Next Steps

1. ✅ Run tests to verify everything works
2. ✅ Set up automated backups (crontab)
3. ✅ Review API documentation
4. ⏭️ Add type hints (see IMPLEMENTATION_COMPLETE_PHASE1_6.md)
5. ⏭️ Set up Grafana dashboards (Week 2)
6. ⏭️ Implement security automation (Week 3)

## Success Criteria

- [ ] All tests pass (./run_tests.sh)
- [ ] Test coverage > 80%
- [ ] Backup/restore works
- [ ] API docs generated
- [ ] Metrics endpoint responds
- [ ] Authentication enforced
- [ ] Rate limiting active

Run through this checklist to verify the enhanced system is working properly!
