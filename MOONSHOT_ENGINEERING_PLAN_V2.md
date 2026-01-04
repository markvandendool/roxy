# 🚀 ROCKY-ROXY MOONSHOT ENGINEERING PLAN V2
## Post-Epic Analysis: What's Done, What's Not, What's Different

**Date:** January 4, 2026  
**Status:** Engineering-Grade Synthesis  
**Previous Work:** ROCKY-ROXY-ROCKIN-V1 (144 points, 103 tests)

---

## 📊 INFRASTRUCTURE AUDIT RESULTS

### Hardware Confirmed
| Resource | Status | Details |
|----------|--------|---------|
| GPU 0 | ✅ AMD | 14% VRAM used, 250W TDP |
| GPU 1 | ✅ AMD | 1% VRAM used, 255W TDP |
| ROCm | ✅ Installed | rocm-smi operational |
| Total GPU Memory | ~32GB+ | Dual GPU setup confirmed |

### Models Available (Ollama)
| Model | Size | Purpose |
|-------|------|---------|
| `tinyllama:latest` | 637 MB | **DRAFT** - Speculative decoding |
| `phi:2.7b` | 1.6 GB | Fast responses |
| `llama3.2:1b` | 1.3 GB | Ultra-fast draft |
| `deepseek-coder:6.7b` | 3.8 GB | Code generation |
| `llama3:8b` | 4.7 GB | General purpose |
| `qwen2.5-coder:14b` | 9.0 GB | Heavy code tasks |
| `qwen2.5:32b` | 19 GB | **TARGET** - Verification |
| `nomic-embed-text` | 274 MB | Embeddings |

### Services Running
| Service | Port | Status |
|---------|------|--------|
| ROXY Core | 8766 | ✅ Live |
| Whisper STT | 10300 | ✅ Live |
| Piper TTS | 10200 | ✅ Live |
| OpenWakeWord | 10400 | ✅ Live |
| ChromaDB | 8000 | ✅ Live |
| Ollama | 11434 | ✅ Live |
| n8n | 5678 | ✅ Live |
| Luno Orchestrator | 3000 | ✅ Live |
| Friday/Citadel | 10.0.0.65:8765 | ✅ Live |

---

## 🎯 MOONSHOT STATUS MATRIX

### 1. "Hey Rocky" Voice-First Music Teacher

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| Wake word detection | ✅ DONE | `voice_integration.py` | Single word only |
| Whisper STT | ✅ DONE | Port 10300 | - |
| Piper TTS | ✅ DONE | Port 10200 | - |
| Voice pipeline | ✅ DONE | `mcp_voice.py` | - |
| Rocky brain | ✅ DONE | `mcp_rocky.py` | Needs music knowledge |
| **Dual wake word** | ❌ NOT DONE | - | Need "Hey Rocky" + "Hey Roxy" |
| **Music-aware routing** | ❌ NOT DONE | - | Route music → Rocky, dev → Roxy |
| **Apollo integration** | ❌ NOT DONE | - | Voice → chord playback |

**Implementation Needed:**
```python
# ~/.roxy/dual_wake_word.py
WAKE_WORDS = {
    "hey rocky": {"persona": "music_teacher", "voice": "rocky"},
    "hey roxy": {"persona": "dev_assistant", "voice": "roxy"}
}
```

---

### 2. Speculative Decoding (Dual GPU)

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| Two GPUs | ✅ HAVE | ROCm confirmed | - |
| Small draft model | ✅ HAVE | tinyllama:637MB | - |
| Large target model | ✅ HAVE | qwen2.5:32b | - |
| Ollama backend | ✅ HAVE | Port 11434 | - |
| **Speculative engine** | ❌ NOT DONE | - | Need draft→verify pipeline |
| **GPU routing** | ❌ NOT DONE | - | tinyllama→GPU0, qwen→GPU1 |

**Implementation Needed:**
```python
# ~/.roxy/speculative_decoder.py
class SpeculativeDecoder:
    draft_model = "tinyllama:latest"  # GPU[0]
    target_model = "qwen2.5:32b"      # GPU[1]
    
    async def generate(self, prompt: str, num_tokens: int = 8):
        # 1. Draft 8 tokens on fast model
        draft = await self.ollama.generate(self.draft_model, prompt)
        # 2. Verify batch on large model
        verified = await self.ollama.verify(self.target_model, draft)
        # 3. Accept matching tokens, re-draft from divergence
        return verified
```

**Benefit:** 2-3x faster inference for real-time responses

---

### 3. WebGPU Rocky (Browser-Local LLM)

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| WebGPU infrastructure | ✅ PARTIAL | `webgpu-dual-canvas-demo/` | For rendering, not LLM |
| ONNX Runtime Web | ✅ HAVE | `package.json` | Installed |
| WebAssembly build | ✅ HAVE | wasm-pack scripts | - |
| **WebLLM** | ❌ NOT DONE | - | Need @mlc-ai/web-llm |
| **Browser RAG** | ❌ NOT DONE | - | IndexedDB vector store |
| **Local model cache** | ❌ NOT DONE | - | ServiceWorker caching |

**Implementation Needed:**
```typescript
// ~/mindsong-juke-hub/src/rocky/WebRocky.ts
import { CreateEngine } from '@mlc-ai/web-llm';

export class WebRocky {
    private engine: any;
    
    async init() {
        this.engine = await CreateEngine("Qwen2.5-1.5B-Instruct-q4f16_1-MLC");
    }
    
    async chat(message: string): Promise<string> {
        return this.engine.chat.completions.create({
            messages: [
                { role: "system", content: ROCKY_MUSIC_TEACHER_PROMPT },
                { role: "user", content: message }
            ]
        });
    }
}
```

**Benefit:** Zero server cost, offline capability, infinite scale

---

### 4. Federated Learning (Privacy-Preserving)

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| Local storage | ✅ HAVE | IndexedDB, localStorage | - |
| Student profiles | ❌ NOT DONE | - | Need schema |
| **Gradient aggregation** | ❌ NOT DONE | - | Complex ML infrastructure |
| **Privacy layer** | ❌ NOT DONE | - | Differential privacy |

**Status:** 🔮 FUTURE - Requires significant ML infrastructure
**Priority:** LOW - Focus on core features first

---

### 5. MCP Gateway (Music-Specific Tools)

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| MCP infrastructure | ✅ DONE | `~/.roxy/mcp/` | 95 tools |
| Rocky bridge | ✅ DONE | `mcp_rocky.py` | 7 tools |
| Cross-pollination | ✅ DONE | `mcp_cross_pollination.py` | 17 tools |
| **play_chord** | ❌ NOT DONE | - | Apollo integration |
| **analyze_audio** | ❌ NOT DONE | - | Music analysis |
| **generate_notation** | ❌ NOT DONE | - | Sheet music |
| **search_songs** | ❌ NOT DONE | - | Chord progression search |

**Implementation Needed:**
```python
# ~/.roxy/mcp/mcp_music_tools.py

@tool
async def play_chord(chord: str, instrument: str = "piano"):
    """Play a chord through Apollo audio engine"""
    # Send to Apollo via WebSocket
    
@tool
async def analyze_audio(audio_path: str):
    """Analyze audio for chords, tempo, key"""
    # Use Whisper + custom music model
    
@tool
async def generate_notation(description: str):
    """Generate sheet music from description"""
    # Use OSMD (OpenSheetMusicDisplay)
    
@tool
async def search_songs_by_progression(progression: str):
    """Search song database by chord progression"""
    # ChromaDB query
```

**Benefit:** Rocky becomes AGENTIC - can DO things, not just talk

---

### 6. Long-Term Memory Layers

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| Postgres memory | ✅ HAVE | `memory_postgres.py` | Exists but underused |
| ChromaDB | ✅ HAVE | Port 8000 | 2,805 docs |
| **Episodic memory** | ❌ NOT DONE | - | Session history |
| **Semantic memory** | ❌ NOT DONE | - | Music knowledge graph |
| **Procedural memory** | ❌ NOT DONE | - | Technique tracking |
| **Prospective memory** | ❌ NOT DONE | - | Next lesson planning |

**Implementation Needed:**
```python
# ~/.roxy/memory_layers.py

class RockyMemoryLayers:
    """Four-tier memory system for personalized teaching"""
    
    # EPISODIC: What happened in sessions
    async def remember_session(self, student_id, events):
        await self.postgres.insert("episodic", {...})
    
    # SEMANTIC: Music theory knowledge
    async def query_music_theory(self, concept):
        return await self.chromadb.query("music_theory", concept)
    
    # PROCEDURAL: How student progresses
    async def track_technique(self, student_id, skill, level):
        await self.postgres.upsert("procedural", {...})
    
    # PROSPECTIVE: What to teach next
    async def plan_next_lesson(self, student_id):
        history = await self.get_procedural(student_id)
        return self.suggest_next_topic(history)
```

---

### 7. Real-Time Jam AI

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| Audio input | ✅ HAVE | Whisper | - |
| Chord analysis | ❌ NOT DONE | - | Real-time detection |
| Apollo playback | ✅ PARTIAL | `src/apollo/` | Needs MIDI routing |
| **Real-time loop** | ❌ NOT DONE | - | <100ms latency |
| **Accompaniment AI** | ❌ NOT DONE | - | Generate complementary parts |

**Status:** 🔶 COMPLEX - Requires low-latency audio pipeline
**Priority:** MEDIUM - Impressive but technically demanding

---

### 8. Edge-Cloud Hybrid

| Component | Status | Location | Gap |
|-----------|--------|----------|-----|
| Browser layer | ✅ PARTIAL | React app | - |
| ROXY Citadel | ✅ DONE | Port 8766 | - |
| Cloud fallback | ✅ HAVE | Supabase | - |
| **Smart routing** | ❌ NOT DONE | - | Complexity-based routing |
| **Offline detection** | ❌ NOT DONE | - | ServiceWorker |
| **Progressive fallback** | ❌ NOT DONE | - | Browser → ROXY → Cloud |

**Implementation Needed:**
```typescript
// ~/mindsong-juke-hub/src/rocky/SmartRouter.ts

class RockySmartRouter {
    async route(query: string) {
        const complexity = this.assessComplexity(query);
        
        // Level 1: Browser (simple queries)
        if (complexity < 0.3 && this.webRocky.isReady()) {
            return this.webRocky.chat(query);
        }
        
        // Level 2: ROXY Citadel (medium queries)
        if (await this.roxyAvailable()) {
            return this.roxyClient.chat(query);
        }
        
        // Level 3: Cloud (fallback)
        return this.cloudClient.chat(query);
    }
}
```

---

## 📋 ENGINEERING-GRADE SPRINT PLAN

### Sprint 5: Dual Wake Word + Music MCP Tools (2 weeks)
**Points:** 40 | **Priority:** HIGH

| Story | Points | Description |
|-------|--------|-------------|
| RRR-019 | 8 | Dual wake word ("Hey Rocky" / "Hey Roxy") with persona switching |
| RRR-020 | 8 | Music-aware query routing (music→Rocky, dev→ROXY) |
| RRR-021 | 8 | `play_chord` MCP tool - Apollo integration |
| RRR-022 | 8 | `analyze_audio` MCP tool - chord/key detection |
| RRR-023 | 8 | `search_songs_by_progression` MCP tool - ChromaDB |

**Deliverables:**
- `~/.roxy/dual_wake_word.py`
- `~/.roxy/persona_router.py`
- `~/.roxy/mcp/mcp_music_tools.py`
- Apollo WebSocket bridge
- 25+ tests

---

### Sprint 6: Speculative Decoding Engine (2 weeks)
**Points:** 40 | **Priority:** HIGH

| Story | Points | Description |
|-------|--------|-------------|
| RRR-024 | 13 | Speculative decoder core (draft→verify pipeline) |
| RRR-025 | 8 | GPU routing (tinyllama→GPU0, qwen→GPU1) |
| RRR-026 | 8 | Batch verification with early acceptance |
| RRR-027 | 5 | Latency benchmarks (<500ms target) |
| RRR-028 | 6 | Integration with existing Rocky/ROXY pipelines |

**Deliverables:**
- `~/.roxy/speculative_decoder.py`
- `~/.roxy/gpu_router.py`
- Performance benchmarks
- 20+ tests

---

### Sprint 7: WebGPU Rocky (2 weeks)
**Points:** 40 | **Priority:** MEDIUM

| Story | Points | Description |
|-------|--------|-------------|
| RRR-029 | 13 | WebLLM integration (browser-local inference) |
| RRR-030 | 8 | IndexedDB vector store for browser RAG |
| RRR-031 | 8 | ServiceWorker model caching |
| RRR-032 | 5 | Offline detection and progressive fallback |
| RRR-033 | 6 | SmartRouter implementation |

**Deliverables:**
- `src/rocky/WebRocky.ts`
- `src/rocky/BrowserRAG.ts`
- `src/rocky/SmartRouter.ts`
- ServiceWorker model cache
- 20+ tests

---

### Sprint 8: Memory Layers + Polish (2 weeks)
**Points:** 40 | **Priority:** MEDIUM

| Story | Points | Description |
|-------|--------|-------------|
| RRR-034 | 13 | Four-tier memory system (episodic/semantic/procedural/prospective) |
| RRR-035 | 8 | Student profile schema and storage |
| RRR-036 | 8 | Music theory knowledge base (ChromaDB seeding) |
| RRR-037 | 5 | Next lesson recommender |
| RRR-038 | 6 | Full integration testing |

**Deliverables:**
- `~/.roxy/memory_layers.py`
- `~/.roxy/student_profiles.py`
- Music theory ChromaDB collection (1000+ concepts)
- 25+ tests

---

## 📊 TOTAL MOONSHOT ROADMAP

| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 1-4 | Foundation (DONE) | 144 | ✅ Complete |
| 5 | Dual Wake + Music Tools | 40 | 🔜 Next |
| 6 | Speculative Decoding | 40 | Planned |
| 7 | WebGPU Rocky | 40 | Planned |
| 8 | Memory Layers | 40 | Planned |

**Total Epic Points:** 304 points  
**Total Tests Target:** 250+  
**Timeline:** 8 weeks (Sprints 5-8)

---

## 🎯 IMMEDIATE NEXT ACTIONS

1. **Install WebLLM** (5 min)
   ```bash
   cd ~/mindsong-juke-hub && pnpm add @mlc-ai/web-llm
   ```

2. **Create dual_wake_word.py** (Sprint 5 Story 1)

3. **Seed music theory ChromaDB** (Sprint 8 prep)
   - Import music theory corpus
   - Index chord progressions, scales, techniques

4. **Benchmark speculative decoding** (Sprint 6 prep)
   - Test tinyllama draft speed
   - Test qwen2.5:32b verification speed
   - Measure token acceptance rates

---

## 🚀 THE MOONSHOT VISION

```
┌────────────────────────────────────────────────────────────────────┐
│                      ROCKY 2.0 ARCHITECTURE                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │    BROWSER      │   │  ROXY CITADEL   │   │     CLOUD       │  │
│  │   (WebGPU)      │   │   (Dual GPU)    │   │   (Fallback)    │  │
│  │                 │   │                 │   │                 │  │
│  │  WebLLM 1.5B    │   │  Speculative    │   │  Supabase Edge  │  │
│  │  IndexedDB RAG  │   │  Decoder        │   │  Claude/GPT     │  │
│  │  ServiceWorker  │   │  32GB GPU       │   │  Global CDN     │  │
│  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘  │
│           │                     │                     │            │
│           └─────────────────────┼─────────────────────┘            │
│                                 │                                  │
│                    ┌────────────▼────────────┐                     │
│                    │      SMART ROUTER       │                     │
│                    │  90% Browser → 9% ROXY  │                     │
│                    │      → 1% Cloud         │                     │
│                    └────────────┬────────────┘                     │
│                                 │                                  │
│                    ┌────────────▼────────────┐                     │
│                    │    UNIFIED MCP GATEWAY  │                     │
│                    │  play_chord │ analyze   │                     │
│                    │  search     │ remember  │                     │
│                    └────────────┬────────────┘                     │
│                                 │                                  │
│                    ┌────────────▼────────────┐                     │
│                    │  DUAL WAKE WORD + VOICE │                     │
│                    │  "Hey Rocky" │ "Hey Roxy"│                    │
│                    └────────────────────────┘                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

**CHIEF'S ASSESSMENT:** The manifesto is visionary. The infrastructure is 70% there. What's missing is the GLUE - speculative decoding, WebGPU inference, and the music-specific MCP tools that transform Rocky from a chatbot into a MUSIC TEACHING OPERATING SYSTEM.

**Sprints 5-8 deliver the remaining 30% that creates the moat.**

---

*Generated: January 4, 2026*  
*Agent: GitHub Copilot (Claude Opus 4.5)*
