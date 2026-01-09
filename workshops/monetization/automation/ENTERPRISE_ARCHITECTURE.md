# StackKraft Enterprise Content Distribution System
## Military-Grade, Self-Hosted, Zero Vendor Lock-In

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTENT INGESTION LAYER                       │
│  - Opus Clip Killer (clip_extractor.py) - Whisper + LLM        │
│  - Broadcast Intelligence (virality prediction, optimization)    │
│  - FFmpeg pipeline (multi-platform encoding)                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MESSAGE QUEUE (NATS)                         │
│  - JetStream enabled (persistence, replay)                       │
│  - Subjects: content.extract, content.optimize, content.publish │
│  - Dead letter queue for failed posts                            │
│  - Exactly-once delivery semantics                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION (n8n)                             │
│  - 42 existing workflows                                         │
│  - Webhook triggers from NATS                                    │
│  - Error handling + retry logic                                  │
│  - Rate limiting per platform                                    │
│  - Schedule optimization (best posting times)                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
   ┌────────┐     ┌────────┐    ┌─────────┐    ┌────────┐
   │TikTok  │     │YouTube │    │Instagram│    │Twitter │
   │Content │     │Data    │    │Graph    │    │API v2  │
   │API     │     │API v3  │    │API      │    │        │
   └────────┘     └────────┘    └─────────┘    └────────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              PERSISTENCE LAYER (PostgreSQL)                      │
│  Tables:                                                         │
│  - posts (id, platform, video_id, status, published_at)        │
│  - analytics (views, likes, comments, shares, revenue)          │
│  - queue (pending posts, retry count, next_attempt)             │
│  - rate_limits (platform, endpoint, remaining, reset_at)        │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│           MONITORING (Prometheus + Grafana)                      │
│  Metrics:                                                        │
│  - Posts per platform per hour                                  │
│  - API rate limit consumption                                   │
│  - Success/failure rates                                        │
│  - Queue depth                                                  │
│  - Average engagement per post                                  │
│  - Revenue attribution                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## OFFICIAL PLATFORM APIS (Enterprise Tier)

### 1. TikTok Content Posting API
**Application:** https://developers.tiktok.com/
- **Tier:** Business/Commercial Use
- **Rate Limits:** 100 posts/day (free), 1000/day (paid)
- **Justification:** AI music technology platform, educational content distribution
- **Approval Time:** 3-7 business days
- **Cost:** FREE (business tier), $500/mo (enterprise unlimited)

### 2. YouTube Data API v3
**Application:** https://console.cloud.google.com/
- **Tier:** Standard (10,000 quota units/day = ~100 uploads)
- **Quota Increase:** Request via GCP support (justify business case)
- **Cost:** FREE up to quota, then $0.016 per 1,000 units
- **OAuth 2.0:** Full automation support

### 3. Instagram Graph API
**Application:** https://developers.facebook.com/
- **Requirements:** Facebook Business Account + Instagram Business Account
- **Rate Limits:** 200 posts/day (business), 1000/day (enterprise)
- **Features:** Carousel posts, Reels, Stories
- **Cost:** FREE

### 4. Twitter API v2
**Application:** https://developer.twitter.com/
- **Tier:** Free (1500 posts/month), Basic ($100/mo - 3000/mo), Pro ($5000/mo - 300k/mo)
- **For 300/day = 9000/month:** Need Pro tier ($5000/mo) OR Basic + rate limiting
- **Alternative:** Free tier with strategic posting (50/day)

---

## DATABASE SCHEMA (PostgreSQL)

```sql
-- Content posts tracking
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    clip_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_post_id VARCHAR(255),
    title TEXT,
    description TEXT,
    video_path TEXT NOT NULL,
    thumbnail_path TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, queued, posted, failed
    scheduled_at TIMESTAMP,
    published_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_at);

-- Analytics tracking
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    post_id INT REFERENCES posts(id),
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    watch_time_seconds BIGINT DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    revenue_cents INT DEFAULT 0,
    synced_at TIMESTAMP DEFAULT NOW()
);

-- Rate limiting tracking
CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    limit_total INT NOT NULL,
    limit_remaining INT NOT NULL,
    reset_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, endpoint)
);

-- Posting schedule optimization
CREATE TABLE optimal_times (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    day_of_week INT NOT NULL, -- 0=Sunday
    hour INT NOT NULL, -- 0-23
    avg_engagement DECIMAL(5,2),
    sample_size INT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, day_of_week, hour)
);
```

---

## NATS JetStream Configuration

```bash
# Create streams for content pipeline
nats stream add CONTENT_EXTRACT \
  --subjects "content.extract.*" \
  --storage file \
  --retention limits \
  --max-age 7d

nats stream add CONTENT_PUBLISH \
  --subjects "content.publish.*" \
  --storage file \
  --retention limits \
  --max-age 7d \
  --max-msgs-per-subject 1000

# Create consumers
nats consumer add CONTENT_PUBLISH publish_worker \
  --filter "content.publish.*" \
  --ack explicit \
  --max-deliver 5 \
  --max-ack-pending 100
```

---

## n8n PRODUCTION WORKFLOWS

### Workflow: Content Extraction Pipeline
```
Trigger: NATS message (content.extract.request)
  ↓
Execute: clip_extractor.py (Whisper + Llama3)
  ↓
Process: broadcast_intelligence.py (optimize metadata)
  ↓
Store: Video files → MinIO, metadata → PostgreSQL
  ↓
Publish: NATS message (content.publish.queue)
```

### Workflow: Multi-Platform Publisher
```
Trigger: NATS message (content.publish.queue)
  ↓
Check: Rate limits (PostgreSQL)
  ↓
Branch by platform:
  ├─ TikTok → Content Posting API
  ├─ YouTube → Data API v3  
  ├─ Instagram → Graph API
  └─ Twitter → API v2
  ↓
Update: PostgreSQL (status=posted, platform_post_id)
  ↓
Schedule: Analytics sync (1hr, 24hr, 7d)
```

### Workflow: Analytics Aggregator
```
Trigger: Cron (every 1 hour)
  ↓
Query: All posted content from last 24hrs
  ↓
For each platform:
  ├─ TikTok Analytics API
  ├─ YouTube Analytics API
  ├─ Instagram Insights API  
  └─ Twitter Engagement API
  ↓
Update: PostgreSQL analytics table
  ↓
Calculate: Optimal posting times
  ↓
Alert: If engagement drops >20%
```

---

## GRAFANA DASHBOARDS

### Content Performance Dashboard
- Posts per platform (last 24hrs, 7d, 30d)
- Engagement rate trends
- Revenue attribution
- Top performing clips
- Queue depth and processing time

### Operations Dashboard  
- API rate limit consumption
- Success/failure rates per platform
- Error types and frequency
- System resource utilization
- NATS queue metrics

---

## DEPLOYMENT

### Initialize Database
```bash
psql -h localhost -U roxy -d roxy_db -f /home/mark/.roxy/workshops/monetization/automation/schema.sql
```

### Configure NATS
```bash
/home/mark/.roxy/workshops/monetization/automation/setup_nats_streams.sh
```

### Import n8n Workflows
```bash
cd ~/.roxy/workshops/monetization/automation/n8n
for workflow in *.json; do
  curl -X POST http://localhost:5678/api/v1/workflows/import \
    -H "Content-Type: multipart/form-data" \
    -F "file=@$workflow"
done
```

### Apply for Platform APIs
```bash
python3 /home/mark/.roxy/workshops/monetization/automation/apply_for_apis.py
```

---

## SCALING TO 300 POSTS/DAY

**Free Tier (0-50 posts/day):**
- YouTube: 100/day (quota)
- Instagram: 25/day (soft limit)
- Twitter: 50/day (free tier)
- TikTok: Requires Business API application

**Paid Tier ($100-200/mo for 300/day):**
- YouTube: Increase quota (free, justify use case)
- Instagram: 200/day (business account, free)
- Twitter: Basic tier $100/mo (3000/month = 100/day) + strategic posting
- TikTok: Business API approval (100/day free, then $500/mo unlimited)

**RECOMMENDATION:**
1. Apply for all official APIs NOW (3-7 day approval)
2. Start with 50 posts/day (free tier) while APIs approve
3. Scale to 300/day once Business/Enterprise tiers approved
4. Use NATS queue to buffer during rate limit windows
5. Schedule posts at optimal engagement times (not evenly distributed)

---

## MONITORING ALERTS

```yaml
# Prometheus alerts
groups:
  - name: content_pipeline
    rules:
      - alert: PostFailureRateHigh
        expr: rate(posts_failed_total[5m]) > 0.1
        annotations:
          summary: "Post failure rate >10% in last 5 minutes"
      
      - alert: QueueDepthHigh
        expr: nats_stream_messages{stream="CONTENT_PUBLISH"} > 500
        annotations:
          summary: "NATS queue depth >500, processing backlog"
      
      - alert: RateLimitApproaching
        expr: api_rate_limit_remaining / api_rate_limit_total < 0.2
        annotations:
          summary: "API rate limit <20% remaining"
```

---

**THIS IS ENTERPRISE ARCHITECTURE. NOT TOY AUTOMATION.**
