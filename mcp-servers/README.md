# CITADEL MCP Servers

Model Context Protocol (MCP) servers for ROXY CITADEL epic phases 6-8.

## Overview

These MCP servers provide tools for:
- **Business Automation** (Phase 7): CRM, Plane, Chatwoot integrations
- **Social Integration** (Phase 6): YouTube, Discord, Telegram, Postiz
- **AI Excellence** (Phase 8): LangGraph, Mem0, Human-in-the-Loop

All servers use Supabase for data storage, matching patterns from mindsong-juke-hub.

## Setup

### 1. Install Dependencies

```bash
# Activate your virtual environment
source /opt/roxy/venv/bin/activate

# Install MCP and dependencies
pip install mcp supabase requests
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Supabase (same as mindsong-juke-hub)
SUPABASE_URL=https://rlbltiuswhlzjvszhvsc.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Or use VITE_ prefix (for compatibility)
VITE_SUPABASE_URL=https://rlbltiuswhlzjvszhvsc.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Social Media APIs
YOUTUBE_API_KEY=your-youtube-api-key
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_WEBHOOK_URL=your-discord-webhook-url
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Business Tools
PLANE_API_URL=http://localhost:8000/api/v1
PLANE_API_KEY=your-plane-api-key
CHATWOOT_API_URL=http://localhost:3000/api/v1
CHATWOOT_ACCESS_TOKEN=your-chatwoot-token

# AI Tools
MEM0_API_URL=http://localhost:8000
LANGGRAPH_API_URL=http://localhost:8123
```

### 3. Create Supabase Tables

Run the migration script in your Supabase SQL editor:

```bash
# Copy the SQL file
cat mcp-servers/supabase_migrations.sql

# Or run directly in Supabase dashboard:
# 1. Go to SQL Editor
# 2. Paste contents of supabase_migrations.sql
# 3. Run the query
```

This creates:
- `social_posts` - Social media post tracking
- `ai_memories` - Persistent AI memory storage
- `approval_requests` - Human-in-the-loop approvals

### 4. Test Integrations

```bash
# Run the test script
python3 mcp-servers/test_integrations.py
```

## Running MCP Servers

### Business MCP Server

```bash
python3 mcp-servers/business/server.py
```

**Available Tools:**
- `crm_create_contact` - Create a CRM contact
- `business_get_contacts` - Get contacts (with stage filtering)
- `crm_get_deals` - Get deals with value calculations
- `crm_create_deal` - Create a deal
- `crm_get_workflows` - Get automation workflows
- `crm_get_analytics` - Get CRM analytics
- `plane_create_issue` - Create Plane project issue
- `business_get_issues` - Get Plane issues
- `chatwoot_send_message` - Send Chatwoot message

### Social MCP Server

```bash
python3 mcp-servers/social/server.py
```

**Available Tools:**
- `social_schedule_post` - Schedule social media post
- `youtube_upload_video` - Upload video to YouTube
- `youtube_get_video_info` - Get YouTube video information
- `discord_send_message` - Send Discord message
- `telegram_send_message` - Send Telegram message
- `social_store_post` - Store post in Supabase
- `social_get_analytics` - Get social media analytics

### AI Orchestrator MCP Server

```bash
python3 mcp-servers/ai-orchestrator/server.py
```

**Available Tools:**
- `ai_create_memory` - Create persistent memory (Supabase/Mem0)
- `ai_get_memories` - Retrieve memories
- `ai_run_workflow` - Run LangGraph workflow
- `ai_request_approval` - Request human approval
- `ai_get_approval_status` - Get approval status
- `ai_unified_gateway_call` - Unified MCP gateway

## Integration with Cursor/Claude

Add to your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "roxy-business": {
      "command": "python3",
      "args": ["/opt/roxy/mcp-servers/business/server.py"],
      "env": {
        "SUPABASE_URL": "https://rlbltiuswhlzjvszhvsc.supabase.co",
        "SUPABASE_ANON_KEY": "your-key-here"
      }
    },
    "roxy-social": {
      "command": "python3",
      "args": ["/opt/roxy/mcp-servers/social/server.py"],
      "env": {
        "SUPABASE_URL": "https://rlbltiuswhlzjvszhvsc.supabase.co",
        "SUPABASE_ANON_KEY": "your-key-here",
        "YOUTUBE_API_KEY": "your-youtube-key"
      }
    },
    "roxy-ai-orchestrator": {
      "command": "python3",
      "args": ["/opt/roxy/mcp-servers/ai-orchestrator/server.py"],
      "env": {
        "SUPABASE_URL": "https://rlbltiuswhlzjvszhvsc.supabase.co",
        "SUPABASE_ANON_KEY": "your-key-here"
      }
    }
  }
}
```

## Database Schema

### social_posts
- `id` (UUID) - Primary key
- `platform` (TEXT) - Platform name
- `content` (TEXT) - Post content
- `post_id` (TEXT) - External post ID
- `media_url` (TEXT) - Media URL
- `engagement` (INTEGER) - Engagement count
- `reach` (INTEGER) - Reach count
- `created_at` (TIMESTAMPTZ) - Creation timestamp

### ai_memories
- `id` (UUID) - Primary key
- `user_id` (TEXT) - User identifier
- `memory_text` (TEXT) - Memory content
- `metadata` (JSONB) - Additional metadata
- `importance_score` (FLOAT) - Memory importance
- `created_at` (TIMESTAMPTZ) - Creation timestamp

### approval_requests
- `id` (UUID) - Primary key
- `action` (TEXT) - Action to approve
- `description` (TEXT) - Description
- `context` (JSONB) - Additional context
- `status` (TEXT) - Status (pending, approved, rejected)
- `created_at` (TIMESTAMPTZ) - Creation timestamp

## Troubleshooting

### "Module not found: mcp"
```bash
pip install mcp
```

### "Supabase credentials not configured"
Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` environment variables.

### "Table does not exist"
Run `supabase_migrations.sql` in your Supabase SQL editor.

### "supabase-py not installed"
The servers will fallback to REST API automatically, or install:
```bash
pip install supabase
```

## Related Documentation

- `CITADEL_MCP_ENHANCEMENTS.md` - Enhancement details
- `MINDSONG_API_INTEGRATIONS.md` - Existing API integrations
- `CITADEL_COMPLETE.md` - Overall CITADEL status







