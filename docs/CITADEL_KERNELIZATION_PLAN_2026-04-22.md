# Citadel Kernelization Plan

Last updated: 2026-04-22
Owner: Codex
Scope: ROXY Mac Pro, Mac Studio, iMac Citadel worker 1, MacBook Citadel worker 2, Linux ROXY Command Center, macOS LifePanel/OperatorBar, mobile control surfaces

## Executive Truth

The current Citadel system is not one control plane with many clients. It is two partially overlapping control planes:

- `ROXY Command Center` on Linux is ROXY-native, command-first, and already consumes a unified runtime snapshot from `roxy-core` at `/ui/snapshot`.
- `OperatorBar / LifePanel` on macOS is Podium-native, briefing-first, and still depends on `operator-briefing.ts` plus separate POST and gateway endpoints for actions.

Those are both valid products, but they are not peers on one kernel yet.

If we keep growing both surfaces independently, the fleet will keep drifting into duplicated truth models, duplicated capability contracts, and duplicated auth/routing logic.

The right move is not "rewrite everything." The right move is:

1. define one Citadel kernel contract,
2. keep the native shells thin,
3. promote GitNexus and Brain Atlas into shared infrastructure,
4. unify action dispatch and operator state across every machine.

## Current Rollout Status

The first compatibility slice is now live:

- `roxy-core` exposes `GET /citadel/snapshot`, `GET /citadel/registry`, and `POST /citadel/action`
- the macOS `OperatorBar` `BriefingStore` now prefers `GET /citadel/snapshot` and only falls back to Podium briefing/websocket paths when Citadel is unavailable
- remote Citadel reachability is enabled by honoring `ROXY_HOST` on the ROXY side, with the live machine currently bound for remote access

This means Linux Command Center and macOS OperatorBar can now converge on one read packet without rewriting either native shell.

## Audit Findings

### What the Linux ROXY side already has

- `roxy-core` serves a unified runtime snapshot at `/ui/snapshot`.
- That snapshot already includes:
  - runtime/system state
  - truth metadata
  - GitNexus status
  - Brain Atlas status
  - bench status
- `ROXY Command Center` already treats this as the authoritative dashboard feed.
- Git truth is split correctly:
  - raw git for live worktree truth
  - GitNexus for code-structure truth
- Brain Atlas v0 already exists as a read-only graph layer over repos, services, machines, and runtime facts.

Relevant files:

- `/home/mark/.roxy/roxy_core.py`
- `/home/mark/.roxy/gitnexus_client.py`
- `/home/mark/.roxy/brain_atlas.py`
- `/home/mark/.roxy/apps/roxy-command-center/widgets/home_console_page.py`

### What the macOS LifePanel side already has

- `OperatorBar` is no longer a pure status mirror.
- It has read paths for:
  - operator briefing
  - live websocket updates
  - GitNexus probe state
- It has write paths for:
  - email send
  - run launch
  - recording control
  - gateway command dispatch
- It also includes a HID authority client path, which is important for multi-machine ownership.

But the macOS surface is still architecturally anchored to Podium:

- read contract: `/api/operator/briefing`
- write contract: `/api/operator/*` POSTs
- separate gateway path for command execution
- separate GitNexus local shell bridge

Relevant files:

- `/home/mark/mindsong-juke-hub/tools/operator-menubar/README.md`
- `/home/mark/mindsong-juke-hub/tools/operator-menubar/OperatorBar/OperatorBar/OperatorBarApp.swift`
- `/home/mark/mindsong-juke-hub/tools/operator-menubar/OperatorBar/OperatorBar/BriefingStore.swift`
- `/home/mark/mindsong-juke-hub/tools/operator-menubar/OperatorBar/OperatorBar/OperatorBarLayout.swift`
- `/home/mark/mindsong-juke-hub/tools/operator-menubar/OperatorBar/OperatorBar/GitNexusOperatorSupport.swift`
- `/home/mark/mindsong-juke-hub/tools/operator-menubar/OperatorBar/OperatorBar/HIDCaptureService.swift`
- `/home/mark/mindsong-juke-hub/docs/OPERATOR_WIDGETS.md`

### Structural mismatches blocking full unification

1. Different source-of-truth packet shapes
   - Linux native uses `roxy-core /ui/snapshot`
   - macOS native uses `Podium /api/operator/briefing`

2. Different action buses
   - Linux native is ROXY-command-centric
   - macOS native mixes Podium operator routes, run launch, and a separate gateway

3. Different auth assumptions
   - Podium auth and gateway auth are historically separate
   - ROXY auth is mostly localhost and service-trust based

4. Different machine model
   - current LifePanel contracts are host-local
   - current ROXY snapshot is machine-local with some remote semantics
   - Citadel fleet needs explicit machine identity and target routing

5. Different UX roles
   - Linux Command Center is an execution workstation
   - macOS LifePanel is an owner/operator rail
   - mobile should be acknowledgment, escalation, and dispatch only

### Important non-problems

- We do not need a single monolithic GUI.
- We do not need to port GTK to macOS or SwiftUI to Linux.
- We do not need to make every machine run every subsystem.
- We do need one kernel contract and one truth spine.

## Kernel Target

The fleet should converge to this model:

- `Citadel Kernel`
  - canonical machine/service/repo/runtime graph
  - canonical action dispatch API
  - canonical operator snapshot packet
  - canonical auth/identity model
  - canonical audit/event log

- `Citadel Clients`
  - Linux ROXY Command Center
  - macOS LifePanel / OperatorBar
  - web `/operator` and `ghost-protocol-lifepanel`
  - mobile surface
  - future CLI/TUI surfaces

- `Truth Substrate`
  - raw git
  - GitNexus
  - Brain Atlas
  - service health
  - orchestrator queue/run state
  - model/runtime state
  - human ownership / hardware claims

## Proposed Architecture

### 1. One shared operator packet

Define a single `CitadelSnapshot` payload that supersedes both:

- `OperatorBriefing`
- `roxy-core /ui/snapshot`

It should contain:

- `fleet`
  - machines
  - reachability
  - roles
  - active host
- `repos`
  - raw git truth
  - GitNexus truth
  - freshness
- `atlas`
  - graph status
  - node/edge counts
  - key entities
- `services`
  - health
  - latency
  - ownership
  - dependency status
- `models`
  - local/remote model inventory
  - active model
  - accelerator binding
- `orchestrator`
  - runs
  - queue
  - blocked items
  - active workers
- `operator`
  - alerts
  - next actions
  - escalation state
- `capabilities`
  - exact executable abilities by machine
- `provenance`
  - packet source
  - generated_at
  - stale_after
  - degraded reasons

Rule:

- Every surface renders from this packet.
- No surface invents its own truth shape.

### 2. One shared action API

Define one `CitadelAction` contract for all write paths:

- `command.run`
- `email.send`
- `recording.start`
- `recording.stop`
- `repo.status`
- `repo.push`
- `gitnexus.analyze`
- `gitnexus.resume`
- `worker.dispatch`
- `service.restart`
- `device.claim`
- `device.release`
- `mobile.alert.ack`

Each action must include:

- `action_id`
- `action_type`
- `target_machine`
- `target_scope`
- `requested_by`
- `requested_from_surface`
- `requires_confirmation`
- `audit_tags`

Rule:

- macOS native, Linux native, web, and mobile all post the same action envelope.
- Adapters can still translate internally, but the client contract is unified.

### 3. One fleet registry

Add a canonical machine registry with stable IDs:

- `roxy-macpro`
- `mac-studio`
- `citadel-worker-1-imac`
- `citadel-worker-2-macbook`
- `phone-primary`

Each machine record should define:

- hostname
- tailscale name
- IPs
- OS
- CPU/GPU
- repo roots
- control endpoints
- model inventory
- mounted volumes
- roles
- trust level

This belongs in Brain Atlas and should also be emitted in the shared snapshot.

### 4. One ownership and authority layer

The existing HID authority work in `HIDCaptureService.swift` is the right direction. Generalize it.

Create an `Authority Service` for:

- hardware claims
- exclusive operator control
- recording ownership
- stream ownership
- dangerous action confirmation
- maintenance windows

This prevents cross-machine fight conditions.

### 5. One audit/event spine

Every action and every significant state transition should be written into one append-only event log:

- snapshot generated
- service degraded
- repo changed
- command launched
- email sent
- recording started/stopped
- worker dispatched
- device claimed/released
- override approved

This is the operational backbone for:

- replay
- blame
- debugging
- mobile notifications
- daily briefings

### 6. One client strategy, many surfaces

Do not try to make all surfaces equally powerful.

Use role-specific shells over the same kernel:

- Linux ROXY Command Center
  - deepest execution surface
  - local heavy ops
  - model control
  - code and repo work

- macOS LifePanel
  - owner cockpit
  - alert triage
  - launch and dispatch
  - high-level oversight
  - direct GitNexus/Nexus ops

- Web `/operator`
  - shared browser surface
  - remote access
  - richer dashboards
  - onboarding and debugging

- Mobile
  - notifications
  - ack/escalate
  - quick launch
  - queue control
  - emergency stop
  - never the full workstation

## Phased Plan

### Phase 1: Contract Unification

Goal: define one kernel without breaking current surfaces

Deliverables:

- `CitadelSnapshot` schema v1
- `CitadelAction` schema v1
- machine registry schema
- capability schema
- audit event schema

Implementation:

- add a translation layer in `roxy-core` that can emit `CitadelSnapshot`
- add a translation layer in Podium that can emit the same packet shape
- do not delete existing endpoints yet

Exit criteria:

- Linux native can render from `CitadelSnapshot`
- macOS native can render from `CitadelSnapshot`
- web operator can render from `CitadelSnapshot`

### Phase 2: Kernel Service

Goal: make one service authoritative

Preferred shape:

- `citadel-kernel`
  - reads fleet state
  - composes snapshot
  - routes actions
  - writes audit log

Pragmatic starting point:

- keep `roxy-core` as the first kernel host
- expose machine-aware APIs
- let Podium consume the kernel instead of inventing parallel truth

Exit criteria:

- Podium operator briefing becomes a view over kernel data, not a separate truth compiler
- native macOS no longer depends on a distinct briefing-only contract

### Phase 3: Brain Atlas Promotion

Goal: make Atlas the fleet topology and ownership graph

Add nodes for:

- machine
- repo
- service
- endpoint
- queue
- model
- GPU
- device
- human operator
- runbook
- control surface

Add edges for:

- hosts
- controls
- indexes
- depends_on
- owns
- mirrors
- dispatches_to
- reports_to

Exit criteria:

- Atlas can answer:
  - which machine owns which service
  - where a repo is canonical vs mirrored
  - which surface can launch which action
  - where a degraded dependency actually lives

### Phase 4: GitNexus Canonicalization Across Fleet

Goal: make code-structure truth portable and consistent

Rules:

- every important repo gets a canonical repo ID
- every machine knows canonical path, mirror path, index path
- GitNexus status is emitted in one standard per-repo payload
- clients do not shell out independently unless explicitly executing operator actions

Exit criteria:

- LifePanel, Command Center, and web `/operator` all show the same repo freshness truth

### Phase 5: Cross-Surface UX Unification

Goal: make surfaces feel like one system, not one-off apps

Standardize:

- chips and severity semantics
- capability presentation
- action confirmations
- degraded-state messaging
- routing/provenance display
- machine targeting UI

Rule:

- same concepts, native presentation
- not pixel-identical cross-platform cloning

### Phase 6: Mobile Control

Goal: safe phone control without pretending a phone is a workstation

Mobile v1 should support:

- alerts inbox
- fleet health
- active runs
- queue depth
- service restart for approved services
- recording start/stop
- quick dispatch templates
- approve/reject risky actions

Mobile v1 should not support:

- raw shell
- arbitrary repo editing
- unrestricted git push
- unrestricted HID/device takeover

## Engineering Priorities

### Do now

1. Define `CitadelSnapshot` schema and adapters.
2. Define `CitadelAction` schema and adapters.
3. Add machine registry into Brain Atlas.
4. Make LifePanel capable of reading the unified packet.
5. Make `/operator` and `ghost-protocol-lifepanel` render the same packet.

### Do next

1. Centralize auth and action confirmation.
2. Move Podium operator briefing logic behind the kernel.
3. Standardize GitNexus repo identity and status.
4. Add multi-machine targeting to ROXY Command Center and LifePanel.

### Do later

1. Mobile surface.
2. Richer atlas-driven navigation.
3. durable workflows for long-running fleet jobs.
4. voice/operator delegation across machines.

## Concrete First Deliverables

### Deliverable A: `citadel_contracts.py` and shared JSON schemas

Define:

- snapshot schema
- action schema
- machine schema
- capability schema
- audit event schema

### Deliverable B: `citadel_kernel` compatibility layer in `roxy-core`

Add endpoints:

- `/citadel/snapshot`
- `/citadel/action`
- `/citadel/registry`
- `/citadel/events`

### Deliverable C: Swift adapter

Change `BriefingStore` to:

- prefer `/citadel/snapshot`
- fall back to `/api/operator/briefing` during transition

### Deliverable D: Web adapter

Change web `/operator` surfaces to:

- consume the shared packet
- stop embedding special-case briefing shape assumptions

## Decision Rules

- Git is authoritative for worktree truth.
- GitNexus is authoritative for code-structure truth.
- Brain Atlas is authoritative for fleet topology and ownership truth.
- Citadel kernel is authoritative for operator packet composition and action dispatch.
- Native shells do not invent business logic.
- Any new surface must consume the shared packet and emit the shared action envelope.

## Risks

- If we do not unify auth early, we will just centralize confusion.
- If we over-centralize execution too early, we will create a fragile single point of failure.
- If we try to make mobile too powerful, we will create an unsafe control path.
- If we keep briefing logic duplicated in Podium and ROXY, drift will continue.

## Immediate Next Step

Build `CitadelSnapshot` v1 and wire both:

- Linux `ROXY Command Center`
- macOS `OperatorBar / LifePanel`

to the same packet before adding new features.
