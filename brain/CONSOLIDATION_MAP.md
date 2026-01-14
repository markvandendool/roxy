# ROXY Documentation Consolidation Map
## Project SKYBEAM — Brain Structure

**Date:** 2026-01-10
**Total Files to Organize:** 992+ MD files

---

## Brain Directory Structure

```
~/.roxy/brain/
├── 00_START_HERE.md          # Entry point for all agents
├── 00_start/                 # Quick start materials
├── 01_onboarding/            # Agent onboarding docs
├── 02_architecture/          # System architecture
├── 03_howto/                 # Operational guides
├── 04_skills/                # Agent skills (like agent-breakroom)
├── 05_reference/             # Reference documentation
├── 06_legacy/                # Archived/historical docs
└── plans/                    # Strategic plans (CRM, etc.)
```

---

## Files to KEEP at Root Level

These are critical entry points that should remain at `~/.roxy/`:

| File | Purpose |
|------|---------|
| `PROJECT_SKYBEAM.md` | Master infrastructure map |
| `SKYBEAM_INDEX.yaml` | Agent navigation index |
| `SKYBEAM_CONSOLIDATION_PROPOSAL.md` | Architecture proposal |
| `README.md` | Repository entry point |
| `QUICK_START.md` | Quick start guide |
| `QUICK_REFERENCE.md` | Quick reference card |

---

## Consolidation Categories

### 01_onboarding/ (Agent Onboarding)
Move these files for new agent orientation:
- HOW_TO_TALK_TO_ROXY.md
- HOW_TO_USE_VOICE.md
- WELCOME_PACKAGE.md
- JARVIS_GUIDE.md
- ROXY_EXPLANATION.md

### 02_architecture/ (System Architecture)
Move these for architecture understanding:
- ARCHITECTURE.md
- FULL_CONTROL_ARCHITECTURE.md
- ROXY_FULL_STACK_MAP.md
- INFRASTRUCTURE_INVENTORY.md
- CITADEL_*.md (deployment series)
- GHOST_PROTOCOL_MAP.md
- UNIVERSE.md

### 03_howto/ (Operational Guides)
Move these for operational procedures:
- GPU_SETUP_GUIDE.md
- GPU_OPTIMIZATION_SUMMARY.md
- WAYLAND_IMPLEMENTATION_GUIDE.md
- WAYLAND_MIGRATION_GUIDE.md
- IPHONE_RDP_SETUP.md
- IPHONE_VNC_SETUP.md
- LOGITECH_MOUSE_SETUP.md
- BLUETOOTH_AUDIO_MIDI_SETUP.md
- PERMANENT_OPTIMIZATIONS_GUIDE.md
- SERVICE_MANAGEMENT.md
- TOP_BAR_MONITOR_GUIDE.md
- RESUME_INDEXING_GUIDE.md

### 05_reference/ (Reference Docs)
Move these for reference material:
- ROXY_HUB_REFERENCE.md
- SECURITY_HARDENING.md
- SECURITY.md
- MINDSONG_API_INTEGRATIONS.md
- MINDSONG_JUKEHUB_APIS.md
- INDUSTRY_BEST_PRACTICES.md
- SCORECARD_RUBRIC_V2.md

### 06_legacy/ (Historical/Archived)
Move these for historical context (already 120+ files here):
- All *_AUDIT_*.md
- All *_REPORT*.md
- All *_COMPLETE*.md
- All IMPLEMENTATION_*.md
- All PHASE*_*.md
- CHIEF_*.md series
- MOONSHOT_*.md series
- TOP_20_*.md series
- DEPLOYMENT_REPORT.md
- ENGINEERING_AUDIT_REPORT.md
- FIX_*.md series
- ERROR_*.md series
- STRESS_TEST_RESULTS.md

---

## Execution Commands

```bash
# Move onboarding docs
mv ~/.roxy/HOW_TO_TALK_TO_ROXY.md ~/.roxy/brain/01_onboarding/
mv ~/.roxy/HOW_TO_USE_VOICE.md ~/.roxy/brain/01_onboarding/
mv ~/.roxy/WELCOME_PACKAGE.md ~/.roxy/brain/01_onboarding/
mv ~/.roxy/JARVIS_GUIDE.md ~/.roxy/brain/01_onboarding/
mv ~/.roxy/ROXY_EXPLANATION.md ~/.roxy/brain/01_onboarding/

# Move architecture docs
mv ~/.roxy/ARCHITECTURE.md ~/.roxy/brain/02_architecture/
mv ~/.roxy/FULL_CONTROL_ARCHITECTURE.md ~/.roxy/brain/02_architecture/
mv ~/.roxy/ROXY_FULL_STACK_MAP.md ~/.roxy/brain/02_architecture/
mv ~/.roxy/INFRASTRUCTURE_INVENTORY.md ~/.roxy/brain/02_architecture/
mv ~/.roxy/GHOST_PROTOCOL_MAP.md ~/.roxy/brain/02_architecture/
mv ~/.roxy/UNIVERSE.md ~/.roxy/brain/02_architecture/
mv ~/.roxy/CITADEL_*.md ~/.roxy/brain/02_architecture/

# Move howto docs
mv ~/.roxy/GPU_SETUP_GUIDE.md ~/.roxy/brain/03_howto/
mv ~/.roxy/GPU_OPTIMIZATION_SUMMARY.md ~/.roxy/brain/03_howto/
mv ~/.roxy/WAYLAND_*.md ~/.roxy/brain/03_howto/
mv ~/.roxy/IPHONE_*.md ~/.roxy/brain/03_howto/
mv ~/.roxy/LOGITECH_MOUSE_SETUP.md ~/.roxy/brain/03_howto/
mv ~/.roxy/BLUETOOTH_AUDIO_MIDI_SETUP.md ~/.roxy/brain/03_howto/
mv ~/.roxy/PERMANENT_OPTIMIZATIONS_GUIDE.md ~/.roxy/brain/03_howto/
mv ~/.roxy/SERVICE_MANAGEMENT.md ~/.roxy/brain/03_howto/
mv ~/.roxy/TOP_BAR_MONITOR_*.md ~/.roxy/brain/03_howto/
mv ~/.roxy/RESUME_INDEXING_GUIDE.md ~/.roxy/brain/03_howto/

# Move reference docs
mv ~/.roxy/ROXY_HUB_REFERENCE.md ~/.roxy/brain/05_reference/
mv ~/.roxy/SECURITY_HARDENING.md ~/.roxy/brain/05_reference/
mv ~/.roxy/SECURITY.md ~/.roxy/brain/05_reference/
mv ~/.roxy/MINDSONG_*.md ~/.roxy/brain/05_reference/
mv ~/.roxy/INDUSTRY_BEST_PRACTICES.md ~/.roxy/brain/05_reference/
mv ~/.roxy/SCORECARD_RUBRIC_V2.md ~/.roxy/brain/05_reference/

# Move legacy docs (bulk)
mv ~/.roxy/*AUDIT*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/*REPORT*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/*COMPLETE*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/IMPLEMENTATION_*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/PHASE*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/CHIEF*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/MOONSHOT*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/TOP_20_*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/FIX_*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/ERROR_*.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/STRESS_TEST_RESULTS.md ~/.roxy/brain/06_legacy/ 2>/dev/null
mv ~/.roxy/DEPLOYMENT_REPORT.md ~/.roxy/brain/06_legacy/ 2>/dev/null
```

---

## Post-Consolidation Verification

After running the moves:
```bash
# Count files in each directory
for dir in ~/.roxy/brain/0*/; do
  echo "$(basename $dir): $(ls -1 $dir 2>/dev/null | wc -l) files"
done

# Count remaining root files
ls ~/.roxy/*.md 2>/dev/null | wc -l
```

---

## Note

This consolidation preserves all files (move, not delete). The 06_legacy/ directory acts as an archive for historical documentation that may have value for context but isn't actively needed.
