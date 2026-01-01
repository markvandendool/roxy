# ROXY Architecture

## System Overview

ROXY is a permanent, learning, resident AI assistant with autonomous capabilities, voice interaction, and extensible tool integration.

## Core Components

### 🧠 Intelligence Layer

#### JARVIS Core (`services/jarvis_core.py`)
- Permanent AI brain
- Persistent memory (SQLite)
- Learning and adaptation
- Conversation management

#### ROXY Core (`services/roxy_core.py`)
- Main orchestration
- Service coordination
- Event handling
- System integration

#### Memory Systems (`services/memory/`)
- **Episodic Memory**: Event-based memories
- **Semantic Memory**: Knowledge and facts
- **Working Memory**: Active context
- **Consolidation**: Memory optimization

#### Learning Systems (`services/learning/`)
- Pattern recognition
- Adaptive behavior
- Knowledge synthesis
- Self-improvement

### 🎤 Voice Layer

#### Text-to-Speech (`voice/tts/`)
- Converts text to speech
- Multiple voice options
- Streaming support

#### Speech-to-Text (`voice/transcription/`)
- Real-time transcription
- Multiple engine support
- Wake word detection

#### Voice Router (`voice/router.py`)
- Routes voice commands
- Intent recognition
- Command execution

### 🤖 Agent Layer

#### Agent Framework (`agents/framework/`)
- Base agent architecture
- Agent orchestration
- Inter-agent communication
- State management

#### Specialized Agents
- **Browser Agent**: Web automation
- **Desktop Agent**: Desktop automation
- **OBS Agent**: Streaming automation
- **Repo Agent**: Code repository management

### 🔧 Service Layer

#### Orchestration
- `services/orchestrator.py`: Service coordination
- `services/eventbus.py`: Event system
- `services/mcp_registry.py`: MCP server registry

#### System Services
- `services/system/`: System management (14 services)
- `services/scheduler/`: Task scheduling (10 services)
- `services/health_monitor.py`: Health monitoring
- `services/observability.py`: Observability

### 🛠️ Tool Layer (MCP Servers)

#### Core MCP Servers
- `mcp-servers/browser/`: Browser automation
- `mcp-servers/desktop/`: Desktop automation
- `mcp-servers/email/`: Email handling
- `mcp-servers/voice/`: Voice services
- `mcp-servers/content/`: Content processing
- `mcp-servers/obs/`: OBS integration

## Data Flow

```
User Input (Voice/Text)
    ↓
Voice Router / Conversation Engine
    ↓
Intent Recognition
    ↓
Agent Orchestrator
    ↓
Specialized Agent
    ↓
MCP Server / Service
    ↓
Action Execution
    ↓
Memory Storage
    ↓
Response Generation
```

## Communication Patterns

### Event Bus
- Pub/sub event system
- Service decoupling
- Real-time updates

### MCP Protocol
- Model Context Protocol
- Tool integration
- Standardized interfaces

### Agent Communication
- Direct messaging
- Shared state
- Collaborative planning

## Data Storage

### Persistent Memory
- SQLite database (`data/jarvis_memory.db`)
- Conversation history
- Learned facts
- User preferences

### Knowledge Base
- ChromaDB for semantic search
- Vector embeddings
- Context retrieval

### Runtime Data
- `data/`: Runtime data (not in git)
- `logs/`: Application logs
- `backups/`: System backups

## Configuration

### Environment Variables
- `.env`: Environment configuration
- Service-specific configs

### JSON Configuration
- `config/agents.json`: Agent configuration
- `config/learning.json`: Learning parameters
- `config/monitoring.json`: Monitoring config
- `config/performance.json`: Performance tuning
- `config/tasks.json`: Task definitions

## Deployment

### Services
- Systemd services for core components
- Docker Compose for infrastructure
- Health monitoring and auto-restart

### Dependencies
- Python 3.12+
- System dependencies (see requirements)
- GPU drivers (for acceleration)

## Security

- Secrets management (Infisical)
- Access control
- Security hardening
- Network security

## Performance

- GPU acceleration
- Async operations
- Caching strategies
- Resource optimization
