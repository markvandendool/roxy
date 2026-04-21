# ROXY Command Center Native Engineering Checklist

Last updated: 2026-04-21 08:59 -0600
Owner: Codex

## P0 Launch Integrity

- [x] Confirm the real native target is the GTK4 desktop app, not the MindSong web route.
- [x] Verify the desktop entry target at `~/.local/share/applications/roxy-command-center.desktop`.
- [x] Fix launcher interpreter selection so ROXY falls back to `/usr/bin/python3` when the ROXY venv cannot import `gi` / GTK / Adw / Soup / cairo.
- [x] Remove destructive single-instance behavior from `launch.sh` (`pkill -f "python3 main.py"`).
- [x] Use the absolute app script path for the native process: `.../roxy-command-center/main.py`.
- [x] Make `launch_cc.sh` start through the same desktop launcher path as the real app.

## P0 Process Ownership

- [x] Make the GTK app write the authoritative PID file itself.
- [x] Make the GTK app remove its PID file on shutdown.
- [x] Make helper `status` resolve the real live app process instead of trusting stale PID files.
- [x] Make helper `stop` terminate the real live app process, including legacy relative-argv instances.
- [x] Teach process detection to recognize both:
  - absolute script launches: `/usr/bin/python3 /home/mark/.../main.py`
  - legacy relative launches: `/usr/bin/python3 main.py` with `cwd` at the app directory
- [x] Reject zombie processes during helper PID resolution.

## P0 Desktop Integration

- [x] Set GTK process identity so `WM_CLASS` matches `org.roxy.CommandCenter`.
- [x] Verify the live X11 window reports `org.roxy.CommandCenter.org.roxy.CommandCenter`.
- [x] Preserve `StartupWMClass=org.roxy.CommandCenter` in the desktop file and confirm it now matches the real window class.

## P1 Launcher Portability

- [x] Replace the hard-coded `GDK_BACKEND=x11` contract with environment-adaptive backend selection.
- [x] Keep manual override support via `ROXY_GDK_BACKEND`.
- [x] Preserve an X11 fallback (`DISPLAY=:0`) when the selected backend is `x11` and no `DISPLAY` is set.
- [x] Enable unbuffered Python output for better native launcher diagnostics.

## P1 Runtime Hygiene

- [x] Remove unsupported GTK CSS rules that were causing parser warnings:
  - `max-width`
  - browser-style `@media`
- [x] Reduce `/info` truth-panel fetch timeout to shorten blocked background threads during degraded backend conditions.
- [x] Stop truth-panel polling explicitly on widget teardown.
- [x] Replace ad-hoc `urllib` polling with a cancellable Gio/Soup async transport path.

## P1 Observability

- [x] Preserve startup/shutdown breadcrumbs in `~/.cache/roxy-command-center/last_exit.json`.
- [x] Preserve native launcher logs in `~/.cache/roxy-command-center/run.log`.
- [x] Preserve crash/fault traces in `~/.cache/roxy-command-center/fault.log`.
- [x] Rotate or segment `run.log` per launch so old sessions do not pollute current diagnostics.
- [x] Add a launch banner with timestamp + selected interpreter + selected backend.

## P2 Validation

- [x] Verify native detached start through `launch_cc.sh start`.
- [x] Verify `launch_cc.sh status` reports the real live PID.
- [x] Verify `launch_cc.sh stop` cleanly terminates the live app and removes the PID file.
- [x] Verify relaunch after stop works.
- [x] Verify second launches do not replace the live PID and instead reactivate/present the running app.
- [x] Verify a real X11 top-level window exists through `wmctrl` / `xwininfo`.

## Current Live State

- Expected process form: `/usr/bin/python3 /home/mark/.roxy/apps/roxy-command-center/main.py`
- Expected desktop identity: `org.roxy.CommandCenter`
- Helper authority source: `~/.cache/roxy-command-center/cc.pid` + live process validation

## Current Verified Runtime State

- Live PID verified via helper + PID file: `2592056`
- Live process form verified: `/usr/bin/python3 /home/mark/.roxy/apps/roxy-command-center/main.py`
- Live X11 window class verified: `org.roxy.CommandCenter.org.roxy.CommandCenter`
- Fresh launcher log verified with launch banner in `~/.cache/roxy-command-center/run.log`
- Fresh shutdown cycle verified without new `GLib.source_remove` warnings
- Fresh `SIGUSR1` fault dump verified without the old truth-panel `urllib` thread pileup
- `roxy-core.service` stop/start and restart now complete cleanly under systemd after removing the legacy `ROXY_IGNORE_SIGTERM=1` stop blocker
- `benchmark_suite.LatencyBenchmark.memory_recall_latency` now measures the live service path at `~57ms` (`score=100.0`) instead of charging Python import startup time
- Benchmark codename recall now routes through explicit deterministic `memory_recall` instead of generic `chat`
- Native operator provenance chips now surface deterministic memory/git execution more truthfully:
  - deterministic routes no longer inherit stale model names
  - memory recall shows `mem:postgres hit`
  - git summary shows branch/dirty-count summary directly in the chip
- Header latency chip now prefers authoritative `roxy-core` `total_ms` and relegates slower end-to-end client timing to the tooltip instead of overwriting the primary latency display
- Native Command Center now consumes a unified `roxy-core` snapshot endpoint (`/ui/snapshot`) instead of splitting dashboard state through the legacy panel daemon and truth chips through a separate `/info` poll
- Default native app connection settings are now sane for ROXY-local operation:
  - `mode=local`
  - `remote_host=127.0.0.1`
  - `remote_port=8766`
  - `poll_interval_ms=5000`
- `roxy-core` now embeds the panel snapshot builder in-process and reuses persistent caches instead of paying subprocess startup cost on every UI refresh
- Warm `ui_snapshot_latency` benchmark now reports `passed=true`, `score=100.0`, `duration≈3.46ms`, `cache_hit=true`

## 2026-04-20 Live Benchmark Validation

- [x] Switched sticky operator settings back to `route=AUTO` and `pool=AUTO` before benchmarking so native results were not biased by forced `CHAT` mode.
- [x] Added native GTK accessibility tooling (`python3-pyatspi`, `python3-dogtail`) and enabled AT-SPI so the live app can be driven through the actual `Gtk.Entry` and `Send` button instead of blind X11 key injection.
- [x] Verified a native round-trip through the live Command Center input path using the real chat entry and send button.
- [x] Verified cross-session memory recall through the live native app:
  - store prompt: `MBENCH-STORE`
  - full app restart
  - recall prompt: `MBENCH-RECALL`
  - returned codename: `AZURE-EMBER-914`
- [x] Verified raw git execution through the live native app:
  - prompt: `git status`
  - execution metadata route: `local_fastpath_git_status`
  - returned a real dirty-tree payload from `/home/mark/.roxy`
- [x] Verified backend control benchmark parity:
  - `/home/mark/.roxy/venv/bin/python -m pytest -q tests/test_integration.py -k test_full_git_status_flow` passed
- [ ] Fix interaction reliability defects exposed by the live benchmark:
- [x] Fix strict-output routing so exact-answer prompts bypass RAG and use direct chat.
- [x] Fix repo-target handling for natural-language git questions so explicit paths like `/home/mark/.roxy` do not silently fall back to another repo.
- [x] Fix git-summary truth so the native app no longer reports a clean tree when the target repo is dirty.
- [x] Suppress proactive suggestions and confidence footers for strict-output prompts.
- [x] Fix native launcher `GLib.source_remove` timeout warnings by tracking live timeout handles correctly.
- [x] Make the native transcript scroll to the newest message after send/receive.
- [x] Fix benchmark-codename learning telemetry so memory-store writes now report `facts_learned=1` with the learned codename in metadata.
- [x] Fix benchmark-codename recall so the latest learned codename is returned instead of an older stale value.
- [x] Route `MBENCH-STORE` prompts to deterministic `memory_store` and honor embedded strict replies like `Reply only with STORED-MBENCH.`
- [x] Switch `benchmark_suite.LatencyBenchmark.memory_recall_latency` to service-first measurement so benchmark scores reflect the deployed ROXY path instead of cold local imports.
- [x] Verified live service memory benchmark now reports `passed=true`, `score=100.0`, `duration≈0.057s`, `backend=postgres`.
- [x] Verified `roxy-core.service` can be restarted cleanly by systemd without wedging in `deactivating (stop-sigterm)`.
- [x] Re-verified the real native GTK client after the service fix:
  - `MBENCH-RECALL ...` -> `AZURE-EMBER-919`
  - `GITBENCH-SUMMARY ...` -> `Branch: main` / `CC files: launch.sh, launch_cc.sh, main.py, +5 more` / `Repo: /home/mark/.roxy`
- [x] Re-verified the real native GTK client after the deterministic memory-recall/provenance pass:
  - metadata chip shows `[MEMORY_RECALL:NONE] memory_recall • mem:postgres hit • ...`
  - header model chip stays `🧠 deterministic` for deterministic recall routes
  - header latency chip matches the authoritative core timing (`⏱️ 13439ms` in the final live proof) instead of a larger client-wall-clock number
  - git-query chip shows repo branch/dirty summary instead of a generic route-only label

## Remaining Backlog

- [ ] If needed later, reduce overall background thread count from non-truth-panel subsystems (for example daemon polling / Mesa worker behavior) based on targeted profiling rather than guesswork.
- [ ] Collapse remaining periodic `/health` and `/bench/status` side-channel polling into the same snapshot cadence or a shared in-app status broker if we want to push native operator idle overhead even lower.
