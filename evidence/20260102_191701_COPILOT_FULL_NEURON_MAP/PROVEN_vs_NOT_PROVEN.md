# PROVEN vs NOT PROVEN - Zero-Trust Truth Table

**Evidence Bundle**: `20260102_191701_COPILOT_FULL_NEURON_MAP`  
**Methodology**: ZERO-TRUST (every claim backed by artifact)  
**Date**: 2026-01-02 19:17-19:25 UTC

---

## PROVEN (Evidence-Backed)

| # | Claim | Evidence | Reproduce Command |
|---|-------|----------|-------------------|
| 1 | Port 8765 owned by PID 11275 (mcp_server.py) | port_8765_lsof.txt, port_8765_owner_ps.txt | `lsof -nP -iTCP:8765 -sTCP:LISTEN` |
| 2 | Port 8766 owned by PID 809812 (roxy_core.py) | port_8766_lsof.txt, port_8766_owner_ps.txt | `lsof -nP -iTCP:8766 -sTCP:LISTEN` |
| 3 | roxy-core.service running 15h+ uptime | systemd_roxy_core_status.txt | `systemctl --user status roxy-core` |
| 4 | MCP server has 21 tools (git, docker, obs, rag) | health_8765_verbose.txt | `curl http://127.0.0.1:8765/health` |
| 5 | ROXY core responds to /health | health_8766_verbose.txt | `curl http://127.0.0.1:8766/health` |
| 6 | 119 Python files in ~/.roxy (excluding venv) | py_file_count.txt, py_file_index.txt | `find ~/.roxy -name "*.py" \| grep -v venv \| wc -l` |
| 7 | Core files compile without errors | py_compile_core.txt | `python3 -m py_compile roxy_core.py roxy_commands.py` |
| 8 | DefaultEmbeddingFunction produces 384-dim vectors | embedding_dim_proof.txt | `python3 -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; print(len(DefaultEmbeddingFunction()(['test'])[0]))"` |
| 9 | ChromaDB has 2 collections: roxy_cache (24), mindsong_docs (40) | chroma_collections_proof.txt | `python3 -c "import chromadb; client=chromadb.PersistentClient(path=str(Path.home()/'.roxy'/'chroma_db')); print([c.name for c in client.list_collections()])"` |
| 10 | parse_command returns 13 distinct cmd_types | parse_command_returns.txt | `grep 'return .*(".*"' ~/.roxy/roxy_commands.py` |
| 11 | execute_command has 11 handler branches | handler_branches.txt | `grep 'cmd_type == "' ~/.roxy/roxy_commands.py` |
| 12 | "hi roxy" routes to RAG (3/3 tests) | api_hi_roxy_1.json, api_hi_roxy_2.json, api_hi_roxy_3.json | `curl -H "X-ROXY-Token: $TOKEN" -d '{"command":"hi roxy"}' http://127.0.0.1:8766/run` |
| 13 | "what is new today" routes to RAG (3/3 tests) | api_status_today_1.json, api_status_today_2.json, api_status_today_3.json | `curl -H "X-ROXY-Token: $TOKEN" -d '{"command":"what is new today"}' http://127.0.0.1:8766/run` |
| 14 | RAG query "what is roxy" works | api_what_is_roxy.json | `curl -H "X-ROXY-Token: $TOKEN" -d '{"command":"what is roxy"}' http://127.0.0.1:8766/run` |
| 15 | Batch endpoint executes 2 commands | api_batch_ping_health.json | `curl -X POST -H "X-ROXY-Token: $TOKEN" -d '{"commands":["ping","health"]}' http://127.0.0.1:8766/batch` |
| 16 | "open obs" routes to obs handler (NOT launch_app) | api_open_obs.json | `curl -H "X-ROXY-Token: $TOKEN" -d '{"command":"open obs"}' http://127.0.0.1:8766/run` |
| 17 | OBS does NOT launch when commanded | obs_before.txt, obs_after.txt, obs_launch_diff.txt | `pgrep obs` before/after API call |
| 18 | ingest process (PID 4059773) running 2+ days | phase0_ingest_detail.txt | `ps -fp 4059773` |
| 19 | roxy-voice.service is active | systemd_related_units.txt | `systemctl --user list-units \| grep roxy` |
| 20 | Authentication requires X-ROXY-Token header | All api_*.json files succeeded with token | `curl -d '{"command":"health"}' http://127.0.0.1:8766/run` (fails without token) |

**PROVEN Count**: 20

---

## NOT PROVEN (Missing Evidence)

| # | Claim | Why Not Proven | What's Needed |
|---|-------|----------------|---------------|
| 1 | Greeting fastpath exists | No fastpath code found in roxy_core.py, all greetings route to RAG | Fastpath implementation or cache hit evidence |
| 2 | "open obs" launches OBS | obs_launch_diff.txt is empty, pgrep before/after identical | Process diff showing OBS started |
| 3 | launch_app handler exists | handler_branches.txt has no "launch_app" branch | Implementation at roxy_commands.py execute_command |
| 4 | Cursor modules (hybrid_search, llm_router, security, feedback) are integrated | Files exist (sha256_all_py.txt) but no import evidence | `grep -r "import.*hybrid_search" ~/.roxy` with results |
| 5 | Truth Gate actively validates responses | truth_gate.py exists but no callsite found | Journal logs showing Truth Gate validation |
| 6 | Rate limiting enforces 10 req/min for /run | Code exists (line 204) but not stress tested | 15 concurrent requests, some 429 responses |
| 7 | Rate limiting enforces 5 req/min for /batch | Code exists (line 338) but not stress tested | 10 concurrent batch requests, some 429 responses |
| 8 | CLI --once flag works | Not tested in this audit | `~/.roxy/venv/bin/python ~/.roxy/roxy_client.py --once "health"` |
| 9 | CLI --stream flag works | Not tested in this audit | `~/.roxy/venv/bin/python ~/.roxy/roxy_client.py --stream "hi"` |
| 10 | Cache returns hits for identical queries | Cache enabled but no hit evidence | Run same query twice, check journal for "cache hit" log |
| 11 | tool_direct handler executes MCP tools | Handler exists (line 353) but untested | `curl -d '{"command":"use git tool status"}' ...` |
| 12 | tool_preflight orchestrates multi-step tools | Handler exists (line 368) but untested | `curl -d '{"command":"docs about README"}' ...` |
| 13 | briefing returns actual briefing (not placeholder) | Returns placeholder: "Briefing feature coming soon" | Actual daily summary with git activity, events |
| 14 | Advanced RAG path (/opt/roxy/services/adapters) active | Path exists but not tested | Evidence of advanced RAG being called |
| 15 | Security module sanitizes input | Import exists (roxy_core.py:232) but filtering not verified | Blocked command evidence (403 response with warnings) |
| 16 | Observability logs requests | Import exists (roxy_core.py:268) but logs not verified | Observability log files with request traces |
| 17 | Subprocess timeouts enforced | timeout=30 in code but not stress tested | Long-running command evidence (>30s subprocess killed) |
| 18 | context_manager provides conversation context | Import exists (roxy_core.py:408) but not verified | Multi-turn conversation with context carryover |
| 19 | Evaluation metrics recorded | Import exists (roxy_core.py:280) but logs not verified | Metrics database/file with query performance data |
| 20 | ingestion process uses 384-dim embeddings | Process running but dimension not verified | `grep DefaultEmbeddingFunction /opt/roxy/scripts/index_mindsong_repo_resume.py` |

**NOT PROVEN Count**: 20

---

## PARTIAL (Some Evidence, Incomplete)

| # | Claim | Evidence For | Evidence Against | What's Missing |
|---|-------|--------------|------------------|----------------|
| 1 | Cache is functional | cache_enabled=true in health check | No cache hit logs in this audit | Evidence of cache hit with timing improvement |
| 2 | OBS WebSocket control works | obs handler exists (line 319) | Connection failed in test (OBS not running) | Test with OBS running and WebSocket enabled |
| 3 | Embedding uniformity (384-dim) | roxy_cache & mindsong_docs both 384-dim, production code uses DefaultEmbeddingFunction | Advanced RAG path not verified, ingestion script not checked | Audit /opt/roxy/services/adapters and ingestion script |

**PARTIAL Count**: 3

---

## SUMMARY STATISTICS

**Total Claims Evaluated**: 43  
**PROVEN** (evidence-backed): 20 (46.5%)  
**NOT PROVEN** (no evidence): 20 (46.5%)  
**PARTIAL** (incomplete evidence): 3 (7.0%)

**Evidence Quality**: ✅ **HIGH** (all PROVEN claims have reproducible commands)  
**Audit Coverage**: ⚠️ **MODERATE** (46.5% proven, 53.5% gaps)

---

## CRITICAL GAPS (P0)

1. ❌ **Greeting Fastpath**: NOT PROVEN (all greetings route to RAG, 3-5 sec delay)
2. ❌ **OBS Launch**: NOT PROVEN (does not launch OBS, routes to WebSocket)
3. ❌ **launch_app Handler**: NOT PROVEN (parsed but no handler implementation)
4. ⚠️ **Cursor Modules Integration**: NOT PROVEN (files exist, no imports found)
5. ⚠️ **Truth Gate Active**: NOT PROVEN (exists but no callsite evidence)

---

## VERIFICATION COMMANDS

### To Prove Greeting Fastpath Exists:
```bash
grep -n "greeting\|fastpath\|^hi.*roxy" ~/.roxy/roxy_core.py
# Should show fastpath check before subprocess call
```

### To Prove OBS Launches:
```bash
pgrep obs  # Before
curl -d '{"command":"open obs"}' http://127.0.0.1:8766/run
sleep 2
pgrep obs  # After (should show new PID)
```

### To Prove launch_app Handler Exists:
```bash
grep -n 'cmd_type == "launch_app"' ~/.roxy/roxy_commands.py
# Should show handler implementation
```

### To Prove Cursor Modules Integrated:
```bash
grep -rn "from hybrid_search\|import hybrid_search" ~/.roxy --include="*.py" | grep -v venv
grep -rn "from llm_router\|import llm_router" ~/.roxy --include="*.py" | grep -v venv
grep -rn "from security\|import.*security" ~/.roxy/roxy_core.py
grep -rn "from feedback\|import feedback" ~/.roxy --include="*.py" | grep -v venv
```

### To Prove Truth Gate Active:
```bash
journalctl --user -u roxy-core --since "1 hour ago" | grep -i "truth.*gate\|validation"
# Should show Truth Gate validation logs
```

---

**END OF TRUTH TABLE**  
**Proof Coverage**: 46.5% proven, 53.5% unproven  
**Next Actions**: Close top 5 critical gaps (P0)
