# ROXY Core API Documentation

## Overview

ROXY Core provides an HTTP IPC API for interacting with the ROXY AI assistant. All endpoints support both versioned (`/v1/*`) and unversioned paths for backward compatibility.

## Base URL

- **Local Development**: `http://127.0.0.1:8766`
- **Localhost**: `http://localhost:8766`

## Authentication

All endpoints except `/health` require authentication via the `X-ROXY-Token` header:

```bash
curl -H "X-ROXY-Token: YOUR_TOKEN" http://127.0.0.1:8766/run
```

## Rate Limiting

Rate limiting is enabled by default:
- **Per IP**: 10 requests/second with burst of 20
- **Per Endpoint**: Varies by endpoint
- **Response**: `429 Too Many Requests` when limit exceeded

## Endpoints

### Health Check

#### GET `/health` or `/v1/health`

Check if the service is healthy.

**Authentication**: Not required

**Response**:
```json
{
  "status": "ok",
  "service": "roxy-core",
  "timestamp": "2026-01-02T12:00:00Z"
}
```

**Example**:
```bash
curl http://127.0.0.1:8766/health
```

### Execute Command

#### POST `/run` or `/v1/run`

Execute a single command.

**Authentication**: Required

**Request Body**:
```json
{
  "command": "hello roxy"
}
```

**Response**:
```json
{
  "status": "success",
  "result": "Hello! How can I help you?",
  "response_time": 0.123,
  "timestamp": "2026-01-02T12:00:00Z"
}
```

**Example**:
```bash
curl -X POST \
  -H "X-ROXY-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "hello roxy"}' \
  http://127.0.0.1:8766/run
```

**Error Responses**:
- `403 Forbidden`: Invalid or missing token
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Batch Commands

#### POST `/batch` or `/v1/batch`

Execute multiple commands in batch.

**Authentication**: Required

**Request Body**:
```json
{
  "commands": ["hello roxy", "git status"]
}
```

**Response**:
```json
{
  "status": "success",
  "commands": [
    {
      "command": "hello roxy",
      "result": "Hello! How can I help you?",
      "status": "success"
    },
    {
      "command": "git status",
      "result": "On branch main...",
      "status": "success"
    }
  ],
  "total_time": 0.456
}
```

**Example**:
```bash
curl -X POST \
  -H "X-ROXY-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"commands": ["hello roxy", "git status"]}' \
  http://127.0.0.1:8766/batch
```

### Streaming (SSE)

#### GET `/stream?q=COMMAND` or `/v1/stream?q=COMMAND`

Execute a command and stream the response as Server-Sent Events.

**Authentication**: Required

**Query Parameters**:
- `q` (required): The command to execute

**Response**: `text/event-stream`

**Example**:
```bash
curl -N \
  -H "X-ROXY-Token: YOUR_TOKEN" \
  "http://127.0.0.1:8766/stream?q=hello%20roxy"
```

**SSE Event Format**:
```
event: token
data: {"token": "Hello", "done": false}

event: token
data: {"token": "!", "done": false}

event: complete
data: {"done": true}
```

## Error Handling

All errors follow this format:

```json
{
  "status": "error",
  "message": "Error description",
  "error_type": "ErrorType"
}
```

### Common Error Types

- `AuthenticationError`: Invalid or missing token
- `RateLimitExceeded`: Rate limit exceeded
- `ServerError`: Internal server error
- `ValidationError`: Invalid request format

## API Versioning

The API supports versioned endpoints:
- `/v1/run` - Version 1 endpoint
- `/run` - Unversioned (backward compatible)

Both endpoints provide the same functionality. Use versioned endpoints for future compatibility.

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
- File: `/opt/roxy/openapi.yaml`
- View online: Use Swagger UI or similar tool

## Examples

### Python Client

```python
import requests

BASE_URL = "http://127.0.0.1:8766"
TOKEN = "YOUR_TOKEN"

headers = {"X-ROXY-Token": TOKEN}

# Execute command
response = requests.post(
    f"{BASE_URL}/run",
    headers=headers,
    json={"command": "hello roxy"}
)
print(response.json())

# Batch commands
response = requests.post(
    f"{BASE_URL}/batch",
    headers=headers,
    json={"commands": ["hello roxy", "git status"]}
)
print(response.json())

# Stream response
response = requests.get(
    f"{BASE_URL}/stream?q=hello%20roxy",
    headers=headers,
    stream=True
)
for line in response.iter_lines():
    if line:
        print(line.decode())
```

### JavaScript/Node.js Client

```javascript
const fetch = require('node-fetch');

const BASE_URL = 'http://127.0.0.1:8766';
const TOKEN = 'YOUR_TOKEN';

// Execute command
async function runCommand(command) {
  const response = await fetch(`${BASE_URL}/run`, {
    method: 'POST',
    headers: {
      'X-ROXY-Token': TOKEN,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ command })
  });
  return response.json();
}

// Stream response
async function streamCommand(command) {
  const response = await fetch(`${BASE_URL}/stream?q=${encodeURIComponent(command)}`, {
    headers: { 'X-ROXY-Token': TOKEN }
  });
  
  const reader = response.body;
  // Process SSE events...
}
```

## Best Practices

1. **Always use authentication**: Include `X-ROXY-Token` header
2. **Handle rate limits**: Implement exponential backoff for 429 responses
3. **Use versioned endpoints**: Prefer `/v1/*` endpoints for future compatibility
4. **Stream for long responses**: Use `/stream` endpoint for long-running commands
5. **Batch when possible**: Use `/batch` for multiple commands
6. **Monitor response times**: Track `response_time` in responses

## Support

For issues or questions:
- Check logs: `/home/mark/.roxy/logs/roxy_core.log`
- Health check: `GET /health`
- See documentation: `docs/INFRASTRUCTURE.md`

