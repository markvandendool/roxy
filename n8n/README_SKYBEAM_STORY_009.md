# SKYBEAM STORY-009: n8n Research Workflow Runbook

**Story ID:** SKYBEAM-STORY-009
**Created:** 2026-01-11
**Author:** Claude Opus 4.5 (Master Chief)

---

## Overview

This workflow orchestrates the SKYBEAM Research Pipeline through n8n:

1. **Trend Detector** (STORY-006) - Fetches RSS feeds and scores trends
2. **Deep Research Agent** (STORY-007) - Generates research briefs
3. **Competitor Analyzer** (STORY-008) - Analyzes competitor coverage
4. **Bundle Writer** (STORY-009) - Combines outputs and publishes to NATS

---

## Files

| File | Purpose |
|------|---------|
| `workflows/SKYBEAM_STORY_009_RESEARCH_PIPELINE.json` | n8n workflow export |
| `~/.roxy/services/research/bundle_writer.py` | Bundle writer script |
| `~/.roxy/services/research/selftest_bundle_nats.py` | NATS integration selftest |

---

## Prerequisites

1. **n8n instance** running and accessible
2. **NATS server** running at `localhost:4222`
3. **Python venv** at `~/.roxy/venv` with dependencies installed
4. **Systemd timers** (optional, for standalone operation)

---

## How to Import Workflow

### Option A: n8n UI Import

1. Open n8n web interface (typically `http://localhost:5678`)
2. Click **Workflows** → **Import from File**
3. Select: `~/.roxy/n8n/workflows/SKYBEAM_STORY_009_RESEARCH_PIPELINE.json`
4. Click **Import**
5. Workflow appears as "SKYBEAM Research Pipeline (STORY-009)"

### Option B: n8n CLI Import

```bash
# If using n8n CLI
n8n import:workflow --input=/home/mark/.roxy/n8n/workflows/SKYBEAM_STORY_009_RESEARCH_PIPELINE.json
```

---

## Required Environment Variables

The scripts use these defaults (no additional config needed):

| Variable | Default | Purpose |
|----------|---------|---------|
| `NATS_URL` | `nats://localhost:4222` | NATS server URL |

---

## How to Run Once

### Option A: Manual n8n Execution

1. Open workflow in n8n
2. Click **Execute Workflow** button
3. Watch execution progress through nodes

### Option B: Command Line (No n8n)

```bash
# Run all four scripts in sequence
~/.roxy/venv/bin/python ~/.roxy/services/research/trend_detector.py && \
~/.roxy/venv/bin/python ~/.roxy/services/research/deep_research_agent.py && \
~/.roxy/venv/bin/python ~/.roxy/services/research/competitor_analyzer.py && \
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py
```

### Option C: Via Systemd (Recommended for Production)

```bash
# Timers already enabled; force immediate run:
systemctl --user start roxy-trend-detector.service
systemctl --user start roxy-deep-research.service
systemctl --user start roxy-competitor-analyzer.service
# Then run bundle writer manually:
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py
```

---

## Output Locations

| Output | Path |
|--------|------|
| Trends | `~/.roxy/content-pipeline/trends/trends_latest.json` |
| Research | `~/.roxy/content-pipeline/research/research_latest.json` |
| Competitors | `~/.roxy/content-pipeline/competitors/competitors_latest.json` |
| **Bundle** | `~/.roxy/content-pipeline/bundles/research_bundle_latest.json` |

---

## NATS Topics

| Topic | Publisher |
|-------|-----------|
| `ghost.content.trends` | trend_detector.py |
| `ghost.content.research` | deep_research_agent.py |
| `ghost.content.competitors` | competitor_analyzer.py |
| `ghost.content.bundle` | bundle_writer.py |

---

## Proof Commands

### Verify Bundle Output

```bash
cat ~/.roxy/content-pipeline/bundles/research_bundle_latest.json | jq '.status, .summary'
```

### Run NATS Selftest

```bash
~/.roxy/venv/bin/python ~/.roxy/services/research/selftest_bundle_nats.py
# Expected: EXIT CODE: 0
```

### Verify Workflow JSON

```bash
cat ~/.roxy/n8n/workflows/SKYBEAM_STORY_009_RESEARCH_PIPELINE.json | jq '.name, .meta'
```

### Test Degraded Mode

```bash
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py --test-degraded
# Expected: status: degraded, all counts: 0
```

---

## Troubleshooting

### Problem: n8n can't find Python

**Cause:** n8n doesn't inherit user PATH

**Fix:** Use absolute paths in workflow (already configured):
```
/home/mark/.roxy/venv/bin/python /home/mark/.roxy/services/research/...
```

### Problem: NATS connection refused

**Cause:** NATS server not running

**Fix:**
```bash
systemctl status nats
# or
docker ps | grep nats
```

### Problem: Missing input files

**Cause:** Upstream scripts haven't run

**Fix:** Run the full pipeline from trend_detector first:
```bash
~/.roxy/venv/bin/python ~/.roxy/services/research/trend_detector.py
~/.roxy/venv/bin/python ~/.roxy/services/research/deep_research_agent.py
~/.roxy/venv/bin/python ~/.roxy/services/research/competitor_analyzer.py
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py
```

---

## Relationship to Systemd Timers

This n8n workflow is an **optional orchestration mirror** of what systemd already provides:

| Timer | Schedule | Equivalent n8n Node |
|-------|----------|---------------------|
| `roxy-trend-detector.timer` | Hourly :00 | Run Trend Detector |
| `roxy-deep-research.timer` | Hourly :05 | Run Deep Research |
| `roxy-competitor-analyzer.timer` | Hourly :10 | Run Competitor Analyzer |
| (manual) | After all above | Write Research Bundle |

**Use cases for n8n:**
- Visual execution monitoring
- Integration with external webhooks
- Complex conditional logic
- Notification on failure

**Use cases for systemd:**
- Minimal resource overhead
- No external dependencies
- Automatic startup on boot
- Native journald logging

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-11 | Initial release (STORY-009) |
