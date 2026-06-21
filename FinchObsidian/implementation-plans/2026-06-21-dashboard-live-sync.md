# Dashboard live sync — control state across simultaneous clients

## Problem
NiceGUI builds a fresh element tree per browser connection, so the dashboard is
inherently multi-client. But `ControlPanel` and `ServoPanel` were built with
`channel=""`, which means `Panel` wired them **no poll timer** (`panel.py`). They
rendered once and only re-read state on a manual "Refresh" click. So when one user moved
a servo slider (or picked a camera/mic), the backend updated but **other open dashboards
never saw it** — sliders drifted out of agreement between users.

## What needs syncing (shared, user-mutable state)
- Servo **angle** (per channel)
- Servo **mid-point calibration / trim** (per channel)
- **Camera** device selection
- **Sound input** device selection

Explicitly *not* synced: the gridstack layout (per-device in `localStorage`, intentional),
device *enumeration* (probes hardware — stays behind the "Refresh devices" button).

## The common interface
The `Bus` is already a process-global, cross-client latest-value fan-out, and `Panel`
already polls it per client. The control panels just opted out. The new piece is a small
**`StateSync`** collaborator (`dashboard/panels/state_sync.py`) — composition, not a base
class — that any panel keys to a bus channel:

- `seed(snapshot)` — adopt a starting value, publishing it only if the channel is empty
  (first client seeds; later clients inherit whatever peers changed it to).
- `publish(snapshot)` — broadcast a user change (no-op if unchanged or mid-apply).
- `receive(snapshot, apply_fn)` — apply a peer's snapshot to widgets, skipping our own
  echo, with an `applying` guard so the programmatic widget writes can't loop back.

Each panel supplies its own **typed snapshot** + apply callback:
- Servos: `ServoSnapshot(states, driver)` (`servos.py`), with pure optimistic-update
  helpers `with_angle` / `with_calibration` so a commit broadcasts instantly without a
  backend re-read.
- Controls: `ControlSelection(camera_index, sound_device)` (`controls.py`), via a concrete
  `ControlsBackend.selection()` (mirrors the new concrete `ServoBackend.snapshot()`).

Both panels now use a non-empty `channel`, so `Panel`'s existing timer delivers peers'
snapshots; commit handlers (`change` on release, `blur` for trim, `on_change` for selects)
call `set_*` on the backend **and** `publish` the new snapshot.

## Flow
1. User A releases a slider → `set_angle` (drives hardware / posts to robot) → `publish`
   an optimistic `ServoSnapshot`.
2. Every client's poll timer reads `bus.latest` → `receive` → `_apply` moves the slider +
   readout. A's own tick dedupes (snapshot == state) so there's no echo/flicker.
3. The `applying` guard + "only publish if changed" make programmatic widget writes inert,
   so there are no feedback loops.

## Tradeoff / future work
Publish-on-commit fully covers **multi-dashboard-user** sync (the request). In *live*
mode the bus snapshot is seeded once and thereafter only updated by dashboard commits, so
a **robot-initiated** change (or a non-dashboard client) isn't reflected until someone
clicks Refresh — same as before, not a regression. If live convergence with external
changes is wanted later, add a `DashboardDataSource` that periodically publishes
`backend.snapshot()` to the channel; the panels already consume it. Skipped here to avoid
continuous HTTP polling and keep the change focused.

## Tests
- Browser-free units: `test_state_sync.py` (seed/dedupe/echo/applying-guard),
  `test_servo_sync.py` (optimistic helpers + value equality), `test_controls_selection.py`.
- E2E: `visual/test_sync.py` — two independent browser contexts; a servo move in one
  appears in the other within a poll tick, both directions. Servos are the deterministic
  target (two fake servos, no host hardware); the selects share the same plumbing.
