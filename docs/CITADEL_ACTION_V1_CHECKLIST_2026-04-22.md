# CitadelAction v1 Checklist

Last updated: 2026-04-22
Owner: Codex
Scope: ROXY action bus, macOS OperatorBar adapter, web/LifePanel compatibility

## P0 Contract

- [x] Keep one shared action envelope: `citadel-action-v1`.
- [x] Keep one canonical action endpoint: `POST /citadel/action`.
- [x] Require stable envelope fields:
  - `action_id`
  - `action_type`
  - `target_machine`
  - `requested_by`
  - `requested_from_surface`
- [x] Normalize optional envelope fields:
  - `target_scope`
  - `payload`
  - `audit_tags`
  - `requires_confirmation`
- [x] Reject malformed non-object `target_scope` and `payload`.

## P0 ROXY Router

- [x] Replace the old `501 not wired yet` placeholder in `roxy-core`.
- [x] Add a dedicated Citadel action router module so routing is testable outside `roxy_core.py`.
- [x] Route local ROXY gateway commands through the existing proxy lane.
- [x] Route local ROXY run-launch requests through the existing `/api/runs` lane.
- [x] Route Mac Studio operator actions through the existing SSH trust path to local-only endpoints on Mac.
- [x] Preserve backend response fields like:
  - `message`
  - `runId`
  - `needsConfirm`
  - `confirmToken`
- [x] Attach Citadel routing provenance to responses without destroying the legacy payload shape.

## P0 Action Coverage

- [x] `command.run`
- [x] `email.send`
- [x] `recording.start`
- [x] `recording.stop`
- [x] `mobile.alert.ack`
- [x] `repo.status` basic local fallback
- [x] `repo.push` basic local fallback
- [ ] `gitnexus.analyze`
- [ ] `gitnexus.resume`
- [ ] `device.claim`
- [ ] `device.release`
- [ ] `service.restart`
- [ ] `worker.dispatch`

## P1 macOS Native Adapter

- [x] Keep `BriefingStore` read-side preference on `GET /citadel/snapshot`.
- [x] Add a preferred write-side path to `POST /citadel/action`.
- [x] Keep fallback to legacy local operator routes only when Citadel transport is unavailable.
- [x] Route native quick-launch gateway commands through Citadel.
- [x] Route native run-launch requests through Citadel.
- [x] Route native email send through Citadel.
- [x] Route native recording start/stop through Citadel.
- [x] Route native alert acknowledgement through Citadel.
- [x] Rebuild and reinstall the live Mac menubar binary after the adapter change.

## P1 Web Compatibility

- [x] Add a Podium-side adapter so `/api/operator/*` write routes can forward into `POST /citadel/action` when Citadel is configured.
- [x] Add a one-hop bypass marker so ROXY-to-Mac Citadel callbacks execute local Podium handlers instead of looping back into Citadel.
- [x] Verify at least one live web operator write flow now traverses Citadel in practice.
- [ ] Verify same confirm-token semantics through the web surface after Citadel forwarding.

## P1 Fleet Metadata

- [x] Add `ssh_target` metadata for SSH-routable machines in the registry.
- [ ] Add explicit network reachability metadata for each machine and endpoint.
- [ ] Distinguish public bind, LAN bind, Tailscale bind, and localhost-only control endpoints.

## P2 Verification

- [x] Unit-test Citadel envelope validation.
- [x] Unit-test local gateway command routing.
- [x] Unit-test Mac Studio SSH-routed run launch routing.
- [x] Unit-test Mac Studio SSH-routed email routing.
- [ ] Live-verify `command.run` through the native macOS menubar app after rebuild.
- [ ] Live-verify `email.send` through Citadel end to end.
- [ ] Live-verify `recording.start` / `recording.stop` through Citadel end to end.
- [x] Live-verify alert acknowledgement through Citadel end to end.
- [x] Live-verify a web operator write flow through Citadel once Podium forwarding is patched.
- [x] Live-verify Mac quick-command gateway routing through Citadel with a safe `status` probe.

## Current Cutover Judgment

- Read-side kernelization is live.
- Write-side kernelization is now real on the ROXY side.
- macOS native source adapter is live in the installed menubar binary.
- Web operator forwarding is live for the patched Podium routes when `CITADEL_API_URL` is configured.
- Mac-side gateway and Podium targets now require runtime discovery instead of stale hardcoded ports or tokens.

## Next Highest-Value Follow-Up

1. Patch Podium operator write handlers to proxy into CitadelAction when `CITADEL_API_URL` is configured.
2. Rebuild/reinstall `OperatorBar` on Mac Studio and capture a live quick-launch proof.
3. Add `gitnexus.analyze` and `gitnexus.resume` to the action router so Nexus execution also flows through the shared bus.
