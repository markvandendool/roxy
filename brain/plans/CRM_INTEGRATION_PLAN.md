# ROXY CRM Integration Plan
## Project SKYBEAM — Phase 7 Implementation

**Status:** READY FOR IMPLEMENTATION
**Date:** 2026-01-10
**Author:** Project SKYBEAM

---

## Executive Summary

ROXY has two CRM paths available:

1. **MindSong Juke Hub CRM** — 77 production-ready React components (already built)
2. **ROXY Business MCP** — Supabase-backed CRM tools (already integrated)

This plan documents how to unify both systems for maximum capability.

---

## Current State

### MindSong CRM Components (77 total)
Location: `/home/mark/mindsong-juke-hub/src/components/crm/`

| Component | Purpose |
|-----------|---------|
| `ContactsManager.tsx` | Contact CRUD with search/filter |
| `DealsManager.tsx` | Deal pipeline management |
| `WorkflowBuilder.tsx` | Visual workflow automation |
| `CompanyManager.tsx` | Company/account management |
| `EngagementTimeline.tsx` | Activity timeline |
| `EmailTemplates.tsx` | Email template library |
| `TaskManager.tsx` | Task assignment/tracking |
| `LeadScoring.tsx` | AI-powered lead scoring |
| `ReportsDashboard.tsx` | Analytics & reporting |
| `ImportExport.tsx` | CSV/Excel import/export |
| + 67 more components | Full CRM suite |

### ROXY Business MCP Server
Location: `/home/mark/.roxy/mcp-servers/business/server.py`

| Tool | Function |
|------|----------|
| `crm_create_contact` | Create contact in Supabase |
| `crm_get_contacts` | Query contacts |
| `crm_create_deal` | Create deal |
| `crm_get_deals` | Query deals |
| `crm_get_analytics` | CRM analytics |
| `crm_get_workflows` | Automation workflows |
| `plane_create_issue` | Project management |
| `chatwoot_send_message` | Customer messaging |

### Supabase Tables (shared between MindSong & ROXY)

```sql
-- Existing tables (from mindsong-juke-hub)
crm_contacts
crm_deals
automation_workflows_crm

-- May need creation
crm_companies
crm_activities
crm_tasks
crm_email_templates
social_posts
ai_memories
approval_requests
```

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ROXY CRM UNIFIED ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐              ┌─────────────────────┐               │
│  │   MindSong Web UI   │              │   ROXY Voice/CLI    │               │
│  │   (React + Vite)    │              │   (MCP Tools)       │               │
│  └──────────┬──────────┘              └──────────┬──────────┘               │
│             │                                    │                          │
│             │    ┌───────────────────────────────┤                          │
│             │    │                               │                          │
│             ▼    ▼                               ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │                    SUPABASE (Unified Backend)               │            │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │            │
│  │  │ crm_contacts │  │  crm_deals   │  │ automation_  │      │            │
│  │  │              │  │              │  │ workflows    │      │            │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │              GHOST PROTOCOL (Real-time Sync)                │            │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │            │
│  │  │ ghost.crm.   │  │ ghost.crm.   │  │ ghost.crm.   │      │            │
│  │  │ contacts     │  │ deals        │  │ activity     │      │            │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │                 VISUALIZATION LAYER                          │            │
│  │  Mac Studio → Ghost Protocol Widget → Real-time CRM View    │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Phase 1: Verify Supabase Tables

```bash
# Check existing tables via REST API
curl -s "${SUPABASE_URL}/rest/v1/" \
  -H "apikey: ${SUPABASE_KEY}" | jq '.[]'
```

Required tables:
- [ ] `crm_contacts` — Verify exists
- [ ] `crm_deals` — Verify exists
- [ ] `crm_companies` — Create if missing
- [ ] `crm_activities` — Create if missing

### Phase 2: Voice Commands (Already Done)

Voice intents created in `/home/mark/.roxy/ops/voice_intents.yaml`:

| Voice Command | Action |
|---------------|--------|
| "show contacts" | List all contacts |
| "add contact John Smith" | Create new contact |
| "show leads" | Filter contacts by stage |
| "create deal Project X" | Create new deal |
| "crm analytics" | Show CRM stats |

### Phase 3: Ghost Protocol CRM Topics

Add to ghost publisher (`/home/mark/.roxy/services/ghost_publisher.py`):

```python
# CRM topics for real-time visualization
"ghost.crm.contacts"  # Contact changes
"ghost.crm.deals"     # Deal pipeline updates
"ghost.crm.activity"  # Activity stream
```

### Phase 4: MindSong Integration Points

The MindSong CRM components are already built. To use them with ROXY:

1. **Standalone Mode**: Run MindSong Juke Hub locally
   ```bash
   cd ~/mindsong-juke-hub
   pnpm dev
   # Access at http://localhost:5173
   ```

2. **Embedded Mode**: Embed CRM widgets in ROXY Control Panel
   - Use `RoxyPage.tsx` from MindSong
   - Import CRM components as needed

3. **Voice-Activated Mode**: Use ROXY voice commands
   - "Hey Roxy, show my deals"
   - "Hey Roxy, add contact from clipboard"

---

## Voice Workflow Examples

### Create Contact from Voice
```
User: "Hey Roxy, create contact John Smith from Acme Corp"
ROXY: [Extracts: first_name=John, last_name=Smith, company=Acme Corp]
ROXY: [Calls crm_create_contact]
ROXY: "Contact John Smith created at Acme Corp"
```

### Check Pipeline
```
User: "Hey Roxy, what's in my pipeline?"
ROXY: [Calls crm_get_deals]
ROXY: "You have 5 deals worth $45,000 total.
       2 in prospecting, 2 in proposal, 1 in negotiation."
```

### CRM Analytics
```
User: "Hey Roxy, CRM stats"
ROXY: [Calls crm_get_analytics]
ROXY: "You have 127 contacts, 23 deals worth $185,000,
       and 4 active automation workflows."
```

---

## Data Model

### Contact Stages (Lifecycle)
```
subscriber → lead → marketing_qualified_lead → sales_qualified_lead → opportunity → customer
```

### Deal Stages (Pipeline)
```
prospecting → qualification → proposal → negotiation → closed_won | closed_lost
```

### Integration Fields

| ROXY Field | MindSong Field | Supabase Column |
|------------|----------------|-----------------|
| first_name | firstName | first_name |
| last_name | lastName | last_name |
| email | email | email |
| company | companyName | company |
| stage | lifecycleStage | stage |
| deal_value | amount | value |

---

## Credentials Required

All credentials should be in `/home/mark/.roxy/vault/`:

| Credential | Environment Variable | Status |
|------------|---------------------|--------|
| Supabase URL | `SUPABASE_URL` | Configured |
| Supabase Key | `SUPABASE_ANON_KEY` | Configured |
| Plane API | `PLANE_API_KEY` | Optional |
| Chatwoot Token | `CHATWOOT_ACCESS_TOKEN` | Optional |

---

## Quick Start

### Test CRM from CLI
```bash
# Test via MCP
echo '{"tool": "crm_get_contacts", "params": {"limit": 5}}' | \
  python3 ~/.roxy/mcp-servers/business/server.py

# Or use voice
# "Hey Roxy, show contacts"
```

### Access MindSong CRM UI
```bash
cd ~/mindsong-juke-hub
pnpm dev
# Open http://localhost:5173/crm
```

---

## Metrics & KPIs

Track these in Grafana dashboard:

| Metric | Target |
|--------|--------|
| Contacts created (voice) | Track count |
| Deals closed | Track value |
| Response time | < 2s for voice commands |
| Supabase queries | Monitor latency |

---

## Next Steps

1. [ ] Verify Supabase tables exist
2. [ ] Test voice CRM commands
3. [ ] Add CRM topics to Ghost Protocol
4. [ ] Create Grafana CRM dashboard
5. [ ] Document MindSong CRM component usage

---

## Files Modified/Created

| File | Purpose |
|------|---------|
| `/home/mark/.roxy/mcp-servers/business/server.py` | CRM MCP tools |
| `/home/mark/.roxy/ops/voice_intents.yaml` | Voice commands |
| `/home/mark/.roxy/brain/plans/CRM_INTEGRATION_PLAN.md` | This plan |

---

*Project SKYBEAM — CRM Integration Plan v1.0*
