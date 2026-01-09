# n8n Automation README

## Overview

n8n workflows for automated content generation, sales funnels, and customer engagement.

## Setup

### Install n8n
```bash
# Via Docker (recommended)
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Or via npm
npm install -g n8n
n8n start
```

### Access
Open: http://localhost:5678

## Workflows

### 1. Daily Video Generation
**File:** `daily-video-generation.json`

**Trigger:** Cron (6 AM, 2 PM, 8 PM)

**Flow:**
1. Execute Python script (faceless_video_engine.py)
2. Read generated video metadata
3. Upload to YouTube via API
4. Post to TikTok (via browser automation)
5. Tweet video link
6. Log to analytics CSV

**Setup:**
1. Import JSON to n8n
2. Add credentials:
   - YouTube OAuth
   - TikTok session cookie
   - Twitter API v2
3. Set file paths
4. Activate workflow

### 2. Product Sales Funnel
**File:** `product-sales-funnel.json`

**Trigger:** Gumroad webhook (on sale)

**Flow:**
1. Receive webhook from Gumroad
2. Send welcome email with download link
3. Add to email list (Listmonk)
4. Send day 3 follow-up (ask for review)
5. Send day 7 upsell (other products)
6. Log sale in revenue tracker

**Setup:**
1. Import JSON
2. Add Gumroad webhook URL to product settings
3. Configure email credentials (SMTP)
4. Set Listmonk API key
5. Activate

### 3. Content Repurposing
**File:** `content-repurposing.json`

**Trigger:** Manual or scheduled

**Flow:**
1. Download long YouTube video
2. Split into 10 clips (ffmpeg)
3. Add captions (Whisper API)
4. Generate thumbnails
5. Upload to TikTok/Shorts queue
6. Schedule posts

**Setup:**
1. Import JSON
2. Add YouTube credentials
3. Add OpenAI API key (for Whisper)
4. Set output directory
5. Test manually first

## Credentials

### YouTube OAuth
1. Go to: https://console.cloud.google.com
2. Create project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Add to n8n: Settings → Credentials → YouTube OAuth2

### TikTok (Web Scraping)
1. Login to TikTok in browser
2. Open DevTools → Application → Cookies
3. Copy `sessionid` cookie
4. Add to n8n as HTTP Header Auth

### Twitter API
1. Apply for developer account: https://developer.twitter.com
2. Create app
3. Get API Key, Secret, Access Token
4. Add to n8n: Twitter API credentials

### Gumroad
1. Go to: https://gumroad.com/settings/advanced
2. Create webhook
3. URL: `http://your-n8n.com/webhook/gumroad-sales`
4. Events: `sale.succeeded`

## Usage

### Trigger Manually
1. Open workflow in n8n
2. Click "Execute Workflow" button
3. Check execution log

### Schedule
1. Open workflow
2. Edit Cron node
3. Set schedule (e.g., `0 6,14,20 * * *` for 6 AM, 2 PM, 8 PM)
4. Activate workflow

### Monitor
```bash
# Check n8n logs
docker logs n8n | tail -50

# Check execution history
# n8n UI → Executions tab
```

## Troubleshooting

### Workflow fails
- Check credentials are valid
- Verify API rate limits
- Check file paths exist
- Review error message in execution log

### YouTube upload fails
- Re-authorize OAuth (token may have expired)
- Check video file size (max 256GB)
- Verify quota remaining (10,000 units/day)

### Webhook not triggering
- Verify webhook URL in Gumroad settings
- Check n8n is accessible from internet (use ngrok if local)
- Test with curl

## Advanced

### Custom Workflow
1. Create new workflow in n8n
2. Add trigger (Cron, Webhook, Manual)
3. Add nodes (HTTP Request, Execute Command, etc.)
4. Connect nodes
5. Test and activate

### Integration with Roxy
```python
# In Roxy skill, trigger n8n workflow
import requests

def trigger_n8n_workflow(workflow_id, data):
    response = requests.post(
        f"http://localhost:5678/webhook/{workflow_id}",
        json=data
    )
    return response.json()

# Example
trigger_n8n_workflow("daily-video-gen", {"niche": "coding"})
```

---

**Next:** Set up cron jobs with [automation/cron/README.md](../cron/README.md)
