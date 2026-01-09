# Monetization Workshop - Troubleshooting Guide

## Product Packaging Issues

### Problem: package_products.sh fails with "Permission denied"
**Solution:**
```bash
chmod +x ~/.roxy/workshops/monetization/products/package_products.sh
./package_products.sh
```

### Problem: ZIP files are too large
**Root Cause:** Including unnecessary dependencies or node_modules

**Solution:**
```bash
# Edit package_products.sh to exclude large folders
# Add to tar exclude list:
--exclude='node_modules' \
--exclude='__pycache__' \
--exclude='.git'
```

### Problem: Secrets not being sanitized
**Check:** Run grep to verify no API keys in output
```bash
cd ~/mindsong-products
unzip -q roxy-ai-infrastructure-v1.zip
grep -r "sk-" roxy-ai-infrastructure/ || echo "Clean ✓"
grep -r "password.*=" roxy-ai-infrastructure/ || echo "Clean ✓"
```

**Fix:** Add patterns to sanitization section:
```bash
# In package_products.sh
sed -i 's/YOUR_SECRET_PATTERN/REDACTED/g' "$file"
```

## Content Generation Issues

### Problem: faceless_video_engine.py fails with "ffmpeg not found"
**Solution:**
```bash
# Install ffmpeg
sudo apt install ffmpeg

# Verify
ffmpeg -version
```

### Problem: TTS voice sounds robotic
**Current:** Using espeak (basic TTS)

**Upgrade Path:**
```bash
# Option 1: Google TTS (free tier)
pip install gtts
# Update script to use: from gtts import gTTS

# Option 2: ElevenLabs (best quality, paid)
pip install elevenlabs
# Add API key to ~/.roxy/.env
# Update script to use: import elevenlabs
```

### Problem: Videos have no visuals
**Root Cause:** Missing background images/b-roll

**Solution:**
```bash
# Download free stock footage
mkdir -p content/assets/stock-footage
cd content/assets/stock-footage

# Use pexels.com API (free)
curl "https://api.pexels.com/videos/search?query=coding&per_page=10" \
  -H "Authorization: YOUR_PEXELS_API_KEY"
```

### Problem: Video metadata not uploading
**Check:** JSON files exist
```bash
ls /tmp/faceless_videos/metadata_*.json
```

**Fix:** Ensure script generates metadata:
```python
# In faceless_video_engine.py
metadata = {
    "title": f"{topic} - Quick Tutorial",
    "description": script,
    "tags": ["tutorial", niche, "ai-generated"]
}
json.dump(metadata, open(f"{output_dir}/metadata_{timestamp}.json", "w"))
```

## Gumroad/Sales Issues

### Problem: No sales after launch
**Diagnostic Checklist:**
- [ ] Product actually published (not draft)?
- [ ] Price set correctly ($49, not $0)?
- [ ] Payment methods enabled?
- [ ] Download link working?
- [ ] Shared on social media?

**Action Plan:**
1. Test purchase yourself (refund after)
2. Post to 5+ communities
3. Add preview screenshots
4. Lower price temporarily ($19 launch sale)

### Problem: High bounce rate on product page
**Optimize:**
```markdown
# Gumroad Product Page Checklist
✓ Clear headline (what problem it solves)
✓ 3-5 bullet points (key features)
✓ Screenshots or demo video
✓ Social proof (testimonials if available)
✓ Clear CTA button
✓ FAQ section
```

### Problem: Payment processing errors
**Check Gumroad dashboard:**
- Stripe connected?
- Bank account verified?
- Tax settings configured?

## OBS/Recording Issues

### Problem: obs_controller.py can't connect
**Solution:**
```bash
# 1. Check OBS is running
ps aux | grep obs

# 2. Check WebSocket enabled
# OBS → Tools → WebSocket Server Settings
# Port: 4455 (default)

# 3. Test connection
python3 -c "from obswebsocket import obsws; ws = obsws('localhost', 4455, ''); ws.connect(); print('Connected'); ws.disconnect()"
```

### Problem: 8K Theater scenes not found
**Solution:**
```bash
# Create symlink
cd ~/.roxy/workshops/monetization/automation/obs
ln -sf ~/mindsong-mirror/figma-8k-theater-rebuild ./theater-scenes

# Verify
ls -la theater-scenes
```

### Problem: NDI cameras not detected
**Check:**
```bash
# 1. NDI library installed?
ls /usr/lib | grep ndi

# 2. Network discovery enabled?
# Router must allow multicast

# 3. Cameras on same subnet?
ip addr show

# 4. Test with NDI Studio Monitor
~/Applications/NDI\ Studio\ Monitor
```

## n8n Automation Issues

### Problem: Workflow won't activate
**Common Causes:**
1. Missing credentials
2. Invalid cron expression
3. API rate limits

**Debug:**
```bash
# Check n8n logs
docker logs n8n | tail -50

# Test workflow manually
# n8n UI → Workflow → Execute Workflow button
```

### Problem: YouTube upload fails
**Check:**
- OAuth token expired? (Re-authorize)
- Video file too large? (Max 256GB)
- Copyright claim? (Use original content)

**Fix:**
```bash
# Refresh OAuth in n8n
# Credentials → YouTube → Re-authorize
```

### Problem: Gumroad webhook not triggering
**Verify:**
```bash
# 1. Webhook URL correct in Gumroad settings?
# Format: https://your-n8n.com/webhook/gumroad-sales

# 2. Test with curl
curl -X POST https://your-n8n.com/webhook/gumroad-sales \
  -H "Content-Type: application/json" \
  -d '{"product_name":"Test","price":"49"}'

# 3. Check n8n execution log
# Should show test execution
```

## Grant Application Issues

### Problem: Application rejected
**Common Reasons:**
1. Budget too high
2. Project scope too broad
3. No clear timeline
4. Missing supporting docs

**Improve Next Time:**
- Narrow scope to specific deliverable
- Add visual mockups/demos
- Include testimonials
- Show traction (users, revenue)

### Problem: No response after 30 days
**Action:**
```bash
# Send polite follow-up
# Use template:
cat grants/follow-up-template.md

# Track in spreadsheet
echo "$(date),Grant Name,Follow-up Sent" >> grants/applications-tracker.csv
```

## Analytics Issues

### Problem: Revenue tracker totals incorrect
**Check CSV format:**
```bash
# Should be: date,source,amount,product
head analytics/revenue-tracker.csv

# Fix formatting
awk -F, 'NF==4 {print}' analytics/revenue-tracker.csv > fixed.csv
mv fixed.csv analytics/revenue-tracker.csv
```

### Problem: Reports not generating
**Debug:**
```bash
# Check script exists
ls -la analytics/generate-weekly-report.sh

# Make executable
chmod +x analytics/generate-weekly-report.sh

# Run manually
./analytics/generate-weekly-report.sh
```

## RAG/Search Issues

### Problem: Roxy can't find workshop documents
**Solution:**
```bash
# Rebuild RAG index
cd ~/.roxy/workshops/monetization
python3 ~/roxy/rebuild_rag_index.py --path ./brain

# Verify index created
ls brain/index.json brain/embeddings.db
```

### Problem: Search returns no results
**Check:**
- Are tags in brain/index.json?
- Is RAG model loaded? (nomic-embed-text)
- Are documents actually in brain/ folders?

**Fix:**
```bash
# Re-index with verbose output
python3 ~/roxy/rebuild_rag_index.py --path ./brain --verbose
```

## General Debugging

### Check All Dependencies
```bash
# Python packages
pip list | grep -E "(ffmpeg|gtts|elevenlabs|requests)"

# System packages
dpkg -l | grep -E "(ffmpeg|espeak)"

# OBS
which obs

# n8n
docker ps | grep n8n
```

### Enable Debug Logging
```bash
# In any Python script, add:
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message here")

# In bash scripts, add:
set -x  # Enable trace mode
```

### Check Disk Space
```bash
df -h
# If /tmp full, clean up old videos:
find /tmp/faceless_videos -mtime +7 -delete
```

### Check Network
```bash
# Test internet
ping -c 3 google.com

# Test APIs
curl https://api.gumroad.com/v2/products
curl https://www.googleapis.com/youtube/v3/channels
```

## Getting Help

### Workshop-Specific Issues
1. Check [00_INDEX.md](../00_INDEX.md)
2. Check [RUNBOOK.md](RUNBOOK.md)
3. Search brain/ documents

### Roxy Infrastructure Issues
1. Check `~/.roxy/README.md`
2. Check `~/.roxy/TROUBLESHOOTING.md`
3. Check logs: `~/.roxy/logs/`

### MindSong Issues
1. Check `~/mindsong-mirror/README.md`
2. Check docs: `~/mindsong-mirror/docs/`

### External Help
- Reddit: r/SideProject, r/EntrepreneurRideAlong
- Discord: IndieHackers, MakerMob
- Twitter: #buildinpublic community

---

**When In Doubt:** Check logs, enable debug mode, isolate the problem step-by-step.
