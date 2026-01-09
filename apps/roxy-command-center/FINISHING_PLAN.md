# ROXY Command Center - Master Finishing Plan
**Created**: 2026-01-09
**Status**: ACTIVE

---

## 🎯 VISION

The Command Center is your **single cockpit** for:
1. **Talk to Roxy** - Voice + text with prominent "Start Conversation" control
2. **Drive Execution** - Progressions timeline with one-click dispatch
3. **Unified Communications** - One inbox across ~20 sources with ultra-fast reply + automation

---

## 📐 HOME SCREEN LAYOUT

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [ROXY]  Mode: Local │ GPU0: 38°C │ GPU1: 56°C │ CPU: 6% │ ⚙️ Settings │
├──────────────────┬─────────────────────────────┬────────────────────────┤
│                  │                             │                        │
│  UNIFIED INBOX   │      ROXY CHAT              │   EXECUTION & STATUS   │
│                  │                             │                        │
│  [All] [SMS] [📧]│  Context chips:             │   PROGRESSIONS         │
│                  │  • Mode: local              │   ┌──────────────────┐ │
│  ┌────────────┐  │  • Model: qwen2.5:14b       │   │ ▶ Deploy v2.1    │ │
│  │ Mom (SMS)  │  │  • Focus: MindSong          │   │   queued → run   │ │
│  │ Hey did... │  │                             │   └──────────────────┘ │
│  └────────────┘  │  ┌─────────────────────┐    │   ┌──────────────────┐ │
│  ┌────────────┐  │  │ Roxy: I found 3     │    │   │ ✓ Backup DB      │ │
│  │ GitHub     │  │  │ issues in the...    │    │   │   completed 2m   │ │
│  │ PR review  │  │  └─────────────────────┘    │   └──────────────────┘ │
│  └────────────┘  │  ┌─────────────────────┐    │                        │
│  ┌────────────┐  │  │ You: Check the GPU  │    │   ALERTS               │
│  │ Slack      │  │  │ temps and...        │    │   ┌──────────────────┐ │
│  │ @channel.. │  │  └─────────────────────┘    │   │ ⚠ GPU1 > 55°C    │ │
│  └────────────┘  │                             │   └──────────────────┘ │
│                  │  [🎤 Voice] [____________]  │                        │
│  Quick Actions:  │  [Run] [Summarize] [Plan]   │   [Refresh] [Logs]     │
│  • Roxy draft    │                             │                        │
│  • Convert task  │                             │                        │
│                  │                             │                        │
└──────────────────┴─────────────────────────────┴────────────────────────┘
```

---

## 🏗️ ARCHITECTURE

### Event-Driven Unified Communications

```
CONNECTORS                    EVENT BUS              STORAGE        UI
─────────────────────────────────────────────────────────────────────────
SMS (Twilio API)     ─┐                         
Email (IMAP)         ─┤                              ┌─────────┐
Slack (Bot)          ─┼─→  NATS JetStream  ─→       │Postgres │ ─→  GTK4
Discord (Bot)        ─┤    ConversationEvent        │ (truth) │     WebSocket
GitHub (Webhooks)    ─┤                              └─────────┘
Telegram (Bot)       ─┘                              
                                                     ┌─────────┐
                           n8n subscribes ───────────│  Redis  │
                           (auto-triage,             │(realtime)│
                            Roxy drafts)             └─────────┘
```

### Canonical Event Schema

```python
ConversationEvent {
    id: UUID
    source: str          # "sms", "email", "slack", "github", etc.
    thread_id: str       # Unified thread identifier
    from_addr: str       # Sender
    to_addr: str         # Recipient
    timestamp: datetime
    content: str
    attachments: list
    metadata: dict       # Source-specific data
    roxy_draft: str?     # AI-generated reply draft
    status: str          # "new", "read", "replied", "archived"
}
```

---

## 📊 PHASED BUILD PLAN

### Phase 0: Telemetry Trust (Current Session)
**Goal**: Never wonder if data is flowing

- [x] normalize_status() function
- [x] Debug strip in header
- [x] Console logging for poll/update cycle
- [ ] Visual timestamp in cards (proves updates are live)
- [ ] "Raw Payload" debug panel (toggle in settings)

### Phase 1: Home = Roxy Chat + Progressions (1-2 weeks)
**Goal**: Core cockpit functionality

- [ ] Roxy chat pane (text input + history)
- [ ] Voice button (placeholder → wyoming integration)
- [ ] Progressions list widget
- [ ] Dispatch button → roxy-core endpoint
- [ ] Status stream (queued → running → done)
- [ ] Alerts panel (current alerts)

### Phase 2: Unified Inbox v1 (2-3 weeks)
**Goal**: 3-6 easy sources

| Source | Integration Method | Priority |
|--------|-------------------|----------|
| Email | IMAP polling | P0 |
| SMS | Twilio API | P0 |
| Slack | Bot + webhooks | P1 |
| Discord | Bot + webhooks | P1 |
| GitHub | Webhooks | P1 |
| Telegram | Bot API | P2 |

- [ ] ConversationEvent schema in Postgres
- [ ] NATS JetStream topic: `inbox.events`
- [ ] Inbox sidebar widget
- [ ] Reply composer (routes back through correct connector)
- [ ] "Roxy Draft" quick action

### Phase 3: Unified Inbox v2 (3-4 weeks)
**Goal**: High-value social + automation

| Source | Integration Method | Priority |
|--------|-------------------|----------|
| Instagram | Official API | P1 |
| WhatsApp Business | Official API | P1 |
| YouTube comments | API | P2 |
| X/Twitter | API | P2 |
| LinkedIn | API (limited) | P3 |

- [ ] n8n flows: auto-triage incoming
- [ ] n8n flows: "Roxy drafts reply" on new message
- [ ] n8n flows: "1-click approve + send"
- [ ] Thread grouping by person/topic

### Phase 4: iMessage Relay (Optional, Gated)
**Goal**: iPhone messages if you accept operational risk

**Reality Check**:
- Apple has NO official iMessage server API
- Requires Mac relay (BlueBubbles, AirMessage, or similar)
- Unofficial/fragile, may break with macOS updates

**Plan Stance**:
- Only attempt AFTER Phases 1-3 are solid
- Requires always-on Mac (Mini or VM)
- Accept: this could break at any time

---

## 🔧 IMMEDIATE NEXT ACTIONS

### Today (Session Continuation)

1. **Verify telemetry updates visually**
   - CPU card shows ticking seconds
   - GPU temps change when under load
   
2. **Remove debug noise after confirming**
   - Keep console logs but remove timestamp from card display
   
3. **Git commit the normalize_status() fix**
   ```bash
   cd ~/.roxy/apps/roxy-command-center
   git add -A
   git commit -m "fix: normalize daemon schema for CPU/GPU display"
   git push
   ```

### Next Session: Phase 1 Kickoff

1. **Add Roxy Chat pane** (center column)
   - Text input with send button
   - Scrollable history
   - Calls `POST /run` to roxy-core
   
2. **Add Progressions panel** (right column)
   - List of recent progressions
   - Dispatch button
   - Live status updates

---

## 📋 TOP 20 MESSAGE SOURCES (To Prioritize)

Please confirm/edit this list:

| # | Source | Has API? | Difficulty | Your Priority |
|---|--------|----------|------------|---------------|
| 1 | Email (personal) | IMAP | Easy | ? |
| 2 | Email (work) | IMAP/API | Easy | ? |
| 3 | SMS | Twilio | Easy | ? |
| 4 | iMessage | Mac relay | Hard | ? |
| 5 | Slack | Bot | Easy | ? |
| 6 | Discord | Bot | Easy | ? |
| 7 | GitHub | Webhooks | Easy | ? |
| 8 | Telegram | Bot | Easy | ? |
| 9 | WhatsApp | Business API | Medium | ? |
| 10 | Instagram DM | API | Medium | ? |
| 11 | Facebook Messenger | API | Medium | ? |
| 12 | YouTube comments | API | Medium | ? |
| 13 | X/Twitter | API | Medium | ? |
| 14 | LinkedIn | Limited API | Hard | ? |
| 15 | Reddit | API | Medium | ? |
| 16 | Twitch chat | API | Easy | ? |
| 17 | Signal | Bridge | Hard | ? |
| 18 | Teams | API | Medium | ? |
| 19 | Matrix | Native | Easy | ? |
| 20 | RSS/Newsletters | Feed | Easy | ? |

---

## 🎛️ BACKBONE DECISION

Chief's options:

**Option A: Custom Roxy Inbox** (Recommended)
- Full control, aligns with "AAA cockpit" goal
- Uses existing NATS/Postgres/n8n
- More work, maximum customization

**Option B: Chatwoot-first**
- Fastest to polished inbox UI
- Open-source omnichannel platform
- Wire Roxy into drafting/routing

**Option C: Matrix-first**
- Maximum unification via bridges
- Command Center becomes Matrix client + Roxy overlay
- Complex but powerful

**YOUR CHOICE**: ________________

---

## ✅ SUCCESS CRITERIA

### Phase 0 Complete When:
- [ ] CPU/GPU cards update every second with visible proof
- [ ] Console shows `[Data] CPU:X% GPUs:N` continuously
- [ ] Debug strip in header shows timestamp

### Phase 1 Complete When:
- [ ] Can type to Roxy and get response in chat pane
- [ ] Progressions list shows at least 3 items
- [ ] Dispatch button triggers execution
- [ ] Status updates from queued → running → done

### Phase 2 Complete When:
- [ ] Inbox shows messages from 3+ sources
- [ ] Can reply from Command Center
- [ ] Reply routes through correct connector
- [ ] "Roxy Draft" generates AI response

---

## 📝 NOTES

- **iMessage stance**: Defer to Phase 4, accept it's unofficial
- **Backbone preference**: Custom Roxy Inbox (my recommendation)
- **Infrastructure ready**: Postgres, Redis, NATS, n8n, Grafana all running
- **Thin client principle**: GTK app calls one endpoint, roxy-core handles complexity

---

*This plan will be updated as decisions are made.*
