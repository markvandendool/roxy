# Monetization Workshop - Operational Runbook

## Daily Operations

### Morning Routine (15 min)
```bash
cd ~/.roxy/workshops/monetization

# 1. Check overnight sales
cat analytics/revenue-tracker.csv | tail -5

# 2. Review video performance
# Check YouTube/TikTok analytics

# 3. Generate today's content
cd content/engines
python3 faceless_video_engine.py --niche=coding

# 4. Schedule upload
# Upload to queue or use n8n automation
```

### Evening Routine (10 min)
```bash
# 1. Log today's revenue
echo "$(date),source,amount,product" >> analytics/revenue-tracker.csv

# 2. Review metrics
cat analytics/revenue-tracker.csv | awk -F, '{sum+=$3} END {print "Total: $"sum}'

# 3. Plan tomorrow
# Update campaigns/ if needed
```

## Weekly Operations

### Monday: Plan Week
```bash
# 1. Review last week's results
cd analytics/reports
./generate-weekly-report.sh

# 2. Set this week's goals
# Update campaigns/week-X/goals.md

# 3. Schedule content
# Batch generate 21 videos (3/day)
cd ../../content/engines
for i in {1..21}; do
  python3 faceless_video_engine.py
  sleep 5
done
```

### Friday: Review & Optimize
```bash
# 1. Analyze best performers
# Check which products/videos performed best

# 2. Double down on winners
# Adjust content strategy

# 3. Archive week's work
tar -czf analytics/archives/week-$(date +%W)-2026.tar.gz \
  analytics/reports/week-*
```

## Product Operations

### Package New Product
```bash
cd products
./package_products.sh

# Upload to:
# - Gumroad: https://gumroad.com/products
# - LemonSqueezy: https://lemonsqueezy.com
# - GitHub Releases (for open-source versions)
```

### Update Existing Product
```bash
# 1. Update source code
cd ~/mindsong-products/[product-name]

# 2. Increment version
# Update version in README.md

# 3. Re-package
cd ~/.roxy/workshops/monetization/products
./package_products.sh

# 4. Email customers (if major update)
# Use automation/n8n/customer-update-email.json
```

## Content Operations

### Generate Video Batch
```bash
cd content/engines

# Generate 10 coding videos
for i in {1..10}; do
  python3 faceless_video_engine.py --niche=coding
done

# Generate 5 AI videos
for i in {1..5}; do
  python3 faceless_video_engine.py --niche=ai
done

# Generate 5 music theory videos
for i in {1..5}; do
  python3 faceless_video_engine.py --niche=music_theory
done

# Videos saved to /tmp/faceless_videos/
```

### Upload to Platforms
```bash
# Manual upload (until automation ready)
# 1. Open YouTube Studio
# 2. Upload from /tmp/faceless_videos/
# 3. Use metadata from metadata_*.json files

# Automated (using n8n)
# Trigger: automation/n8n/daily-video-generation.json
```

### Use 8K Theater for High-Quality Content
```bash
# 1. Link to theater scenes
cd automation/obs/scenes
ln -sf ~/mindsong-mirror/figma-8k-theater-rebuild ./theater

# 2. Start OBS with scene
python3 ~/.roxy/obs_controller.py set_scene "Coding Tutorial"

# 3. Start recording
python3 ~/.roxy/obs_controller.py start_recording

# 4. Stop after session
python3 ~/.roxy/obs_controller.py stop_recording
```

## Grant Operations

### Submit Grant Application
```bash
cd grants/[grant-name]

# 1. Fill out application template
# Edit application.md

# 2. Prepare supporting docs
# - Demo video (if required)
# - Budget spreadsheet
# - Letters of support

# 3. Submit via platform
# Follow grant/[name]/INSTRUCTIONS.md

# 4. Track submission
echo "$(date),Grant Name,Status,Amount" >> ../applications-tracker.csv
```

### Follow Up on Grants
```bash
# Weekly check on pending grants
cat grants/applications-tracker.csv | grep "Pending"

# Send follow-up if > 30 days
# Use template in grants/follow-up-template.md
```

## Automation Operations

### Deploy n8n Workflow
```bash
# 1. Test workflow locally
# Import automation/n8n/[workflow].json into n8n

# 2. Configure credentials
# Add API keys in n8n UI

# 3. Activate workflow
# Set schedule/trigger

# 4. Monitor execution
# Check n8n logs
```

### Schedule Cron Jobs
```bash
# Edit crontab
crontab -e

# Add daily video generation (6 AM, 2 PM, 8 PM)
0 6,14,20 * * * cd ~/.roxy/workshops/monetization/content/engines && python3 faceless_video_engine.py

# Add weekly report (Monday 9 AM)
0 9 * * 1 cd ~/.roxy/workshops/monetization/analytics && ./generate-weekly-report.sh
```

## Analytics Operations

### Track Revenue
```bash
cd analytics

# Add sale
echo "$(date '+%Y-%m-%d'),Gumroad,49,Roxy Infrastructure" >> revenue-tracker.csv

# View total
awk -F, '{sum+=$3} END {print "Total Revenue: $"sum}' revenue-tracker.csv

# View by source
awk -F, '{sources[$2]+=$3} END {for (s in sources) print s": $"sources[s]}' revenue-tracker.csv
```

### Generate Reports
```bash
cd analytics

# Weekly report
./generate-weekly-report.sh > reports/week-$(date +%W)-2026.md

# Monthly report
./generate-monthly-report.sh > reports/month-$(date +%m)-2026.md
```

## Maintenance Operations

### Backup Workshop
```bash
# Full backup
tar -czf ~/backups/monetization-workshop-$(date +%Y%m%d).tar.gz \
  ~/.roxy/workshops/monetization

# Incremental backup (analytics only)
tar -czf ~/backups/monetization-analytics-$(date +%Y%m%d).tar.gz \
  ~/.roxy/workshops/monetization/analytics
```

### Update Documentation
```bash
# After making changes
cd ~/.roxy/workshops/monetization

# Rebuild RAG index
python3 ~/roxy/rebuild_rag_index.py --path ./brain

# Commit to git
git add -A
git commit -m "Update monetization docs"
git push
```

### Clean Up
```bash
# Remove old videos
find /tmp/faceless_videos -name "*.mp4" -mtime +7 -delete

# Archive old reports
cd analytics/reports
tar -czf archives/$(date +%Y-%m).tar.gz *.md
rm -f week-*.md
```

## Emergency Procedures

### Revenue Stopped
1. Check Gumroad dashboard for issues
2. Verify payment processing
3. Check if product links are working
4. Review analytics for traffic drop

### Automation Failed
1. Check n8n logs: `docker logs n8n`
2. Verify API credentials
3. Test workflow manually
4. Check rate limits

### Content Not Generating
1. Check ffmpeg installation: `ffmpeg -version`
2. Verify TTS engine: `espeak --version`
3. Check disk space: `df -h /tmp`
4. Review Python errors in logs

---

**Remember:** Log everything in `analytics/`, review weekly, optimize based on data.
