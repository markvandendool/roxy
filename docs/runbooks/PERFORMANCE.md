# ROXY Performance Tuning Guide

## Overview

This guide covers performance optimization strategies for ROXY.

## Metrics to Monitor

### Key Performance Indicators (KPIs)

- **Request Latency**: P50, P95, P99
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests
- **Cache Hit Rate**: Percentage of cache hits
- **Resource Utilization**: CPU, memory, disk

### Monitoring Tools

- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Docker Stats**: Container resource usage
- **System Tools**: `htop`, `iostat`, `netstat`

## Optimization Strategies

### 1. Caching

**Enable Semantic Caching**:
- Cache frequent RAG queries
- Cache LLM responses
- Use Redis for distributed caching

**Configuration**:
```python
# Enable cache in config.json
{
  "caching_enabled": true,
  "cache_ttl": 3600
}
```

### 2. Database Optimization

**PostgreSQL**:
- Add indexes for frequent queries
- Tune `shared_buffers` and `work_mem`
- Use connection pooling

**ChromaDB**:
- Limit collection size
- Use batch operations
- Optimize embedding dimensions

### 3. Model Selection

**Faster Models**:
- Use smaller models for simple queries
- Use quantized models
- Cache model responses

**Model Recommendations**:
- **Fast**: `qwen2.5-coder:7b` (smaller, faster)
- **Balanced**: `qwen2.5-coder:14b` (default)
- **Quality**: `qwen2.5-coder:32b` (slower, better quality)

### 4. Resource Limits

**Docker Compose**:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '0.5'
      memory: 1G
```

**Adjust Based on**:
- Workload patterns
- Available system resources
- Performance requirements

### 5. Connection Pooling

**PostgreSQL**:
- Use connection pooler (PgBouncer)
- Limit max connections
- Reuse connections

**Ollama**:
- Keep connections alive
- Use HTTP/2 if available
- Batch requests when possible

### 6. Query Optimization

**RAG Queries**:
- Limit context size
- Use hybrid search (semantic + keyword)
- Cache frequent queries

**Command Execution**:
- Batch multiple commands
- Use streaming for long responses
- Optimize command parsing

## Performance Testing

### Load Testing

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Run load test
ab -n 1000 -c 10 -H "X-ROXY-Token: YOUR_TOKEN" \
  -p request.json -T application/json \
  http://127.0.0.1:8766/run
```

### Stress Testing

```bash
# Use stress test script
python3 ~/.roxy/stress_test_comprehensive.py
```

### Benchmarking

```bash
# Measure response times
time curl -H "X-ROXY-Token: YOUR_TOKEN" \
  -X POST -d '{"command":"hello"}' \
  http://127.0.0.1:8766/run
```

## Troubleshooting Performance

### High Latency

1. **Check Database**: Slow queries?
2. **Check LLM**: Model too large?
3. **Check Network**: Connection issues?
4. **Check Resources**: CPU/memory constraints?

### High Memory Usage

1. **Limit ChromaDB**: Reduce memory limit
2. **Clear Cache**: Restart services
3. **Optimize Queries**: Reduce context size

### High CPU Usage

1. **Optimize Models**: Use smaller models
2. **Enable Caching**: Reduce redundant work
3. **Scale Horizontally**: Add more instances

## Best Practices

1. **Monitor Continuously**: Use Prometheus/Grafana
2. **Set Alerts**: Alert on high latency/error rate
3. **Regular Testing**: Run load tests regularly
4. **Optimize Incrementally**: Make small changes, measure impact
5. **Document Changes**: Keep performance notes

## Related Documentation

- `docs/INFRASTRUCTURE.md` - Infrastructure details
- `docs/API.md` - API documentation
- `docs/runbooks/TROUBLESHOOTING.md` - Troubleshooting guide

