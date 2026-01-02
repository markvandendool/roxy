# ROXY Troubleshooting Guide

## Common Issues

### ROXY Core Not Starting

**Symptoms**:
- `systemctl --user status roxy-core` shows failed
- Port 8766 not listening

**Diagnosis**:
```bash
# Check service status
systemctl --user status roxy-core

# Check logs
journalctl --user -u roxy-core -n 50

# Check if port is in use
lsof -i :8766
```

**Solutions**:
1. **Missing Auth Token**:
   ```bash
   # Generate token
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > ~/.roxy/secret.token
   chmod 600 ~/.roxy/secret.token
   systemctl --user restart roxy-core
   ```

2. **Port Already in Use**:
   ```bash
   # Find process using port
   lsof -i :8766
   # Kill process or change port in config.json
   ```

3. **Permission Issues**:
   ```bash
   # Check file permissions
   ls -la ~/.roxy/
   # Fix permissions
   chmod 600 ~/.roxy/secret.token
   chmod 644 ~/.roxy/config.json
   ```

### Authentication Failures

**Symptoms**:
- 403 Forbidden responses
- "Invalid or missing token" errors

**Diagnosis**:
```bash
# Check token file
cat ~/.roxy/secret.token

# Test with curl
curl -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" http://127.0.0.1:8766/health
```

**Solutions**:
1. **Token Mismatch**: Regenerate token
2. **Token File Missing**: Create token file
3. **Header Name**: Ensure using `X-ROXY-Token` header

### Rate Limiting Issues

**Symptoms**:
- 429 Too Many Requests
- Requests being blocked

**Diagnosis**:
```bash
# Check rate limit config
cat ~/.roxy/config.json | grep rate_limit

# Check logs for rate limit events
grep -i "rate limit" ~/.roxy/logs/roxy_core.log
```

**Solutions**:
1. **Increase Limits**: Edit `config.json`
2. **Wait**: Rate limits reset over time
3. **Check IP**: Rate limiting is per-IP

### ChromaDB Connection Issues

**Symptoms**:
- RAG queries failing
- "Connection refused" errors

**Diagnosis**:
```bash
# Check ChromaDB container
docker ps | grep chromadb

# Check ChromaDB health
curl http://localhost:8000/api/v1/heartbeat

# Check logs
docker logs roxy-chromadb --tail 50
```

**Solutions**:
1. **Container Not Running**: `docker-compose up -d chromadb`
2. **Port Conflict**: Check if port 8000 is available
3. **Data Directory**: Check `~/.roxy/chroma_db` permissions

### Ollama API Issues

**Symptoms**:
- LLM responses failing
- Timeout errors

**Diagnosis**:
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# Check if model is available
curl http://localhost:11434/api/show -d '{"name": "qwen2.5-coder:14b"}'
```

**Solutions**:
1. **Ollama Not Running**: Start Ollama service
2. **Model Not Available**: Pull model: `ollama pull qwen2.5-coder:14b`
3. **Timeout**: Increase timeout in streaming.py

### n8n Restart Loop

**Symptoms**:
- n8n container constantly restarting
- Database connection errors

**Diagnosis**:
```bash
# Check n8n logs
docker logs roxy-n8n --tail 50

# Check PostgreSQL connection
docker exec roxy-postgres psql -U roxy -d n8n -c "SELECT 1;"

# Check password
grep POSTGRES_PASSWORD .env
```

**Solutions**:
1. **Database Not Initialized**: Create n8n database
2. **Password Mismatch**: Verify password in `.env` and docker-compose
3. **Network Issues**: Check docker network connectivity

## Performance Issues

### Slow Response Times

**Diagnosis**:
```bash
# Check Prometheus metrics
curl http://localhost:9091/metrics | grep roxy_request_duration

# Check system resources
docker stats
htop
```

**Solutions**:
1. **Resource Limits**: Increase Docker resource limits
2. **Cache**: Enable caching for frequent queries
3. **Model Size**: Use smaller/faster models

### High Memory Usage

**Diagnosis**:
```bash
# Check memory usage
docker stats
free -h

# Check ChromaDB memory
docker stats roxy-chromadb
```

**Solutions**:
1. **Limit ChromaDB**: Reduce memory limit in docker-compose
2. **Clear Cache**: Restart services
3. **Optimize Queries**: Reduce RAG query size

## Log Analysis

### View Recent Logs

```bash
# ROXY Core logs
tail -f ~/.roxy/logs/roxy_core.log

# Audit logs
tail -f ~/.roxy/logs/audit.log

# Observability logs
tail -f ~/.roxy/logs/observability/requests_*.jsonl
```

### Search Logs

```bash
# Search for errors
grep -i error ~/.roxy/logs/roxy_core.log

# Search for specific command
grep "git status" ~/.roxy/logs/roxy_core.log

# Search for blocked commands
grep BLOCKED ~/.roxy/logs/audit.log
```

## Health Checks

### Manual Health Check

```bash
/opt/roxy/scripts/health_check.sh
```

### Service Health

```bash
# ROXY Core
curl http://127.0.0.1:8766/health

# ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# PostgreSQL
docker exec roxy-postgres pg_isready -U roxy

# Redis
docker exec roxy-redis redis-cli ping
```

## Getting Help

1. **Check Documentation**: `docs/` directory
2. **Review Logs**: `~/.roxy/logs/`
3. **Health Check**: Run health check script
4. **Service Status**: Check all services with `systemctl` and `docker ps`

