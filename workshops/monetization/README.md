# Monetization Workshop - Quick Start

**Location:** `~/.roxy/workshops/monetization/`  
**Purpose:** Generate revenue using existing MindSong/Roxy infrastructure  
**Target:** $500-$2,000 in 30 days

## ⚡ 2-Hour Revenue Sprint

### Step 1: Package Product (30 min)
```bash
cd ~/.roxy/workshops/monetization/products
./package_products.sh
```

Creates: `~/mindsong-products/roxy-ai-infrastructure-v1.zip`

### Step 2: Create Gumroad Account (15 min)
1. Visit: https://gumroad.com/start
2. Upload ZIP file
3. Price: $49
4. Title: "Roxy AI Infrastructure Boilerplate"

### Step 3: Share Product (45 min)
Post to:
- Reddit r/Python
- Twitter/X with #buildinpublic
- Hacker News "Show HN"

### Step 4: Generate Content (30 min)
```bash
cd content/engines
python3 faceless_video_engine.py
```

Upload to YouTube/TikTok.

## 📂 Structure

```
00_INDEX.md                    ← Master index (start here)
README.md                      ← This file
brain/                         ← Documentation
  ├── strategies/              ← Revenue strategies
  ├── playbooks/               ← Execution guides
  └── market-research/         ← Market data
products/                      ← Sellable code packages
content/                       ← Video generation
  ├── vertical/                ← TikTok/Shorts (9:16)
  ├── horizontal/              ← YouTube (16:9)
  └── engines/                 ← Python generators
automation/                    ← Workflows
  ├── n8n/                     ← Automation workflows
  ├── obs/                     ← Recording automation
  └── cron/                    ← Scheduled tasks
grants/                        ← Funding applications
analytics/                     ← Revenue tracking
ops/                           ← Runbooks
```

## 🔗 Integration

### Uses Existing Roxy Infrastructure
- `~/.roxy/obs_controller.py` - OBS automation
- `~/.roxy/mcp/mcp_n8n.py` - n8n integration
- `~/.roxy/mcp/mcp_obs.py` - OBS control

### Uses Existing MindSong Assets
- `~/mindsong-mirror/figma-8k-theater-rebuild/` - Production scenes
- `~/mindsong-mirror/automation/obs/` - OBS layouts
- `~/mindsong-mirror/src/pages/MarketingDashboard.tsx` - Metrics UI

## 📖 Read First

1. [00_INDEX.md](00_INDEX.md) - Master overview
2. [brain/playbooks/00_executive-summary.md](brain/playbooks/00_executive-summary.md) - Complete guide
3. [brain/playbooks/01_revenue-playbook.md](brain/playbooks/01_revenue-playbook.md) - Detailed strategies

## 🎯 Revenue Tracks

| Track | Time | Revenue (Month 1) | File |
|-------|------|-------------------|------|
| Digital Products | 4 hrs | $300-$800 | `products/BUILD.md` |
| Faceless Videos | 3 hrs/day | $0-$300 | `content/PIPELINE.md` |
| Freelance | 5 hrs/week | $500-$1,500 | `brain/strategies/` |
| Grants | 8 hrs | $1k-$25k | `grants/00_INDEX.md` |

## 🆘 Help

- **Runbook:** [ops/RUNBOOK.md](ops/RUNBOOK.md)
- **Troubleshooting:** [ops/TROUBLESHOOTING.md](ops/TROUBLESHOOTING.md)
- **Questions:** Check 00_INDEX.md first

## ✅ Status

- [x] Workshop structure created
- [x] Files migrated
- [x] Documentation indexed
- [ ] RAG index built
- [ ] First product shipped
- [ ] First revenue generated

---

**Next:** Read [00_INDEX.md](00_INDEX.md) for full overview.
