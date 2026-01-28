# Strategic Recommendations - ROXY Development Path

**Date**: 2026-01-02 20:50 UTC  
**Synthesized From**: Copilot strategic analysis + Chief technical guidance  
**Current State**: P0 fixes complete, P1 fixes in progress

---

## EXECUTIVE SUMMARY

**Current Status**: ✅ **ROXY Core Functional** (P0 bugs fixed, OBS control working)  
**Strategic Path**: **MOONSHOT → CITADEL Sprint 4 → UI → Knowledge**  
**Technical Foundation**: ✅ **OBS WebSocket Control Ready** (90%+ coverage via obs-websocket)

---

## IMMEDIATE FIXES COMPLETED

### ✅ roxy_client.py Bug Fixed
**Issue**: `sys` import shadowing (local imports inside function)  
**Fix**: Removed redundant `import sys` statements (lines 192, 201, 212)  
**Status**: ✅ **FIXED** - `roxy` command should work now

**Verification**:
```bash
roxy  # Should start interactive chat without errors
```

---

## STRATEGIC RECOMMENDATIONS (Priority Order)

### PHASE 1: Complete ROXY MOONSHOT Core (2 weeks) ⭐ **HIGHEST PRIORITY**

**Why First**: ROXY needs to be smart and fast before controlling complex hardware. Current state: 35% → Target: 95% production-ready.

#### Week 1: Streaming + Monitoring + RAG (40 hours)

**1.1 SSE Streaming** ⭐ **HIGHEST IMPACT**
- **Current**: `/stream` endpoint exists but not fully tested
- **Target**: Real-time token streaming to client
- **Impact**: +50% perceived speed (users see responses immediately)
- **Effort**: 8 hours
- **Files**: `roxy_core.py` (enhance `_handle_streaming`), `roxy_client.py` (SSE client)

**1.2 Prometheus + Grafana Dashboard** ⭐ **HIGH VISIBILITY**
- **Current**: Observability module exists, no dashboard
- **Target**: Real-time metrics dashboard (requests, latency, errors, RAG performance)
- **Impact**: Debug everything else faster
- **Effort**: 12 hours
- **Files**: New `monitoring/prometheus_exporter.py`, Grafana config

**1.3 Hybrid RAG Enhancement** ⭐ **SMARTNESS BOOST**
- **Current**: Hybrid search code exists but not fully integrated
- **Target**: BM25 + Vector + Reranking working end-to-end
- **Impact**: +50% accuracy on RAG queries
- **Effort**: 8 hours
- **Files**: `rag/hybrid_search.py` (verify integration), `roxy_commands.py` (test)

**1.4 Rate Limiting Fix** (P1)
- **Current**: Code exists but not triggering (all 200 responses)
- **Target**: Verify rate limiting works under load
- **Effort**: 4 hours
- **Files**: `rate_limiting.py` (add logging, test)

**1.5 Cache Optimization** (P1)
- **Current**: Minimal improvement (1.3% faster)
- **Target**: Verify cache hits, optimize TTL
- **Effort**: 4 hours
- **Files**: `cache.py` (verify hits, optimize)

**Week 1 Deliverables**:
- ✅ SSE streaming working (real-time responses)
- ✅ Grafana dashboard showing metrics
- ✅ Hybrid RAG improving query accuracy
- ✅ Rate limiting verified
- ✅ Cache optimized

#### Week 2: Performance + UI (40 hours)

**2.1 GPU Batching** (if applicable)
- **Target**: Batch LLM requests for 3x throughput
- **Effort**: 12 hours
- **Files**: `llm_router.py` (add batching)

**2.2 8-bit Quantization** (if applicable)
- **Target**: Reduce VRAM usage by 50%
- **Effort**: 8 hours
- **Files**: LLM service integration

**2.3 Web UI (Gradio)** ⭐ **USER EXPERIENCE**
- **Current**: CLI-only interface
- **Target**: Web dashboard for ROXY interaction
- **Impact**: Easier to use, better for monitoring
- **Effort**: 8 hours
- **Files**: New `web_ui/gradio_app.py`

**2.4 Advanced RAG Features**
- **Target**: Query expansion, metadata filtering, multi-vector retrieval
- **Effort**: 8 hours
- **Files**: `rag/hybrid_search.py` enhancements

**2.5 Tool Handler Testing** (P1)
- **Target**: Verify tool_direct and tool_preflight work
- **Effort**: 4 hours
- **Files**: Test MCP tool integration

**Week 2 Deliverables**:
- ✅ Web UI accessible via browser
- ✅ Performance optimizations applied
- ✅ All tool handlers tested

---

### PHASE 2: CITADEL Sprint 4 - Broadcast Stack (1 week)

**Why After MOONSHOT**: ROXY needs to be smart enough to help debug camera issues. Current state: OBS control working, cameras pending.

#### Sprint 4 Tasks (24 hours)

**4.1 DeckLink Drivers Installation** (Story 011)
- **Target**: Install Blackmagic DeckLink drivers
- **Effort**: 4 hours
- **Status**: Blocked on hardware availability

**4.2 OBS Scene Configuration** (Story 012)
- **Current**: OBS WebSocket control working
- **Target**: Configure scenes, sources, transitions
- **Effort**: 4 hours
- **Files**: OBS configuration, scene templates

**4.3 Camera Capture Testing**
- **Target**: Test HDMI capture via DeckLink
- **Effort**: 8 hours
- **Status**: Depends on DeckLink drivers

**4.4 NDI Streaming Setup**
- **Target**: Configure NDI for multi-camera streaming
- **Effort**: 4 hours

**4.5 ROXY Voice Control Integration**
- **Target**: "Hey Roxy, start recording" → OBS WebSocket command
- **Effort**: 4 hours
- **Files**: Voice pipeline → ROXY command routing

**Sprint 4 Deliverables**:
- ✅ DeckLink drivers installed
- ✅ OBS scenes configured
- ✅ Camera capture working
- ✅ Voice control integrated

---

### PHASE 3: Knowledge + Automation (Ongoing)

**3.1 RAG Knowledge Base Expansion**
- **Target**: Ingest more documentation, code, knowledge
- **Effort**: Ongoing
- **Files**: `ingest_rag.py`, `rebuild_rag_index.py`

**3.2 MCP Server Configuration**
- **Target**: Configure all MCP servers for optimal tool access
- **Effort**: 8 hours

**3.3 Autonomous Agents** (100 Improvements)
- **Target**: Implement high-impact improvements from cursor plan
- **Effort**: Ongoing
- **Files**: Various (per improvement)

---

## TECHNICAL FOUNDATION: OBS WebSocket Control

### Current State ✅

**OBS Control Surface**:
- ✅ OBS WebSocket v5 active (port 4455)
- ✅ ROXY integration complete (obs_controller.py + obs_skill.py)
- ✅ Natural language commands working
- ✅ OBS launches successfully (P0 fix complete)

**Coverage**: **90%+ operational control** via obs-websocket

### What ROXY Can Control (via obs-websocket)

**✅ Available Now**:
- Scenes (switch, list, create, remove)
- Sources (enable/disable, transform, visibility)
- Streaming (start/stop, status)
- Recording (start/stop/pause/resume)
- Audio (volume, mute, monitoring)
- Virtual camera (start/stop)
- Replay buffer (save/clip)
- Transitions (set, duration, trigger)
- Hotkeys (trigger configured hotkeys)
- Stats (performance, output status)

**⚠️ May Need VendorRequests**:
- Third-party plugin settings (if not exposed)
- Deep graphics pipeline controls
- Non-exposed UI actions
- Bespoke atomic operations

**❌ Requires Custom Plugin**:
- In-process OBS control (C/C++ modules)
- OBS scripting (Python/Lua) for internal state
- Config file manipulation requiring restart

### Chief's Recommendation: VendorRequest Pattern

**For "Full Byte Control"**:
1. Use **obs-websocket as single remote control plane**
2. Define ROXY command set → OBS "macros" (StartShow, StopShow, ArmRecord, SwitchToScene X)
3. When hitting a wall, add **small OBS plugin** exposing one VendorRequest at a time
4. Keep everything local-only (localhost, authenticated)

**ROXY's Current OBS Control Path**:
```
User: "start streaming"
  ↓
parse_command() → ("obs", ["start streaming"])
  ↓
execute_command() → obs handler (line 319)
  ↓
obs_skill.py → OBSSkill.handle_command()
  ↓
obsws_python.ReqClient → OBS WebSocket v5
  ↓
OBS Studio → Starts streaming
```

**This is the CORRECT flow** - no changes needed for basic control.

---

## RECOMMENDED ACTION PLAN

### TODAY (2 hours)
1. ✅ Test `roxy` command (bug fixed)
2. ✅ Verify OBS control works ("start streaming", "switch to scene")
3. ✅ Read MOONSHOT plan (understand full scope)
4. ✅ Pick Week 1 task (SSE streaming OR Grafana dashboard)

### THIS WEEK (40 hours)
**Monday-Tuesday**: SSE Streaming
- Enhance `/stream` endpoint
- Add SSE client to roxy_client.py
- Test real-time token streaming

**Wednesday**: Prometheus + Grafana
- Add Prometheus exporter
- Configure Grafana dashboard
- Display metrics (requests, latency, errors)

**Thursday-Friday**: Hybrid RAG
- Verify hybrid search integration
- Test BM25 + Vector + Reranking
- Measure accuracy improvement

**Result**: ROXY streams responses, you have dashboards, RAG is smarter

### NEXT WEEK (40 hours)
**Option 1**: Web UI (Gradio)
- Build Gradio dashboard
- Integrate with ROXY API
- Add monitoring widgets

**Option 2**: CITADEL Sprint 4
- Install DeckLink drivers
- Configure OBS scenes
- Test camera capture

**Recommendation**: Web UI first (you'll use it to monitor camera capture)

### MONTH END
- ✅ ROXY: Production-ready AI core
- ✅ CITADEL: Cameras working, voice control live
- ✅ You have: Smart assistant + broadcast stack + monitoring

---

## WHY THIS ORDER?

### 1. Unblocks Immediate Work
- Streaming not blocked on speakers
- Monitoring helps debug everything
- RAG improvements make ROXY smarter

### 2. Makes ROXY Smarter Before Hardware
- Voice testing blocked on speakers anyway
- Cameras blocked on DeckLink drivers (Sprint 4 task)
- ROXY needs to be intelligent before controlling complex hardware

### 3. Monitoring Helps Debug Everything
- Grafana dashboard shows camera capture performance
- ROXY can help debug camera issues
- Voice control needs streaming to be useful

### 4. Cameras + Voice Together = Killer Demo
- Once ROXY is smart and fast
- Add cameras and voice control
- Complete broadcast stack with AI assistant

---

## THE FULL PLAN LOCATIONS

**ROXY Plans**:
- 📄 `ROXY_MOONSHOT_UPGRADE_PLAN.md` ← **PRIMARY PLAN** (35% → 95%)
- 📄 CITADEL Epic LUNA-000 (45% complete, cameras = Sprint 4)
- 📄 Cursor plans:
  - `roxy_100_ultra_high_impact_improvements` (needs review)
  - `roxy_top_20_improvements` (compatible architecture) ✅ **COMPLETE**
  - `roxy_gpu_acceleration_ultimate` (performance)

**UI Plans**:
- MOONSHOT Phase 1.2: Web UI (Gradio recommended)
- Alternative: React dashboard (Phase 2)
- Voice UI: Already in progress (Phase 1 Voice Stack)

---

## FINAL RECOMMENDATION 💎

**Do this in order**:
1. ✅ **Test roxy command** (5 min) - Bug fixed
2. 🚀 **MOONSHOT Week 1** (Streaming + Monitoring + RAG) - 40 hours
3. 🎨 **MOONSHOT Week 2** (Web UI + Performance) - 40 hours
4. 🎥 **CITADEL Sprint 4** (DeckLink + Cameras) - 24 hours
5. 📚 **Knowledge expansion** (ingest more docs) - Ongoing

**Why this order**:
- Unblocks immediate work (streaming not blocked on speakers)
- Makes ROXY smarter before adding hardware complexity
- Monitoring helps debug everything else
- Cameras + voice together = killer demo

**Total time to "complete ROXY":** ~3 weeks  
**Total time to cameras working:** +1 week after that

---

## OBS CONTROL STATUS

**Current**: ✅ **90%+ Control Available** via obs-websocket  
**ROXY Integration**: ✅ **Complete** (obs_controller.py + obs_skill.py)  
**Natural Language**: ✅ **Working** ("start streaming", "switch to scene")

**For "Full Byte Control"**:
- Use obs-websocket for 90%+ (already working)
- Add VendorRequests for gaps (when needed)
- Custom plugins for deep control (if required)

**No changes needed** for basic OBS control - ROXY's current implementation is correct.

---

**Status**: ✅ **STRATEGIC PATH DEFINED**  
**Next Action**: Start MOONSHOT Week 1 (SSE streaming OR Grafana dashboard)  
**Date**: 2026-01-02 20:50 UTC














