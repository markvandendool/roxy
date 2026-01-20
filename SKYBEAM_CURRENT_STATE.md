---
ai-doc-type: runbook
ai-priority: critical
ai-status: canonical
ai-last-updated: 2026-01-20
ai-owners: [SKYBEAM]
ai-depends-on: [~/.roxy/PROJECT_SKYBEAM.md]
---

# SKYBEAM CURRENT STATE — Canonical Truth Document

**Last Updated:** 2026-01-20
**Updated By:** Claude Opus 4.5 (Master Chief)
**Authority:** This document is the SINGLE SOURCE OF TRUTH for SKYBEAM pipeline state.

---

## EXECUTIVE STATUS

| Metric | Value |
|--------|-------|
| **Overall Progress** | Phase 1-5 COMPLETE |
| **Stories Completed** | 20 / 26 |
| **Story Points Completed** | 240 / 311 (77.2%) |
| **Daemons Running** | 2 (content-handler, skybeam-worker) |
| **Timers Enabled** | 15 (P2: 4, P3: 3, P4: 4, P5: 4) |
| **Master Output** | master_latest.mp4 (1080x1920, 10s, 205KB) |

---

## PHASE STATUS

| Phase | Name | Stories | Points | Status |
|-------|------|---------|--------|--------|
| **1** | Core Pipeline Infrastructure | 5 | 42 | **CERTIFIED** |
| **2** | Research & Intelligence Layer | 4/4 | 55/55 | **COMPLETE** |
| **3** | Scripting Engine | 3/3 | 47/47 | **COMPLETE** |
| **4** | Asset Generation | 4/4 | 52/52 | **COMPLETE** |
| **5** | Production Pipeline | 4/4 | 44/44 | **COMPLETE** |
| 6 | Publishing & Monitoring | 6 | 58 | Pending |

---

## CERTIFIED ARTIFACTS (Phase 1 + P0)

### Services

| Service | Port | Systemd Unit | Status |
|---------|------|--------------|--------|
| Content Request Handler | 8780 | `roxy-content-handler.service` | Running |
| SKYBEAM Worker (P0) | - | `roxy-skybeam-worker.service` | Running |
| Trend Detector (STORY-006) | - | `roxy-trend-detector.timer` | Hourly |
| Deep Research (STORY-007) | - | `roxy-deep-research.timer` | Hourly (+5m offset) |
| Competitor Analyzer (STORY-008) | - | `roxy-competitor-analyzer.timer` | Hourly (+10m offset) |

### Files

```
~/.roxy/services/
├── content_request_handler.py    # STORY-001: FastAPI webhook
├── skybeam_worker.py             # P0: NATS subscriber
├── skybeam_p0_renderer.py        # P0: Cards + TTS → master.mp4
├── ghost_publisher.py            # STORY-005: ghost.content.* topics
└── obs_client.py                 # STORY-004: OBS WebSocket

~/.config/systemd/user/
├── roxy-content-handler.service  # STORY-001
├── roxy-skybeam-worker.service   # P0
├── roxy-trend-detector.service   # STORY-006
├── roxy-trend-detector.timer     # STORY-006 (hourly)
├── roxy-deep-research.service    # STORY-007
├── roxy-deep-research.timer      # STORY-007 (hourly +5m)
├── roxy-competitor-analyzer.service   # STORY-008
├── roxy-competitor-analyzer.timer     # STORY-008 (hourly +10m)
├── roxy-bundle-writer.service         # STORY-009
├── roxy-bundle-writer.timer           # STORY-009 (hourly +12m)
├── roxy-template-library.service      # STORY-011
├── roxy-template-library.timer        # STORY-011 (hourly +14m)
├── roxy-script-generator.service      # STORY-010
├── roxy-script-generator.timer        # STORY-010 (hourly +16m)
├── roxy-script-reviewer.service       # STORY-012
├── roxy-script-reviewer.timer         # STORY-012 (hourly +18m)
├── roxy-asset-briefs.service          # STORY-013
├── roxy-asset-briefs.timer            # STORY-013 (hourly +20m)
├── roxy-prompt-packs.service          # STORY-014
├── roxy-prompt-packs.timer            # STORY-014 (hourly +22m)
├── roxy-storyboards.service           # STORY-015
├── roxy-storyboards.timer             # STORY-015 (hourly +24m)
├── roxy-asset-qa.service              # STORY-016
└── roxy-asset-qa.timer                # STORY-016 (hourly +26m)

~/.roxy/content-pipeline/
├── manifest_schema.json          # STORY-003: Job manifest schema
├── pipeline.sh                   # STORY-003: v2.0.0 with manifest
└── jobs/                         # Job output directories
    └── JOB_20260110_233218_f9d9c3f9/
        ├── manifest.json         # status: completed
        └── outputs/
            └── master.mp4        # 178KB, 36s, 1920x1080, H.264

~/.roxy/ops/iphone_shortcuts/
└── video_request.yaml            # STORY-002: iPhone Shortcuts doc
```

### NATS Topics (STORY-005)

| Topic | Purpose |
|-------|---------|
| `ghost.content.request` | New content request |
| `ghost.content.research` | Research stage |
| `ghost.content.script` | Script stage |
| `ghost.content.assets` | Assets stage |
| `ghost.content.production` | Production stage |
| `ghost.content.publish` | Publishing stage |
| `ghost.content.status` | Full status snapshot |
| `ghost.content.trends` | Trend detector snapshots (STORY-006) |
| `ghost.content.research` | Research briefs (STORY-007) |
| `ghost.content.competitors` | Competitor analyses (STORY-008) |
| `ghost.content.bundle` | Research bundle (STORY-009) |
| `ghost.script.templates` | Template library (STORY-011) |
| `ghost.script.generated` | Generated scripts (STORY-010) |
| `ghost.script.reviewed` | Reviewed scripts (STORY-012) |
| `ghost.asset.briefs` | Asset briefs (STORY-013) |
| `ghost.asset.prompts` | Prompt packs (STORY-014) |
| `ghost.asset.storyboards` | Storyboards (STORY-015) |
| `ghost.asset.qa` | QA reports (STORY-016) |

---

## PHASE 2: RESEARCH & INTELLIGENCE LAYER

### STORY-006: Trend Detector Service — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (status field: healthy/partial/degraded) |
| File output | `~/.roxy/content-pipeline/trends/trends_latest.json` |
| NATS publish | `ghost.content.trends` verified with subscriber |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Proof Commands:**
```bash
# Normal run
~/.roxy/venv/bin/python ~/.roxy/services/research/trend_detector.py

# Degraded mode
~/.roxy/venv/bin/python ~/.roxy/services/research/trend_detector.py --test-degraded
```

**Files:**
```
~/.roxy/services/research/
├── trend_detector.py           # Main service
├── verify_nats_trends.py       # NATS verifier
└── selftest_trends_nats.py     # Deterministic selftest

~/.roxy/content-pipeline/trends/
└── trends_latest.json          # Output snapshot
```

**Systemd Timer:**
```bash
systemctl --user list-timers | grep trend  # Shows hourly schedule
systemctl --user status roxy-trend-detector.timer
```

### STORY-007: Deep Research Agent — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (JSON schema at schemas/research_brief.json) |
| File output | `~/.roxy/content-pipeline/research/research_latest.json` |
| NATS publish | `ghost.content.research` verified with subscriber |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Proof Commands:**
```bash
# Normal run
~/.roxy/venv/bin/python ~/.roxy/services/research/deep_research_agent.py

# Degraded mode
~/.roxy/venv/bin/python ~/.roxy/services/research/deep_research_agent.py --test-degraded
```

**Files:**
```
~/.roxy/services/research/
├── deep_research_agent.py      # Main service
├── verify_nats_research.py     # NATS verifier
├── selftest_research_nats.py   # Deterministic selftest
└── schemas/
    └── research_brief.json     # JSON schema

~/.roxy/content-pipeline/research/
└── research_latest.json        # Output briefs
```

**Systemd Timer:**
```bash
systemctl --user list-timers | grep research  # Shows hourly +5m schedule
systemctl --user status roxy-deep-research.timer
```

### STORY-008: Competitor Analyzer — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (JSON schema at schemas/competitor_analysis.json) |
| File output | `~/.roxy/content-pipeline/competitors/competitors_latest.json` |
| NATS publish | `ghost.content.competitors` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Proof Commands:**
```bash
# Normal run
~/.roxy/venv/bin/python ~/.roxy/services/research/competitor_analyzer.py

# Degraded mode
~/.roxy/venv/bin/python ~/.roxy/services/research/competitor_analyzer.py --test-degraded

# Selftest
~/.roxy/venv/bin/python ~/.roxy/services/research/selftest_competitors_nats.py
```

**Files:**
```
~/.roxy/services/research/
├── competitor_analyzer.py        # Main service
├── competitors_list.json         # 19 competitors to track
├── selftest_competitors_nats.py  # Deterministic selftest
└── schemas/
    └── competitor_analysis.json  # JSON schema

~/.roxy/content-pipeline/competitors/
└── competitors_latest.json       # Output analyses
```

**Systemd Timer:**
```bash
systemctl --user list-timers | grep competitor  # Shows hourly +10m schedule
systemctl --user status roxy-competitor-analyzer.timer
```

### STORY-009: n8n Research Workflow — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Workflow JSON | `~/.roxy/n8n/workflows/SKYBEAM_STORY_009_RESEARCH_PIPELINE.json` |
| bundle_writer output | Schema-valid, status: healthy/partial/degraded |
| File output | `~/.roxy/content-pipeline/bundles/research_bundle_latest.json` |
| NATS publish | `ghost.content.bundle` verified with selftest |
| Runbook | `~/.roxy/n8n/README_SKYBEAM_STORY_009.md` |

**Proof Commands:**
```bash
# Run bundle writer
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py

# Test degraded mode
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py --test-degraded

# Run NATS selftest
~/.roxy/venv/bin/python ~/.roxy/services/research/selftest_bundle_nats.py
```

**Files:**
```
~/.roxy/services/research/
├── bundle_writer.py              # Main bundle combiner
└── selftest_bundle_nats.py       # Deterministic selftest

~/.roxy/n8n/
├── workflows/
│   └── SKYBEAM_STORY_009_RESEARCH_PIPELINE.json  # n8n workflow export
└── README_SKYBEAM_STORY_009.md   # Runbook

~/.roxy/content-pipeline/bundles/
└── research_bundle_latest.json   # Output bundle
```

**Systemd Timer:**
```bash
systemctl --user list-timers | grep bundle  # Shows hourly +12m schedule
systemctl --user status roxy-bundle-writer.timer
```

**Automation Cadence (sealed pipeline):**
```
Phase 2: :00 trends → :05 research → :10 competitors → :12 bundle
Phase 3: :14 templates → :16 scripts → :18 review
Phase 4: :20 briefs → :22 prompts → :24 storyboards → :26 qa
Phase 5: :28 requests → :30 render → :32 master → :34 prod-qa
```

---

## PHASE 3: SCRIPTING ENGINE

### STORY-011: Template Library — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/template_library.json) |
| File output | `~/.roxy/content-pipeline/scripts/templates_latest.json` |
| NATS publish | `ghost.script.templates` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Files:**
```
~/.roxy/services/scripting/
├── template_library.py           # Main service
├── templates/
│   └── templates.json            # 7 template definitions
├── selftest_templates_nats.py    # Deterministic selftest
└── schemas/
    └── template_library.json     # JSON schema
```

### STORY-010: Script Generator — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/script_output.json) |
| File output | `~/.roxy/content-pipeline/scripts/scripts_latest.json` |
| NATS publish | `ghost.script.generated` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Files:**
```
~/.roxy/services/scripting/
├── script_generator.py           # Main service
├── selftest_scripts_nats.py      # Deterministic selftest
└── schemas/
    └── script_output.json        # JSON schema
```

### STORY-012: Script Reviewer — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/script_reviewed.json) |
| File output | `~/.roxy/content-pipeline/scripts/scripts_reviewed.json` |
| NATS publish | `ghost.script.reviewed` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |
| Review metrics | Output includes avg_score + approved_count (see scripts_reviewed.json) |

**Files:**
```
~/.roxy/services/scripting/
├── script_reviewer.py            # Main service
├── selftest_review_nats.py       # Deterministic selftest
└── schemas/
    └── script_reviewed.json      # JSON schema
```

**Proof Commands (Phase 3):**
```bash
# Run full scripting pipeline
~/.roxy/venv/bin/python ~/.roxy/services/scripting/template_library.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/script_generator.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/script_reviewer.py

# Run all selftests
~/.roxy/venv/bin/python ~/.roxy/services/scripting/selftest_templates_nats.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/selftest_scripts_nats.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/selftest_review_nats.py
```

**Systemd Timers:**
```bash
systemctl --user list-timers | grep -E 'roxy-(template|script)'
```

---

## PHASE 4: ASSET GENERATION

### STORY-013: Video Asset Brief Builder — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/asset_briefs.json) |
| File output | `~/.roxy/content-pipeline/assets/briefs/asset_briefs_latest.json` |
| NATS publish | `ghost.asset.briefs` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Files:**
```
~/.roxy/services/assets/
├── asset_brief_builder.py        # Main service
├── selftest_briefs_nats.py       # Deterministic selftest
└── schemas/
    └── asset_briefs.json         # JSON schema

~/.roxy/content-pipeline/assets/briefs/
└── asset_briefs_latest.json      # Output briefs
```

### STORY-014: Prompt Pack Generator — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/prompt_packs.json) |
| File output | `~/.roxy/content-pipeline/assets/prompts/prompt_packs_latest.json` |
| NATS publish | `ghost.asset.prompts` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Files:**
```
~/.roxy/services/assets/
├── prompt_pack_generator.py      # Main service
├── selftest_prompts_nats.py      # Deterministic selftest
└── schemas/
    └── prompt_packs.json         # JSON schema

~/.roxy/content-pipeline/assets/prompts/
└── prompt_packs_latest.json      # Output packs (32 prompts)
```

### STORY-015: Storyboard + Shotlist Generator — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/storyboards.json) |
| File output | `~/.roxy/content-pipeline/assets/storyboards/storyboards_latest.json` |
| NATS publish | `ghost.asset.storyboards` verified with selftest |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Files:**
```
~/.roxy/services/assets/
├── storyboard_generator.py       # Main service
├── selftest_storyboards_nats.py  # Deterministic selftest
└── schemas/
    └── storyboards.json          # JSON schema

~/.roxy/content-pipeline/assets/storyboards/
└── storyboards_latest.json       # Output (32 frames, 32 shots)
```

### STORY-016: Asset QA + Lint Gate — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/asset_qa.json) |
| File output | `~/.roxy/content-pipeline/assets/qa/asset_qa_latest.json` |
| NATS publish | `ghost.asset.qa` verified with selftest |
| Gate checks | 43/43 passed, gate: approved |
| Degraded mode | `--test-degraded` flag, schema-valid empty output |

**Files:**
```
~/.roxy/services/assets/
├── asset_qa_gate.py              # Main service
├── selftest_qa_nats.py           # Deterministic selftest
└── schemas/
    └── asset_qa.json             # JSON schema

~/.roxy/content-pipeline/assets/qa/
└── asset_qa_latest.json          # Output (43 checks passed)
```

**Proof Commands (Phase 4):**
```bash
# Run full asset pipeline
~/.roxy/venv/bin/python ~/.roxy/services/assets/asset_brief_builder.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/prompt_pack_generator.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/storyboard_generator.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/asset_qa_gate.py

# Run all selftests
~/.roxy/venv/bin/python ~/.roxy/services/assets/selftest_briefs_nats.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/selftest_prompts_nats.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/selftest_storyboards_nats.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/selftest_qa_nats.py
```

**Systemd Timers:**
```bash
systemctl --user list-timers | grep -E 'roxy-(asset|prompt|storyboard)'
```

---

## PHASE 4 HEALTH CHECK

Quick command to verify the Asset Generation layer is healthy:

```bash
# Check all four Phase 4 timers are scheduled
systemctl --user list-timers | grep -E 'roxy-(asset|prompt|storyboard)'

# Verify all output files exist with recent timestamps
ls -la ~/.roxy/content-pipeline/assets/{briefs,prompts,storyboards,qa}/*latest.json

# Quick status from QA gate (pipe-safe)
python3 << 'PYEOF'
import json
from pathlib import Path
p = Path.home()/'.roxy/content-pipeline/assets/qa/asset_qa_latest.json'
d = json.loads(p.read_text(encoding='utf-8'))
s = d.get('summary', {})
print(f"QA: {d.get('status')} | Gate: {s.get('gate_result')} | Checks: {s.get('total_passed')}/{s.get('total_checks')} passed")
PYEOF
```

---

## PHASE 5: PRODUCTION PIPELINE

### STORY-017: Render Request Builder — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/render_requests.json) |
| File output | `~/.roxy/content-pipeline/production/requests/render_requests_latest.json` |
| NATS publish | `ghost.prod.render_request` verified with selftest |
| Deterministic selection | Top 1 approved by score DESC, script_id ASC |

### STORY-018: Renderer Runner — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/render_result.json) |
| File output | `~/.roxy/content-pipeline/production/renders/render_result_latest.json` |
| Video output | `~/.roxy/content-pipeline/production/renders/<script_id>/render.mp4` |
| NATS publish | `ghost.prod.render_result` verified with selftest |
| Lock enforcement | flock /tmp/skybeam_prod.lock prevents overlap |
| ffprobe + sha256 | Included in file_proof |

### STORY-019: Master Assembler — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/master.json) |
| File output | `~/.roxy/content-pipeline/production/master/master_latest.json` |
| Video output | `~/.roxy/content-pipeline/production/master/master_latest.mp4` |
| NATS publish | `ghost.prod.master` verified with selftest |
| Vertical format | 1080x1920 (9:16 aspect) |

### STORY-020: Production QA Gate — COMPLETE

**Status:** CERTIFIED (2026-01-11)

| Proof Gate | Evidence |
|------------|----------|
| Schema validation | PASSED (schemas/production_qa.json) |
| File output | `~/.roxy/content-pipeline/production/qa/production_qa_latest.json` |
| NATS publish | `ghost.prod.qa` verified with selftest |
| Gate checks | 7/7 passed (file, size, ffprobe, resolution, duration, audio, sha256) |
| Gate result | approved |

**Files:**
```
~/.roxy/services/production/
├── render_request_builder.py     # STORY-017
├── renderer_runner.py            # STORY-018
├── master_assembler.py           # STORY-019
├── production_qa_gate.py         # STORY-020
├── selftest_render_requests_nats.py
├── selftest_renderer_nats.py
├── selftest_master_nats.py
├── selftest_production_qa_nats.py
└── schemas/
    ├── render_requests.json
    ├── render_result.json
    ├── master.json
    └── production_qa.json

~/.roxy/content-pipeline/production/
├── requests/render_requests_latest.json
├── renders/
│   ├── render_result_latest.json
│   └── <script_id>/render.mp4
├── master/
│   ├── master_latest.mp4    # 1080x1920, 10s, 205KB
│   └── master_latest.json
└── qa/production_qa_latest.json
```

---

## PHASE 5 HEALTH CHECK

Quick command to verify the Production Pipeline layer is healthy:

```bash
# Check all four Phase 5 timers are scheduled
systemctl --user list-timers | grep roxy-prod

# Verify master output exists
ls -la ~/.roxy/content-pipeline/production/master/master_latest.mp4

# Quick status from production QA gate (pipe-safe)
python3 << 'PY'
import json
from pathlib import Path
p = Path.home()/'.roxy/content-pipeline/production/qa/production_qa_latest.json'
d = json.loads(p.read_text(encoding='utf-8'))
print(f"QA: {d.get('status')} | Gate: {d.get('gate_result')} | Checks: {d.get('meta',{}).get('passed')}/{d.get('meta',{}).get('check_count')} passed")
PY
```

---

## VIRAL SEED INJECTION

Manual seed injection for pedagogical content from repo mining.

### Convention

Seeds are stored in `~/.roxy/content-pipeline/seeds/` and injected into `trends_latest.json` with hygiene fields:

```json
{
  "title": "See Your Pitch Accuracy in Real-Time (No More Guessing)",
  "source": "MindSong Pedagogy",
  "origin": "seed",
  "seed_id": "SEED_20260111_VIRAL_001",
  "injected": true,
  "score": 99
}
```

### Seed File

```
~/.roxy/content-pipeline/seeds/viral_short_001.json
```

### Token-Safe Chain Runner

```bash
set -euo pipefail
echo "=== RUNNING FULL PIPELINE CHAIN (TOKEN-SAFE) ==="
~/.roxy/venv/bin/python ~/.roxy/services/research/bundle_writer.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/template_library.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/script_generator.py
~/.roxy/venv/bin/python ~/.roxy/services/scripting/script_reviewer.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/asset_brief_builder.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/prompt_pack_generator.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/storyboard_generator.py
~/.roxy/venv/bin/python ~/.roxy/services/assets/asset_qa_gate.py

echo "=== PROOF: QA SUMMARY ==="
python3 << 'PY'
import json
from pathlib import Path
p = Path.home()/'.roxy/content-pipeline/assets/qa/asset_qa_latest.json'
d = json.loads(p.read_text(encoding='utf-8'))
s = d.get('summary', {})
print(f"QA: {d.get('status')} | Gate: {s.get('gate_result')} | Checks: {s.get('total_passed')}/{s.get('total_checks')} passed")
PY
```

### Proof (2026-01-11)

- Seed: `SEED_20260111_VIRAL_001`
- Title: "See Your Pitch Accuracy in Real-Time (No More Guessing)"
- Source: Mined from `docs/FRETBOARD_UNIVERSAL_MISSION_COMPLETE.md`
- Result: QA healthy, gate approved, 45/45 checks passed

---

## PHASE 3 HEALTH CHECK

Quick command to verify the Scripting Engine layer is healthy:

```bash
# Check all three Phase 3 timers are scheduled
systemctl --user list-timers | grep -E 'roxy-(template|script)'

# Verify all output files exist with recent timestamps
ls -la ~/.roxy/content-pipeline/scripts/*latest.json

# Quick status from review
cat ~/.roxy/content-pipeline/scripts/scripts_reviewed.json | \
  python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('summary',{}); print(f'Review: {d[\"status\"]} | Total: {s.get(\"total_reviewed\")} | Approved: {s.get(\"approved\")} | Avg: {s.get(\"average_score\")}')"
```

---

## PHASE 2 HEALTH CHECK

Quick command to verify the entire Research & Intelligence layer is healthy:

```bash
# Check all three timers are scheduled
systemctl --user list-timers | grep -E 'roxy-(trend|deep|competitor)'

# Verify all output files exist with recent timestamps
ls -la ~/.roxy/content-pipeline/{trends,research,competitors,bundles}/*latest.json

# Quick status from bundle
cat ~/.roxy/content-pipeline/bundles/research_bundle_latest.json | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Bundle: {d[\"status\"]} | Trends: {d[\"summary\"][\"trend_count\"]} | Briefs: {d[\"summary\"][\"brief_count\"]} | Analyses: {d[\"summary\"][\"analysis_count\"]}')"
```

---

## SYSTEM FIXES

### Lock Warning Contamination Fix (2026-01-11)

**Problem:** `/etc/profile.d/mindsong-warning.sh` was printing warnings in non-interactive shells, contaminating script output.

**Solution:** Added interactive shell guards:
```bash
if [[ -n "${PS1:-}" ]] && [[ -t 1 ]]; then
  # Only show warning in interactive terminals
fi
```

**Proof:**
```bash
bash -c 'echo OK'              # Output: OK (exact, no contamination)
bash -c 'python3 -c "print(123)"'  # Output: 123 (exact)
```

**Rollback:** Forensic copy at `~/.roxy/forensics/LOCK_WARNING_FIX_20260111/`

---

## CERTIFICATION EVIDENCE

### P0 End-to-End Proof

```
Job ID:     JOB_20260110_233218_f9d9c3f9
Input:      POST /api/content/request with topic="SKYBEAM P0 master.mp4 proof"
Output:     ~/.roxy/content-pipeline/jobs/JOB_20260110_233218_f9d9c3f9/outputs/master.mp4

ffprobe verification:
- Codec: H.264 High Profile
- Resolution: 1920x1080
- Frame Rate: 30 fps
- Duration: 36.000000 seconds
- File Size: 178,519 bytes

Manifest verification:
- status: completed
- stages.production.status: completed
- stages.production.master_mp4: (path set correctly)
```

### Service Health

```bash
# Check command
curl -s http://127.0.0.1:8780/health

# Response
{"status":"healthy","service":"content-request-handler","nats":"connected"}
```

---

## SKOREQ PLAN REFERENCE

| Field | Value |
|-------|-------|
| **Plan ID** | SKYBEAM-CONTENT-FACTORY-V1 |
| **Location** | `mindsong-juke-hub/docs/skoreq/SKYBEAM-CONTENT-FACTORY-V1/` |
| **Status** | Applied |
| **Committed** | `94c0ab9189` (2026-01-10) |
| **Stories** | 26 |
| **Total Points** | 311 |

---

## PIPELINE FLOW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SKYBEAM P0 PIPELINE (CERTIFIED)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  iPhone/HTTP POST                                                           │
│       │                                                                     │
│       ▼                                                                     │
│  content_request_handler.py (port 8780)                                     │
│       │ Creates job dir + manifest.json                                     │
│       │ Publishes to NATS: ghost.content.request                            │
│       ▼                                                                     │
│  skybeam_worker.py (NATS subscriber)                                        │
│       │ Receives job_id                                                     │
│       ▼                                                                     │
│  skybeam_p0_renderer.py                                                     │
│       │ 1. Write cards text                                                 │
│       │ 2. Generate TTS (espeak-ng or silent)                               │
│       │ 3. Create cards video (ffmpeg drawtext)                             │
│       │ 4. Mux master.mp4 (video + audio)                                   │
│       │ 5. ffprobe verification                                             │
│       │ 6. Update manifest.json                                             │
│       ▼                                                                     │
│  outputs/master.mp4 (CERTIFIED OUTPUT)                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## NEXT PHASE: Research & Intelligence Layer

### Stories Pending (Phase 2)

| ID | Title | Points | Priority | Status |
|----|-------|--------|----------|--------|
| SKYBEAM-STORY-006 | Build Trend Detector Service | 13 | high | COMPLETE |
| SKYBEAM-STORY-007 | Build Deep Research Agent | 21 | high | COMPLETE |
| SKYBEAM-STORY-008 | Build Competitor Analyzer | 13 | medium | COMPLETE |
| SKYBEAM-STORY-009 | Create n8n Research Workflow | 8 | high | COMPLETE |

### Files to Create

```
~/.roxy/services/research/
├── __init__.py
├── trend_detector.py       # STORY-006
├── deep_research_agent.py  # STORY-007
└── competitor_analyzer.py  # STORY-008

~/.roxy/n8n-workflows/
└── skybeam_research.json   # STORY-009
```

---

## COMMANDS REFERENCE

```bash
# Check services
systemctl --user status roxy-content-handler roxy-skybeam-worker

# Health check
curl -s http://127.0.0.1:8780/health

# Submit content request
curl -X POST http://127.0.0.1:8780/api/content/request \
  -H "Authorization: Bearer $(cat ~/.roxy/secret.token)" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Test topic"}'

# List jobs
curl -s http://127.0.0.1:8780/api/content/jobs \
  -H "Authorization: Bearer $(cat ~/.roxy/secret.token)"

# View worker logs
journalctl --user -u roxy-skybeam-worker -f

# Publish ghost state
python3 ~/.roxy/services/ghost_publisher.py
```

---

## COMMIT SANDBOX PROTOCOL

**Status:** OPERATIONAL (2026-01-11)

### Purpose

Enables ROXY/Mac Pro agents to commit to mindsong-juke-hub safely without breaking governance, while Mac Studio remains merge authority.

### Commits

| Location | Commit | Description |
|----------|--------|-------------|
| Main (Mac Studio) | `43e64270d3` | Initial sandbox scripts |
| Main (Mac Studio) | `89fad3c1dd` | Path check bug fix |
| Main (Mac Studio) | `4bd6f2af91` | Common failure modes docs |
| Main (Mac Studio) | `8850306be5` | Selftest smoke script |
| Sandbox (ROXY) | `9f3d2201` | Protocol proof test |
| Sandbox (ROXY) | `664f7e8f` | Cleanup of proof test |

### Active Feature Branch

- **Branch:** `roxy/macpro-linux/20260110-sandbox-proof`
- **Remote:** `origin/roxy/macpro-linux/20260110-sandbox-proof`
- **Purpose:** Sandbox protocol proof-of-concept
- **Status:** Ready for merge on Mac Studio (if desired)

### Files Delivered

```
scripts/governance/
├── bootstrap-sandbox.sh     # Create sandbox clone
├── commit-sandbox.mjs       # 5-gate commit protocol
├── push-sandbox.mjs         # Protected branch push gate
└── selftest-sandbox.sh      # Smoke test (5/5 passing)

docs/agent-breakroom/skills/
└── roxy-commit-sandbox.md   # Full documentation
```

### Proven Gates

| Gate | Test | Result |
|------|------|--------|
| Gate 1 | Sandbox path verification | ✅ PROVEN |
| Gate 2 | Branch naming (roxy/<host>/<date>-<slug>) | ✅ PROVEN |
| Gate 3 | Allowlist enforcement | ✅ PROVEN (blocked test-outside-allowlist.txt) |
| Gate 4 | ALLOW_SKORE_EDIT flag for SKORE files | ✅ PROVEN |
| Gate 5 | SKOREQ validation | ✅ PROVEN (skipped when validator absent) |
| Push Gate | Protected branch rejection | ✅ PROVEN (blocked push to main) |

### Known Operational Hazards

1. **bun not in PATH on SSH**: Use `source ~/.zshrc` before git commands on Mac Studio
2. **Sparse checkout**: Only allowlisted paths are checked out; other files appear missing
3. **HTTPS vs SSH**: Sandbox uses HTTPS by default; SSH keys may not be configured

---

## UPDATE PROTOCOL

When updating this document:

1. Update `Last Updated` timestamp
2. Update `Updated By` field
3. Add evidence paths for any new certified artifacts
4. Update phase/story status tables
5. Keep pipeline diagram current

**This document must reflect reality. If reality differs, fix the document OR fix reality.**

---

*Generated: 2026-01-10 by Master Chief (Claude Opus 4.5)*
