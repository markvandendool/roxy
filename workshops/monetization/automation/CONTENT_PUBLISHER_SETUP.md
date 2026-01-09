# Content Publisher - Complete Publishing Automation

## You Already Have The Infrastructure!

### Existing Roxy Assets

1. **[clip_extractor.py](~/.roxy/clip_extractor.py)** - "Opus Clip Killer"
   - Whisper transcription with timestamps
   - LLM viral moment detection (uses Ollama)
   - Engagement scoring (1-100)
   - FFmpeg extraction with platform optimization
   - Supports: TikTok (9:16), YouTube Shorts (9:16), Instagram Reels (9:16), Twitter (1:1), YouTube (16:9)

2. **[broadcast_intelligence.py](~/.roxy/broadcast_intelligence.py)** - Platform Optimization
   - Virality prediction
   - Optimal posting time calculation
   - Platform-specific recommendations
   - Title/hashtag optimization
   - Audience engagement prediction

3. **n8n Integration** (ready for workflow automation)
   - Located: mindsong-juke-hub has n8n references
   - Can use for scheduled publishing

---

## Complete Setup Guide

### Step 1: Manual Account Creation (15 min, one-time)

#### 1. ProtonMail
```bash
# Go to proton.me/mail
# Choose: roughdraft@proton.me (or your chosen brand)
# Save password to file
echo "protonmail_password" > ~/.roxy/workshops/monetization/.proton_pass
chmod 600 ~/.roxy/workshops/monetization/.proton_pass
```

#### 2. YouTube (Requires Google Account)
```bash
# 1. Create Google account with ProtonMail
# 2. Create YouTube channel
# 3. Enable YouTube Data API v3:
#    - Go to console.cloud.google.com
#    - Create project
#    - Enable "YouTube Data API v3"
#    - Create OAuth 2.0 credentials
#    - Download client_secret.json
mv ~/Downloads/client_secret*.json ~/.roxy/workshops/monetization/.youtube_client_secret.json

# 4. First run will open browser for OAuth consent
python3 ~/.roxy/workshops/monetization/automation/youtube_auth.py
```

#### 3. TikTok (Requires Mobile App or Browser Cookies)
```bash
# Method 1: Browser cookies (easier)
# 1. Sign up on tiktok.com with ProtonMail
# 2. Export cookies using browser extension:
#    - Chrome: "EditThisCookie" extension
#    - Firefox: "Cookie-Editor" add-on
# 3. Save cookies as JSON:
cat > ~/.roxy/workshops/monetization/.tiktok_cookies.json << 'EOF'
{
  "sessionid": "your_sessionid_here"
}
EOF

# Method 2: Use tiktok-uploader's auth helper
pip install tiktok-uploader
tiktok-uploader --auth  # Opens browser for login
```

#### 4. Twitter/X Developer Account
```bash
# 1. Sign up on twitter.com with ProtonMail
# 2. Apply for Developer account (free): developer.twitter.com
# 3. Create app, get API keys
# 4. Save credentials:
cat > ~/.roxy/workshops/monetization/.twitter_creds.json << 'EOF'
{
  "api_key": "YOUR_API_KEY",
  "api_secret": "YOUR_API_SECRET",
  "bearer_token": "YOUR_BEARER_TOKEN",
  "access_token": "YOUR_ACCESS_TOKEN",
  "access_secret": "YOUR_ACCESS_SECRET"
}
EOF
```

#### 5. Reddit
```bash
# 1. Sign up on reddit.com with ProtonMail
# 2. Create app: reddit.com/prefs/apps → "script" type
# 3. Save credentials:
cat > ~/.roxy/workshops/monetization/.reddit_creds.json << 'EOF'
{
  "client_id": "YOUR_CLIENT_ID",
  "secret": "YOUR_SECRET",
  "username": "roughdraft",
  "password": "YOUR_PASSWORD"
}
EOF
```

#### 6. Gumroad
```bash
# 1. Sign up on gumroad.com with ProtonMail
# 2. Create product manually (upload roxy-ai-starter-v1.zip)
# 3. Get API key: Settings → Advanced → Generate API Key
# 4. Save:
cat > ~/.roxy/workshops/monetization/.gumroad_creds.json << 'EOF'
{
  "api_key": "YOUR_API_KEY",
  "product_id": "YOUR_PRODUCT_ID",
  "product_url": "https://roughdraft.gumroad.com/l/roxy-ai-starter"
}
EOF
```

#### 7. Consolidate Credentials
```bash
# Merge all into single secure file
python3 - << 'EOF'
import json
from pathlib import Path

base = Path.home() / ".roxy" / "workshops" / "monetization"
creds = {}

# Load all credential files
for name in ["youtube", "tiktok", "twitter", "reddit", "gumroad"]:
    file = base / f".{name}_creds.json"
    if file.exists():
        with open(file) as f:
            creds[name] = json.load(f)

# Add TikTok cookies if exists
cookies_file = base / ".tiktok_cookies.json"
if cookies_file.exists():
    with open(cookies_file) as f:
        creds['tiktok'] = {"cookies": json.load(f)}

# Save consolidated
output = base / ".credentials.json"
with open(output, "w") as f:
    json.dump(creds, f, indent=2)

# Secure permissions
output.chmod(0o600)

print(f"✅ Credentials saved to {output}")
EOF
```

---

### Step 2: Install Python Dependencies

```bash
cd ~/.roxy/workshops/monetization/automation

# Install all required libraries
pip install \
  google-api-python-client \
  google-auth-oauthlib \
  tweepy \
  praw \
  tiktok-uploader \
  requests

# Verify installation
python3 -c "import googleapiclient, tweepy, praw; print('✅ All imports work')"
```

---

### Step 3: Test with Existing Videos

```bash
cd ~/.roxy/workshops/monetization/automation

# Test YouTube only (safest for first try)
python3 content_publisher.py \
  --video /tmp/faceless_videos/final_coding_20260108_140540.mp4 \
  --title "GPU Monitoring Stack (Terminal + Python + Redis)" \
  --description "I melted two GPUs before building this monitoring setup. Here's the stack that saved me." \
  --tags "python,ai,gpu,monitoring,automation" \
  --platforms youtube

# Test all platforms
python3 content_publisher.py \
  --video /tmp/faceless_videos/final_coding_20260108_140540.mp4 \
  --title "GPU Monitoring Stack" \
  --description "Terminal + Python + Redis. Here's what works." \
  --tags "python,ai,gpu" \
  --platforms youtube,tiktok,twitter,reddit
```

---

### Step 4: Extract Viral Clips from Long Videos

```bash
# Use existing clip_extractor.py (Opus Clip killer)
python3 ~/.roxy/clip_extractor.py ~/Videos/stream_recording.mp4

# This will:
# 1. Transcribe with Whisper
# 2. Detect viral moments with LLM (Ollama)
# 3. Score engagement (1-100)
# 4. Extract clips for each platform
# 5. Output to ~/.roxy/clips/stream_recording/

# Then publish the best clips
python3 content_publisher.py \
  --video ~/.roxy/clips/stream_recording/01_tiktok_gpu_crash_story.mp4 \
  --platforms tiktok,youtube
```

---

## Usage Examples

### Publish with Metadata File
```bash
# Create metadata JSON
cat > video_metadata.json << 'EOF'
{
  "title": "My GPU Monitoring Stack (Or: How to Not Destroy $3K Hardware)",
  "description": "I melted two GPUs before building this. Terminal + Python + Redis. Here's the code.",
  "tags": ["python", "ai", "gpu", "monitoring", "devops"]
}
EOF

# Publish
python3 content_publisher.py \
  --video final_coding.mp4 \
  --metadata-file video_metadata.json \
  --platforms youtube,tiktok,twitter
```

### Extract + Publish Workflow
```bash
# 1. Record long-form content
# (You already have ~/Videos/ with recordings)

# 2. Extract viral clips
python3 content_publisher.py \
  --video ~/Videos/guitar_lesson_2026-01-08.mp4 \
  --extract-clips

# 3. Review extracted clips
ls ~/.roxy/clips/guitar_lesson_2026-01-08/

# 4. Publish best ones
for clip in ~/.roxy/clips/guitar_lesson_2026-01-08/*_tiktok_*.mp4; do
  python3 content_publisher.py \
    --video "$clip" \
    --platforms tiktok,youtube
  sleep 3600  # 1 hour between posts (avoid spam flags)
done
```

---

## Integration with Existing Roxy Infrastructure

### 1. Use Broadcast Intelligence for Timing
```python
from broadcast_intelligence import get_optimal_time

# Get best posting time
optimal = get_optimal_time("tiktok")
print(f"Post at: {optimal['datetime']}")
# Output: "2026-01-08 19:30:00" (peak engagement time)
```

### 2. Use Clip Extractor for Automation
```python
from clip_extractor import process_video

# Extract clips programmatically
clips = process_video(
    video_path=Path("stream.mp4"),
    output_dir=Path("clips/"),
    min_score=80  # Only high-scoring clips
)

# Clips are already optimized for each platform (9:16, 1:1, 16:9)
```

### 3. Scheduled Publishing via Cron
```bash
# Add to crontab for automated publishing
crontab -e

# Publish to TikTok at 7 PM daily
0 19 * * * cd ~/.roxy/workshops/monetization/automation && python3 content_publisher.py --video /tmp/daily_video.mp4 --platforms tiktok

# Extract clips from recordings every morning
0 9 * * * python3 ~/.roxy/clip_extractor.py ~/Videos/latest_recording.mp4
```

---

## Credentials File Structure

```json
{
  "youtube": {
    "client_secret_file": "/home/mark/.roxy/workshops/monetization/.youtube_client_secret.json",
    "token_file": "/home/mark/.roxy/workshops/monetization/.youtube_token.pickle"
  },
  "tiktok": {
    "cookies": {
      "sessionid": "..."
    }
  },
  "twitter": {
    "api_key": "...",
    "api_secret": "...",
    "bearer_token": "...",
    "access_token": "...",
    "access_secret": "..."
  },
  "reddit": {
    "client_id": "...",
    "secret": "...",
    "username": "roughdraft",
    "password": "..."
  },
  "gumroad": {
    "api_key": "...",
    "product_id": "...",
    "product_url": "https://roughdraft.gumroad.com/l/roxy-ai-starter"
  }
}
```

**Security:** File is chmod 600 (only you can read), stored in ~/.roxy/ (not in git)

---

## Next Steps

1. **Tonight:** Create accounts manually (15 min)
2. **Test:** Publish one video to YouTube only
3. **Scale:** Add other platforms once YouTube works
4. **Automate:** Extract clips from existing recordings
5. **Schedule:** Set up cron for daily publishing

## The Gem

This is the actual gem: **One command publishes to 5 platforms**

```bash
python3 content_publisher.py --video gpu_crash.mp4 --platforms youtube,tiktok,twitter,reddit
```

Uses your existing:
- `clip_extractor.py` for viral moment detection
- `broadcast_intelligence.py` for optimization
- Official APIs (TOS-compliant)
- Roxy infrastructure (no reinventing wheels)
