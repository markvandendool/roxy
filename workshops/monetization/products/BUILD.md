# Product Build Documentation

## Quick Build

```bash
cd ~/.roxy/workshops/monetization/products
./package_products.sh
```

Output: `~/mindsong-products/` with two ZIP files ready for sale.

## Products Overview

### 1. Roxy AI Infrastructure ($49)
**What:** Complete boilerplate for AI agent infrastructure
**Includes:**
- Expert router system (Phi-2.7b)
- Redis vector cache
- PostgreSQL memory with pgvector
- FastAPI server skeleton
- Docker Compose setup

### 2. OBS Automation Toolkit ($29)
**What:** Python library for OBS automation
**Includes:**
- WebSocket client wrapper
- Scene/source control
- Recording automation
- NDI camera integration
- Example workflows

## Build Process

### Step 1: Pre-Build Checklist
```bash
# Verify source files exist
ls ~/.roxy/infrastructure.py
ls ~/.roxy/cache_redis.py
ls ~/.roxy/memory_postgres.py
ls ~/.roxy/expert_router.py
ls ~/.roxy/obs_controller.py

# All should exist ✓
```

### Step 2: Run Packaging Script
```bash
cd products
./package_products.sh
```

**What Happens:**
1. Creates temp directory
2. Copies source files
3. Sanitizes secrets (removes API keys, passwords)
4. Generates README.md for each product
5. Adds example code
6. Creates Dockerfile
7. ZIPs everything
8. Moves to `~/mindsong-products/`

### Step 3: Quality Check
```bash
cd ~/mindsong-products

# Extract and inspect
unzip -l roxy-ai-infrastructure-v1.zip
unzip -l obs-automation-toolkit-v1.zip

# Check for secrets (should find none)
unzip -q roxy-ai-infrastructure-v1.zip
grep -r "sk-" roxy-ai-infrastructure/ && echo "⚠️ API key found!" || echo "✓ Clean"
grep -r "password.*=" roxy-ai-infrastructure/ && echo "⚠️ Password found!" || echo "✓ Clean"

# Test Docker build
cd roxy-ai-infrastructure
docker build -t roxy-test .
docker run --rm roxy-test python infrastructure.py --help
```

### Step 4: Create Product Listing

#### Gumroad
1. Go to: https://gumroad.com/products/new
2. Upload ZIP file
3. Fill in details:

**Title:** Roxy AI Infrastructure Boilerplate
**Price:** $49
**Description:**
```
Production-ready AI agent infrastructure with:

✓ Expert router (Phi-2.7b model selection)
✓ Redis vector cache (sub-ms retrieval)
✓ PostgreSQL long-term memory
✓ FastAPI server skeleton
✓ Docker Compose setup

Perfect for building AI assistants, chatbots, or autonomous agents.

Includes:
- Complete source code
- Docker setup
- Example workflows
- Documentation

No recurring costs. One-time purchase.
```

**Tags:** ai, python, infrastructure, agent, chatbot

4. Add screenshots:
   - Terminal showing agent running
   - Architecture diagram
   - Code snippet

5. Publish

#### LemonSqueezy (Alternative)
1. Go to: https://lemonsqueezy.com/products/new
2. Same process as Gumroad
3. Pros: Better EU VAT handling, lower fees

## Product Variants

### Premium Version ($99)
**Additional Features:**
- Include MindSong integration
- Add 8K Theater scenes
- Include n8n workflows
- Add video tutorials

**Build:**
```bash
# Create premium package
cd products
./package_products_premium.sh

# Includes:
# - Everything in basic version
# - content/engines/
# - automation/n8n/
# - automation/obs/scenes/
# - 5 video tutorials
```

### Enterprise Version ($499)
**Additional Features:**
- Full MindSong codebase (858K LOC)
- Private Discord access
- 1-hour consultation call
- Custom setup assistance

**Build:**
```bash
# Clone entire MindSong repo
cd ~/mindsong-products
git clone ~/mindsong-mirror mindsong-enterprise
cd mindsong-enterprise

# Sanitize
find . -name "*.env*" -delete
find . -name ".git" -exec rm -rf {} +

# Package
tar -czf ../mindsong-enterprise-v1.tar.gz .
```

## Marketing Assets

### Screenshots to Include
1. **Terminal Demo:**
   ```bash
   cd ~/.roxy
   python infrastructure.py
   # Screenshot of agent responding
   ```

2. **Architecture Diagram:**
   - Draw in Excalidraw
   - Show: User → FastAPI → Expert Router → Models → Cache/Memory

3. **Code Sample:**
   ```python
   from infrastructure import RoxyAgent
   
   agent = RoxyAgent()
   response = agent.query("Explain quantum computing")
   print(response)
   ```

### Demo Video (2 minutes)
**Script:**
```
0:00 - "Here's Roxy AI Infrastructure"
0:10 - Show file structure
0:20 - Start Docker Compose
0:30 - Make API call
0:45 - Show response
1:00 - Explain expert routing
1:30 - Show cache performance
1:45 - CTA: "Link in description"
```

**Record:**
```bash
# Use OBS
cd ~/automation/obs
python ~/.roxy/obs_controller.py set_scene "Screen Recording"
python ~/.roxy/obs_controller.py start_recording
# Record demo
python ~/.roxy/obs_controller.py stop_recording
```

## Pricing Strategy

### Initial Launch
- **Week 1-2:** $49 (early bird)
- **Week 3-4:** $69 (regular price)
- **Month 2+:** $79 (standard)

### Bundles
- **Basic:** $49 (Roxy Infrastructure only)
- **Pro:** $79 (Roxy + OBS Toolkit)
- **Ultimate:** $149 (Roxy + OBS + n8n Workflows + Videos)

### Lifetime Deal
- **One-time:** $299 (All products + future updates)

## Distribution Channels

### Primary
- Gumroad (easiest, 10% fee)
- LemonSqueezy (lower fees, better EU)

### Secondary
- GitHub Releases (open-source version, freemium model)
- Product Hunt (launch day traffic)

### Affiliate
- Share product with tech influencers
- Offer 30% commission
- Track with Gumroad affiliate system

## Updates & Versioning

### Version Format
`v1.2.3`
- Major: Breaking changes
- Minor: New features
- Patch: Bug fixes

### Update Schedule
- **Patch:** Weekly (bug fixes)
- **Minor:** Monthly (new features)
- **Major:** Quarterly (breaking changes)

### Notify Customers
```bash
# Use n8n workflow
# Trigger: New version tagged
# Action: Email all customers
# Template: automation/n8n/customer-update-email.json
```

## Legal

### License
Use MIT License for code products:
```
MIT License

Copyright (c) 2026 MindSong

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

### Terms of Service
Include `TERMS.md` in each package:
- No refunds (digital product)
- Use at your own risk
- No warranty
- Cannot resell as-is

## Support

### FAQ Document
Include `FAQ.md`:
- How to install?
- Requirements?
- How to get updates?
- Refund policy?
- Support contact?

### Support Email
- Setup: support@mindsong.ai (or use Gumroad email)
- Response time: 24-48 hours
- Track in: `analytics/support-tickets.csv`

## Metrics to Track

```bash
# In analytics/product-metrics.csv
date,product,sales,revenue,refunds,support_tickets

# Weekly review
cat analytics/product-metrics.csv | tail -7
```

---

**Next:** After building products, read [ops/RUNBOOK.md](../ops/RUNBOOK.md) for operational procedures.
