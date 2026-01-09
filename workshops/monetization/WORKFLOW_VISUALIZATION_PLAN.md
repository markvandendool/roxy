# StackKraft Workflow Visualization Plan

## n8n Integration Strategy

### Why n8n?
- **Visual workflow builder** - drag & drop automation
- **Self-hosted** - full control, no cloud dependencies
- **REST API** - can embed/display workflows in command center
- **Built-in nodes** - Twitter, YouTube, Reddit, webhooks, etc.
- **Real-time monitoring** - watch executions live

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ROXY COMMAND CENTER                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  Video Monitor │  │ n8n Workflows  │  │ Platform Stats │ │
│  │   (GPU/CPU)    │  │  (Live View)   │  │   (Analytics)  │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   n8n Server     │
                    │  localhost:5678  │
                    └──────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  [Twitter API]         [TikTok API]          [YouTube API]
```

### Workflows to Build

1. **Content Publishing Pipeline**
   - Trigger: New video in /tmp/faceless_videos/
   - Extract metadata (clip_extractor.py)
   - Optimize for each platform (broadcast_intelligence.py)
   - Upload to TikTok, YouTube Shorts, Instagram Reels
   - Post Twitter thread with link
   - Log results

2. **Engagement Monitor**
   - Trigger: Every 30 minutes
   - Fetch analytics from all platforms
   - Calculate virality score
   - Send alerts for trending posts
   - Update dashboard

3. **Comment Responder**
   - Trigger: New comment webhook
   - Run through Ollama for sentiment analysis
   - Generate contextual reply
   - Post response (if sentiment > 0.6)
   - Log interaction

### Command Center Integration

**Option 1: Embedded iframe**
```html
<iframe src="http://localhost:5678/workflow/123" 
        width="100%" height="600px" 
        style="border: none;">
</iframe>
```

**Option 2: Custom Dashboard (Better)**
- n8n REST API → fetch workflow status
- Show active executions in real-time
- Display success/failure counts
- Visualize workflow graph with D3.js/Mermaid
- Click to open full n8n editor

**Option 3: Hybrid**
- Main view: Custom dashboard with stats
- Expandable panel: Full n8n iframe for editing
- Keyboard shortcut to toggle (Ctrl+Shift+N)

### Installation Plan

```bash
# 1. Install n8n
npm install -g n8n

# 2. Configure for local use
export N8N_BASIC_AUTH_ACTIVE=false  # Internal use only
export N8N_HOST=localhost
export N8N_PORT=5678

# 3. Start n8n
n8n start &

# 4. Create systemd service for auto-start
sudo systemctl enable n8n.service
```

### API Integration Examples

**Get workflow executions:**
```python
import requests

resp = requests.get('http://localhost:5678/api/v1/executions')
executions = resp.json()['data']

for exec in executions:
    print(f"{exec['workflowName']}: {exec['status']}")
```

**Trigger workflow via webhook:**
```bash
curl -X POST http://localhost:5678/webhook/upload-video \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/tmp/faceless_videos/final_coding.mp4"}'
```

### Command Center Widget Mockup

```
┌──────────────────────────────────────────────┐
│  🔄 ACTIVE WORKFLOWS                   [+]  │
├──────────────────────────────────────────────┤
│  📹 Video Publisher          ✅ Running      │
│     Last: 2m ago → TikTok, YouTube           │
│     Next: 28m (scheduled)                    │
│                                              │
│  📊 Analytics Sync           ✅ Running      │
│     Last: 15m ago → 15 new views             │
│     Next: 15m (every 30m)                    │
│                                              │
│  💬 Comment Responder        ⏸️  Paused      │
│     Last: 2h ago → 3 replies sent            │
│     [Resume]                                 │
├──────────────────────────────────────────────┤
│  📈 LAST 24H                                 │
│     ✅ 12 executions    ❌ 1 failed          │
│     🎥 6 videos uploaded                     │
│     💬 24 comments processed                 │
└──────────────────────────────────────────────┘
```

### Next Steps

1. **Tonight**: Manual TikTok upload (learn the process)
2. **Tomorrow**: Install n8n, create first workflow
3. **This Week**: Build all 3 core workflows
4. **Next Week**: Integrate into command center

### Benefits

✅ **Visual automation** - See the flow, not just code
✅ **Quick iterations** - Change workflows without editing Python
✅ **Error handling** - Built-in retry, logging, alerting
✅ **Monitoring** - Real-time execution visibility
✅ **Scalable** - Add new platforms easily
✅ **Command center ready** - REST API for live updates

### Alternative: Keep Python-only?

**Pros of staying with Python:**
- No new dependencies
- Full control
- Faster execution
- Already built (content_publisher.py)

**Cons:**
- No visual workflow editing
- Manual logging/monitoring
- Harder to debug complex flows
- No built-in retry/error handling

**Recommendation**: Hybrid approach
- Use n8n for orchestration & monitoring
- Keep Python scripts for heavy lifting (clip_extractor, broadcast_intelligence)
- n8n calls Python scripts as child processes
- Best of both worlds!
