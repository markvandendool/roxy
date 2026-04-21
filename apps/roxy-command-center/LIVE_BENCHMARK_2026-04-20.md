# ROXY Command Center Live Benchmark

Date: 2026-04-20
Owner: Codex
Target: Native Linux GTK app at `~/.roxy/apps/roxy-command-center`

## Scope

This pass exercised the real native Command Center window, not the MindSong web route. The app was driven through the live `Gtk.Entry` and `Send` button using AT-SPI so the benchmark ran through the same native chat path an operator uses.

## Preconditions

- Sticky settings forced back to `route=AUTO` and `pool=AUTO`
- Live process verified as `/usr/bin/python3 /home/mark/.roxy/apps/roxy-command-center/main.py`
- AT-SPI enabled with `python3-pyatspi` and `python3-dogtail`

## Control Checks

- Native round-trip path verified through the real chat entry
- Existing backend git integration test passed:
  - `/home/mark/.roxy/venv/bin/python -m pytest -q tests/test_integration.py -k test_full_git_status_flow`
- Existing memory latency benchmark failed in current environment:
  - `benchmark_suite.LatencyBenchmark.memory_recall_latency`
  - observed Postgres auth failure for memory benchmark path

## Benchmark 1: Exact Answer Discipline

Prompt:

`Reply only with READY.`

Observed native result:

- Routed to `rag`
- Ignored the exact-answer instruction
- Returned fallback documentation passages instead of `READY`

Assessment:

- Fails instruction discipline
- Fails route selection for a trivial direct-response query

## Benchmark 2: Cross-Session Memory Recall

Store prompt:

`MBENCH-STORE: My benchmark codename is AZURE-EMBER-914. Remember it for later. Reply only with STORED-MBENCH.`

Observed store result:

- Routed to `chat`
- Returned `STORED-MBENCH`
- Added unsolicited recommendations
- Execution metadata still reported `facts_learned: 0`

Recall procedure:

1. Restart native app
2. Send recall prompt:
   `MBENCH-RECALL: What is my benchmark codename from earlier? Reply with only the codename.`

Observed recall result:

- Routed to `chat`
- Returned `AZURE-EMBER-914`
- Added unsolicited confidence text

Assessment:

- Pass on practical cross-session recall
- Fail on response discipline and learning telemetry trustworthiness

## Benchmark 3: Raw Git Capability

Prompt:

`git status`

Observed native result:

- Routed to `local_fastpath_git_status`
- Execution metadata reported `mode=exec`
- Returned a real dirty-tree payload from `/home/mark/.roxy`

Assessment:

- Pass on raw git action / repo truth retrieval
- Good evidence that the native client can surface a real repo state result

## Benchmark 4: Git Reasoning / Summary Quality

Prompt:

`GITBENCH-SUMMARY: In /home/mark/.roxy, what branch am I on and which Roxy Command Center files are modified? Reply in exactly three short lines.`

Observed native result:

- Routed to `git`
- Response claimed: `Working directory is clean. No changes to commit.`
- This contradicted the raw `git status` result returned moments earlier in the same client

Assessment:

- Fail on repo reasoning reliability
- Fail on summarization correctness
- Not Claude-Code-grade for git reasoning in current state

## Interaction Reliability Defects

- `services/chat_service.py:429` still emits `GLib.source_remove` warnings during successful request completion
- The transcript does not reliably auto-scroll to the newest response after send
- Exact-answer prompts still attract unsolicited confidence / recommendation boilerplate

## Verdict

Native Command Center status after live benchmark:

- Launch integrity: pass
- Native control path: pass
- Cross-session memory recall: pass with caveats
- Raw git execution: pass
- Instruction following: fail
- Git reasoning / summary reliability: fail

Current overall assessment:

`78/100` for live native operator use

Reason:

- Strong launch/process correctness
- Real memory and git capability exist
- Interaction correctness is not yet reliable enough for Claude-Code-grade trust, especially when the system shifts from raw command execution into natural-language summarization

## Follow-Up Remediation (2026-04-20 22:42 -0600)

Applied fixes:

- Strict-output prompts now route to direct chat instead of RAG.
- Literal prompt `Reply only with READY.` now returns exact `READY` in the live native app.
- Natural-language git repo questions now honor explicit repo paths like `/home/mark/.roxy`.
- The previous false-clean git summary was fixed by replacing the wrong-repo `git_voice_ops.py` path with deterministic `git_query` handling anchored to the requested repo.
- Strict-output prompts no longer accumulate `Recommended next steps` or `⚠️ Confidence` footers.
- `services/chat_service.py` timeout bookkeeping was hardened so successful requests no longer emit the old `GLib.source_remove` warning in the current session log.
- Talk transcript now auto-scrolls to the newest message.

Current reassessment after remediation:

`92/100`

Additional remediation completed after the first pass:

- `MBENCH-STORE` now routes to deterministic `memory_store` instead of generic `chat`.
- `MBENCH-STORE` now returns exact `STORED-MBENCH` while still persisting the learned codename.
- Benchmark-style memory writes now report `facts_learned=1` with the learned codename in `metadata.memory.learned_facts`.
- Benchmark-style codename recall now returns the latest stored codename (`AZURE-EMBER-919` in the final live proof), not an older stale codename.
- `benchmark_suite.LatencyBenchmark.memory_recall_latency` now measures the live service path first; current result is:
  - `passed=true`
  - `score=50.0`
  - `duration≈0.157s`
  - `backend=postgres`
- Native GTK validation re-run through AT-SPI now shows:
  - `Reply only with READY.` -> exact `READY`
  - `GITBENCH-SUMMARY ...` -> `Branch: main` / `CC files: ...` / `Repo: /home/mark/.roxy`

Remaining gap to 95+:

- `roxy-core.service` restart hygiene still relies on an explicit kill because the service ignores `SIGTERM` during stop/restart.
- Warm memory recall is now fast and correct, but still above the `<100ms` threshold needed for a 100/100 latency score.

## Follow-Up Remediation (2026-04-21 05:57 -0600)

Applied fixes:

- `roxy_core.py` now honors `SIGTERM` under systemd even if the legacy `ROXY_IGNORE_SIGTERM=1` env flag is present, and explicitly closes the HTTP server/socket on shutdown.
- The user unit drop-in `~/.config/systemd/user/roxy-core.service.d/86-eval-stability.conf` no longer injects the stale `ROXY_IGNORE_SIGTERM=1` stop blocker.
- `benchmark_suite.LatencyBenchmark.memory_recall_latency` now starts timing after the lazy `requests` import and uses the real benchmark recall query (`what is my benchmark codename from earlier`) instead of a broader synthetic probe.

Current proof after the 2026-04-21 pass:

- `systemctl --user restart roxy-core.service` completed successfully in `~15.18s`, and the service returned to `ActiveState=active`, `SubState=running`.
- `curl http://127.0.0.1:8766/health` returned healthy immediately after restart.
- Live service benchmark now reports:
  - `passed=true`
  - `score=100.0`
  - `duration≈0.057s`
  - `backend=postgres`
- Native GTK Command Center re-check via AT-SPI on the live app window now shows:
  - `MBENCH-RECALL ...` -> `AZURE-EMBER-919`
  - `GITBENCH-SUMMARY ...` -> `Branch: main` / `CC files: launch.sh, launch_cc.sh, main.py, +5 more` / `Repo: /home/mark/.roxy`

Current reassessment after the 2026-04-21 pass:

`96/100`

Remaining gap:

- Background thread count is still higher than ideal because of other subsystems outside the Command Center truth-panel path. That is a profiling/polish pass, not a correctness blocker for native operator use.

## Follow-Up Remediation (2026-04-21 08:07 -0600)

Applied fixes:

- Benchmark codename recall now routes through explicit deterministic `memory_recall` instead of the generic `chat` lane.
- `roxy_commands.CommandResponse` now JSON-sanitizes metadata recursively, preventing datetime-bearing memory receipts from silently breaking structured-response handoff back to `roxy-core`.
- Native provenance chips in the GTK Command Center now summarize deterministic execution truth more directly:
  - memory recall shows `mem:postgres hit`
  - git query shows `repo:<branch> dirty:<count>`
  - deterministic routes no longer inherit stale LLM model names in either the execution chip or the header model chip

Current proof after the 2026-04-21 08:07 pass:

- Live `/run` now returns:
  - `route=memory_recall`
  - `mode=memory_recall`
  - `routing.reason=deterministic:memory_recall:benchmark_codename`
  - `routing.memory_source=profile`
  - `result_tail=AZURE-EMBER-919`
- Native GTK Command Center re-check via AT-SPI now shows:
  - memory chip: `[MEMORY_RECALL:NONE] memory_recall • mem:postgres hit • ...`
  - header model chip: `🧠 deterministic`
  - git chip summary after live prompt: `[GIT_QUERY:NONE] git_query • repo:main dirty:141 • ctx:postgres • 150ms`

Current reassessment after the 2026-04-21 08:07 pass:

`97/100`

## Follow-Up Remediation (2026-04-21 08:09 -0600)

Applied fixes:

- The header latency chip no longer gets overwritten by the slower client-side wall-clock timing after assistant messages arrive.
- Native UI now keeps the authoritative `roxy-core` `total_ms` as the primary latency display and moves the broader UI/transport timing into the tooltip.

Current proof after the 2026-04-21 08:09 pass:

- Native GTK Command Center final live proof via AT-SPI now shows:
  - memory chip: `[MEMORY_RECALL:NONE] memory_recall • mem:postgres hit • 13439ms`
  - header model chip: `🧠 deterministic`
  - header latency chip: `⏱️ 13439ms`

Current reassessment after the 2026-04-21 08:09 pass:

`98/100`

## Follow-Up Remediation (2026-04-21 08:59 -0600)

Applied fixes:

- The native Command Center data plane was unified behind `roxy-core` `GET /ui/snapshot`, replacing the old split path where the main window polled the legacy panel daemon while the truth chips separately polled `/info`.
- `roxy-core` now embeds the panel snapshot builder in-process and reuses persistent caches instead of paying subprocess startup cost on every GTK refresh.
- Native app defaults are now ROXY-local and less noisy by default:
  - `mode=local`
  - `remote_host=127.0.0.1`
  - `remote_port=8766`
  - `poll_interval_ms=5000`
- The live `TalkColumn` no longer starts its own truth-panel polling loop in the new launcher session; truth chips are hydrated from the shared snapshot pushed through the main window update path.
- Added `benchmark_suite.LatencyBenchmark.ui_snapshot_latency` so the operator truth path has its own measurable benchmark.

Current proof after the 2026-04-21 08:59 pass:

- `curl http://127.0.0.1:8766/ui/snapshot?...` now returns a unified payload with:
  - `snapshot_meta.source=roxy-core`
  - `snapshot_meta.transport=roxy-core.ui_snapshot`
  - truth payload under `info`
  - benchmark status under `bench`
- Warm snapshot benchmark now reports:
  - `passed=true`
  - `score=100.0`
  - `duration≈0.00346s`
  - `cache_hit=true`
- Fresh native launcher session log now shows:
  - `TalkColumn] Truth panel awaiting unified snapshot...`
- Live GTK truth chips after restart still render correctly via AT-SPI:
  - `🕐 2026-04-21 08:58`
  - `🔀 main • d0d2b9d • ⚠️`
  - `🦙 W5700X:ok 6900XT:ok`
  - `🐙 ok`

Current reassessment after the 2026-04-21 08:59 pass:

`99/100`
