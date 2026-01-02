# ROXY Architecture Documentation

## Overview

ROXY (Roxy Omniscient Control System) is an autonomous AI assistant system with system control, browser automation, content pipeline, voice control, and social media automation capabilities.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ROXY Core Service                        │
│  (HTTP IPC Server - systemd user service)                  │
│  - Command routing                                          │
│  - Authentication & rate limiting                           │
│  - Request/response handling                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Security   │ │  Observability│ │ Rate Limiting│
│   Module     │ │   Module      │ │   Module     │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   ChromaDB   │ │    Ollama    │ │  PostgreSQL  │
│  (Vector DB) │ │   (LLM API)  │ │  (Database)  │
└──────────────┘ └──────────────┘ └──────────────┘
```

## Components

### 1. ROXY Core (`roxy_core.py`)

**Purpose**: Main HTTP IPC server for ROXY

**Responsibilities**:
- HTTP request handling
- Authentication and authorization
- Command routing
- Response generation
- Error handling

**Endpoints**:
- `GET /health` - Health check
- `POST /run` - Execute single command
- `POST /batch` - Execute batch commands
- `GET /stream` - Stream responses (SSE)

**Dependencies**:
- `roxy_commands.py` - Command parsing and execution
- `security.py` - Input sanitization
- `rate_limiting.py` - Rate limiting
- `observability.py` - Logging and metrics

### 2. Command Router (`roxy_commands.py`)

**Purpose**: Parse and route commands to appropriate handlers

**Command Types**:
- **Git**: `git status`, `git commit`, `git push`
- **OBS**: `start streaming`, `start recording`
- **RAG**: Natural language queries
- **System**: `health`, `status`
- **Content**: `briefing`, `clip <video>`

**Flow**:
```
User Input → parse_command() → Command Type → Handler → Response
```

### 3. Security Module (`security.py`)

**Purpose**: Input sanitization and output filtering

**Features**:
- Dangerous pattern blocking (rm -rf, sudo, etc.)
- Prompt injection detection
- PII detection and redaction
- Audit logging

### 4. Rate Limiting (`rate_limiting.py`)

**Purpose**: Prevent abuse and DoS attacks

**Features**:
- Token bucket algorithm
- Per-IP rate limiting
- Per-endpoint rate limiting
- Circuit breaker for external services

### 5. Observability (`observability.py`)

**Purpose**: Request/response logging and performance tracking

**Features**:
- Request logging
- Error logging
- Latency statistics
- Integration with Prometheus

### 6. Streaming (`streaming.py`)

**Purpose**: Server-Sent Events (SSE) streaming for LLM responses

**Features**:
- Real-time token streaming
- Ollama API integration
- RAG context injection
- Retry and circuit breaker protection

## Data Flow

### Command Execution Flow

```
1. HTTP Request → roxy_core.py
2. Authentication Check → security.py
3. Rate Limiting Check → rate_limiting.py
4. Command Parsing → roxy_commands.py
5. Command Execution → Handler (git/obs/rag/etc.)
6. Response Generation → roxy_core.py
7. Observability Logging → observability.py
8. HTTP Response → Client
```

### RAG Query Flow

```
1. User Query → roxy_core.py
2. Query Expansion → roxy_commands.py
3. Embedding Generation → DefaultEmbeddingFunction
4. Vector Search → ChromaDB
5. Context Retrieval → Top N results
6. LLM Query → Ollama API (with context)
7. Response Streaming → SSE events
8. Client receives tokens in real-time
```

## Infrastructure Components

### ChromaDB

**Purpose**: Vector database for RAG (Retrieval-Augmented Generation)

**Usage**:
- Store document embeddings
- Semantic search for context retrieval
- Collection: `mindsong_docs`

### Ollama

**Purpose**: Local LLM API for text generation

**Models Used**:
- `qwen2.5-coder:14b` - Code generation
- Other models as configured

### PostgreSQL

**Purpose**: Relational database for structured data

**Usage**:
- n8n workflow data
- Application data
- User preferences

### Redis

**Purpose**: Queue and cache

**Usage**:
- n8n job queue
- Rate limiting state
- Caching

## Security Architecture

### Authentication

- **Method**: Token-based (X-ROXY-Token header)
- **Storage**: `~/.roxy/secret.token`
- **Validation**: Mandatory (system fails to start without token)

### Input Sanitization

- **Pattern Matching**: Dangerous command detection
- **PII Detection**: SSN, email, credit card
- **Audit Logging**: All blocked commands logged

### Rate Limiting

- **Algorithm**: Token bucket
- **Scope**: Per-IP and per-endpoint
- **Response**: 429 Too Many Requests

## Monitoring & Observability

### Prometheus Metrics

- Request count by endpoint/status
- Request duration (histogram)
- Active requests (gauge)
- RAG queries counter
- Cache hits/misses
- Ollama API calls
- Error count by type

### Grafana Dashboards

- Request rate
- Request duration (P95)
- Active requests
- Error rate
- RAG queries
- Cache hit rate
- Ollama API calls
- Blocked commands

### Logging

- **Location**: `~/.roxy/logs/`
- **Files**:
  - `roxy_core.log` - Core service logs
  - `audit.log` - Security events
  - `observability/` - Request/response logs

## Deployment

### Systemd Service

- **Service**: `roxy-core.service`
- **Type**: User service
- **Location**: `~/.config/systemd/user/`
- **Status**: `systemctl --user status roxy-core`

### Docker Services

- **Compose File**: `compose/docker-compose.foundation.yml`
- **Services**: PostgreSQL, Redis, ChromaDB, n8n, Prometheus, Grafana
- **Network**: `roxy-network` (bridge)

## Related Documentation

- `docs/API.md` - API documentation
- `docs/INFRASTRUCTURE.md` - Infrastructure details
- `docs/DISASTER_RECOVERY.md` - Backup and restore procedures
- `docs/runbooks/` - Operational runbooks

