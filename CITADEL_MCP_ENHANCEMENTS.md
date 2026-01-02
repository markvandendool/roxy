# CITADEL MCP Servers - Supabase Integration Enhancements

## Overview

Enhanced all CITADEL Phase 6-8 MCP servers with Supabase integration patterns found in the mindsong-juke-hub repository. All servers now use the same database patterns and can leverage existing CRM infrastructure.

## Changes Summary

### 1. Business MCP Server (`mcp-servers/business/server.py`)

#### Enhanced Tools:
- **`business_get_contacts`**: Now supports filtering by stage (subscriber, lead, marketing_qualified_lead, etc.)
- **`crm_get_deals`**: New tool to get deals with stage filtering and total value calculation
- **`crm_create_deal`**: New tool to create deals with contact association
- **`crm_get_workflows`**: New tool to get automation workflows with status filtering
- **`crm_get_analytics`**: New tool to get comprehensive CRM analytics (contacts count, deals value, active workflows)

#### Supabase Integration:
- Uses same Supabase URL/key as mindsong-juke-hub
- Queries `crm_contacts`, `crm_deals`, `automation_workflows_crm` tables
- Fallback to REST API when `supabase-py` not installed
- Matches exact patterns from CRM components

### 2. Social MCP Server (`mcp-servers/social/server.py`)

#### Enhanced Tools:
- **`social_get_analytics`**: Now queries Supabase `social_posts` table for analytics
- **`youtube_get_video_info`**: New tool to get YouTube video information using Data API v3
- **`social_store_post`**: New tool to store social media posts in Supabase for tracking

#### Supabase Integration:
- Stores social media posts in `social_posts` table
- Tracks engagement and reach metrics
- Supports YouTube, Discord, Telegram, Postiz platforms
- Graceful fallback if table doesn't exist yet

### 3. AI Orchestrator MCP Server (`mcp-servers/ai-orchestrator/server.py`)

#### Enhanced Tools:
- **`ai_create_memory`**: Now uses Supabase `ai_memories` table with Mem0 fallback
- **`ai_get_memories`**: Queries Supabase first, falls back to Mem0 API
- **`ai_request_approval`**: Stores approval requests in Supabase `approval_requests` table
- **`ai_get_approval_status`**: Queries Supabase for approval status

#### Supabase Integration:
- Persistent memory storage in `ai_memories` table
- Approval request tracking in `approval_requests` table
- Fallback to Mem0 API if Supabase not available
- Matches patterns from mindsong-juke-hub AI components

## Database Tables Used

### Existing Tables (from mindsong-juke-hub):
- `crm_contacts` - Contact management
- `crm_deals` - Deal pipeline
- `automation_workflows_crm` - CRM automation workflows
- `ai_response_cache` - AI response caching
- `ai_usage_logs` - AI usage tracking

### New Tables (may need to be created):
- `social_posts` - Social media post tracking
- `ai_memories` - Persistent AI memories
- `approval_requests` - Human-in-the-loop approvals

## Integration Patterns

### 1. Supabase Client Pattern
```python
from supabase import create_client, Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
response = supabase.table('table_name').select('*').execute()
```

### 2. REST API Fallback Pattern
```python
import requests
headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}
response = requests.get(f'{SUPABASE_URL}/rest/v1/table_name', headers=headers)
```

### 3. Error Handling
- Graceful fallback when tables don't exist
- Clear error messages
- Logging for debugging

## Configuration

All servers use environment variables:
- `SUPABASE_URL` or `VITE_SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` or `VITE_SUPABASE_ANON_KEY` - Supabase anonymous key
- Platform-specific keys (YouTube, Discord, Telegram, etc.)

## Benefits

1. **Unified Data Storage**: All CITADEL data in same Supabase instance as mindsong-juke-hub
2. **Existing Infrastructure**: Leverages existing CRM tables and patterns
3. **Consistency**: Same patterns across all MCP servers
4. **Flexibility**: REST API fallback when Python client not available
5. **Scalability**: Can easily add more tools using same patterns

## Next Steps

1. **Create Missing Tables**: If `social_posts`, `ai_memories`, `approval_requests` don't exist, create them in Supabase
2. **Test Integrations**: Test each MCP server with actual Supabase credentials
3. **Add More Tools**: Extend with more CRM features (segments, activities, etc.)
4. **Documentation**: Add API documentation for each tool
5. **Monitoring**: Add logging/monitoring for API calls

## Example Usage

### Business MCP:
```python
# Get contacts
result = await business_get_contacts(limit=10, stage='lead')

# Create deal
result = await crm_create_deal(
    name="New Deal",
    value=5000.0,
    contact_id="contact-uuid",
    stage="prospecting"
)

# Get analytics
result = await crm_get_analytics()
```

### Social MCP:
```python
# Get YouTube video info
result = await youtube_get_video_info(video_id="dQw4w9WgXcQ")

# Store post
result = await social_store_post(
    platform="youtube",
    content="Check out this video!",
    post_id="video-id",
    engagement=1000,
    reach=5000
)
```

### AI Orchestrator:
```python
# Create memory
result = await ai_create_memory(
    user_id="user-123",
    memory_text="User prefers email communication",
    metadata={"source": "conversation"}
)

# Request approval
result = await ai_request_approval(
    action="send_email",
    description="Send marketing email to 1000 contacts",
    context={"campaign_id": "campaign-123"}
)
```

## Files Modified

- `mcp-servers/business/server.py` - Enhanced with 5 new CRM tools
- `mcp-servers/social/server.py` - Added YouTube info and Supabase storage
- `mcp-servers/ai-orchestrator/server.py` - Added Supabase memory and approval storage

## Related Documentation

- `MINDSONG_API_INTEGRATIONS.md` - Catalog of existing API integrations
- `CITADEL_COMPLETE.md` - Overall CITADEL epic completion status


