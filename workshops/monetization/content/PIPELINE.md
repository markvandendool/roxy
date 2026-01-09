# Content Pipeline Documentation

## Overview

Automated content generation pipeline for TikTok, YouTube Shorts, and YouTube videos.

## Quick Start

```bash
# Generate one video
cd ~/.roxy/workshops/monetization/content/engines
python3 faceless_video_engine.py

# Generate batch (21 videos for week)
for i in {1..21}; do
  python3 faceless_video_engine.py
  sleep 5
done
```

## Formats

### Vertical (TikTok, Shorts, Reels)
- **Resolution:** 1080x1920 (9:16)
- **Duration:** 15-60 seconds
- **Platform:** TikTok, YouTube Shorts, Instagram Reels
- **Templates:** `content/vertical/templates/`

### Horizontal (YouTube, Twitter)
- **Resolution:** 1920x1080 (16:9)
- **Duration:** 30-180 seconds
- **Platform:** YouTube, Twitter, LinkedIn
- **Templates:** `content/horizontal/templates/`

## Content Engines

### 1. Faceless Video Engine
**File:** `content/engines/faceless_video_engine.py`

**Niches Supported:**
- Coding tutorials
- AI/ML explanations
- Music theory lessons

**How It Works:**
1. Selects topic from niche
2. Generates script (30-60s read time)
3. Creates TTS voiceover
4. Adds background visuals
5. Composes final video with ffmpeg
6. Exports to `/tmp/faceless_videos/`

**Usage:**
```bash
# Default (random niche)
python3 faceless_video_engine.py

# Specific niche
python3 faceless_video_engine.py --niche=coding

# With background image
python3 faceless_video_engine.py --background=/path/to/image.jpg
```

### 2. 8K Theater Recording
**Location:** `automation/obs/theater-scenes/`

**Use For:** High-quality talking head videos, tutorials, demos

**Scenes Available:**
- Coding Tutorial (screen share + webcam)
- Product Demo (clean background)
- Podcast Setup (two cameras)
- Vertical TikTok (9:16 layout)
- Horizontal YouTube (16:9 layout)

**Record Video:**
```bash
# Start OBS with scene
python3 ~/.roxy/obs_controller.py set_scene "Coding Tutorial"

# Start recording
python3 ~/.roxy/obs_controller.py start_recording

# Present your content...

# Stop recording
python3 ~/.roxy/obs_controller.py stop_recording

# Video saved to: ~/Videos/
```

### 3. Screen Recording (No Face)
**For:** Quick tutorials, code walkthroughs

```bash
# Set screen-only scene
python3 ~/.roxy/obs_controller.py set_scene "Screen Only"

# Record
python3 ~/.roxy/obs_controller.py start_recording

# Stop
python3 ~/.roxy/obs_controller.py stop_recording
```

## Upload Workflow

### Manual Upload
1. Generate videos
2. Go to platform (YouTube, TikTok)
3. Upload from `/tmp/faceless_videos/` or `~/Videos/`
4. Use metadata from `metadata_*.json` files

### Automated Upload (n8n)
**File:** `automation/n8n/daily-video-generation.json`

**Flow:**
1. Cron trigger (6 AM, 2 PM, 8 PM)
2. Run faceless_video_engine.py
3. Upload to YouTube via API
4. Post to TikTok via web scraping
5. Tweet video link
6. Log in analytics

**Setup:**
```bash
# Import workflow to n8n
# Add credentials:
# - YouTube OAuth
# - TikTok session cookie
# - Twitter API

# Activate workflow
```

## Content Calendar

### Week 1: Foundation
| Day | Videos | Platform | Topic |
|-----|--------|----------|-------|
| Mon | 3 | TikTok | Python tips |
| Tue | 3 | TikTok | AI concepts |
| Wed | 3 | TikTok | Music theory |
| Thu | 1 | YouTube | Long tutorial |
| Fri | 3 | TikTok | Coding shortcuts |
| Sat | 0 | - | Review analytics |
| Sun | 0 | - | Plan next week |

### Scaling Up
- **Month 2:** 5 videos/day
- **Month 3:** 10 videos/day (batch generation)
- **Month 6:** 20 videos/day (hire editor)

## Asset Library

### Stock Footage
**Location:** `content/assets/stock-footage/`

**Free Sources:**
- Pexels.com (via API)
- Pixabay.com
- Videvo.net

**Download Script:**
```bash
cd content/assets
./download-stock-footage.sh coding 10
./download-stock-footage.sh ai 10
./download-stock-footage.sh music 10
```

### Background Music
**Location:** `content/assets/music/`

**Free Sources:**
- YouTube Audio Library
- Pixabay Music
- Free Music Archive

**Requirements:**
- Royalty-free
- Attribution (if needed)
- Suitable for background (not distracting)

### Fonts & Graphics
**Location:** `content/assets/fonts/`

**Free Fonts:**
- Roboto (Google Fonts)
- Montserrat (Google Fonts)
- Inter (Google Fonts)

## Optimization

### Video SEO
**Title Format:**
```
[Hook] | [Topic] in [Duration] Seconds
Example: "This Will Blow Your Mind | Recursion in 60 Seconds"
```

**Description Template:**
```
[Quick summary]

In this video:
• Point 1
• Point 2
• Point 3

[CTA: Subscribe, like, comment]

#hashtag1 #hashtag2 #hashtag3
```

**Tags:**
- Primary keyword
- Secondary keywords
- Niche tags
- Platform-specific tags

### Thumbnail Strategy
**For YouTube:**
- Bold text (3-5 words)
- High contrast
- Face (if showing face) or eye-catching graphic
- Bright colors

**Tools:**
- Canva (free templates)
- Photopea (free Photoshop alternative)
- GIMP (open source)

### Posting Schedule
**Best Times (EST):**
- **TikTok:** 6 AM, 2 PM, 8 PM
- **YouTube:** 12 PM, 6 PM
- **Instagram:** 11 AM, 7 PM

## Analytics

### Track Metrics
```bash
# Content performance CSV
echo "date,platform,video_id,views,likes,comments,shares,revenue" > content/analytics/video-metrics.csv

# Add entry
echo "$(date '+%Y-%m-%d'),TikTok,video123,1500,45,12,8,0" >> content/analytics/video-metrics.csv
```

### Review Weekly
```bash
# Top performers
cat content/analytics/video-metrics.csv | sort -t, -k4 -nr | head -10

# By platform
awk -F, 'NR>1 {platforms[$2]+=$4} END {for (p in platforms) print p": "platforms[p]" views"}' content/analytics/video-metrics.csv
```

## Scaling Content

### Hire Editor (Month 3+)
**Post on:**
- Upwork
- Fiverr
- r/forhire

**Rate:** $15-$30/hour

**Tasks:**
- Edit raw footage
- Add captions
- Color correction
- Thumbnail creation

### Batch Production
```bash
# Generate 100 videos overnight
cd content/engines
for i in {1..100}; do
  python3 faceless_video_engine.py &
  if (( $i % 10 == 0 )); then
    wait  # Wait for batch of 10 to complete
  fi
done
wait
```

### Content Repurposing
**Workflow:** `automation/n8n/content-repurposing.json`

**Flow:**
1. Upload long YouTube video
2. Extract 10 short clips
3. Add captions automatically
4. Post to TikTok/Shorts
5. Tweet highlights

## Tips

### Consistency > Perfection
- Post daily, even if not perfect
- Improve over time
- Algorithm rewards consistency

### Engage with Audience
- Reply to all comments (first hour)
- Ask questions in captions
- Create polls/quizzes

### Experiment
- Try different formats
- Test posting times
- A/B test thumbnails
- Iterate based on data

---

**Next:** Set up automation with [automation/n8n/README.md](../automation/n8n/README.md)
