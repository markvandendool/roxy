# ADR-003: Real-time Collaboration for Circle of Fifths

## Status
Accepted (2025-11-15)

## Context
The Olympus Circle of Fifths now needs to support multi-user sessions so multiple operators can view and manipulate the same dial in real time. Previous work focused on parity with the Novaxe SEB tonality button but operated strictly within a single client context. The team requires a lightweight, zero-backend setup that works across multiple browser tabs and can be swapped for a dedicated realtime transport later.

## Decision
We introduce a collaboration service layer (`CircleCollaborationService`) that uses `BroadcastChannel` when available (with a `localStorage` fallback) to share state between peers on the same session id. Each client:

- Generates a stable peer id and optional display name.
- Connects to a session-specific channel (`circle-of-fifths-collab:<sessionId>`).
- Broadcasts chord-wheel state snapshots containing selection, mode, rotation, and lock state, along with a monotonically increasing version stamp.
- Emits presence heartbeats every 10 seconds so the UI can show active peers and prune stale entries.

The Zustand store now records collaboration metadata (enabled flag, session id, peer list, last version). Remote state is applied through dedicated actions to avoid infinite broadcast loops. `useTonalityButton` orchestrates the service lifecycle and ensures that local updates broadcast only when the component is not applying a remote update. The V3 widget exposes a toggle, session badge, and peer summary so operators can verify active collaborators.

## Consequences
- Collaboration works out of the box for multiple browser tabs or kiosks without introducing a dedicated backend (though the transport can be swapped later).
- Presence and state handling are encapsulated in the store + hook, so additional widgets can opt-in by selecting the same state/actions.
- Version tracking prevents oscillation between peers when simultaneous updates occur.
- Additional safeguards (auth, remote conflict resolution) are deferred until a dedicated realtime service is provisioned.


