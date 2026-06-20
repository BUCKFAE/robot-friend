# Dashboard ↔ robot: telemetry-attach architecture

**Date:** 2026-06-20
**Supersedes the integration model in** [[2026-06-18-dashboard]] (§5 assumed a single
in-process loop; this splits producer and viewer into two processes).

**Status: implemented 2026-06-20.** New: `robot_server.py` (`RobotServer`),
`telemetry/{codec,store}.py`, `utils/{jpeg,mjpeg}.py`, dashboard
`sources/telemetry_source.py` + `sources/video/robot_video_source.py`, audio
`transcribe_loop.py`. Removed: `mjpeg.py`, dashboard `CameraVideoSource` + ASR
`AudioSource`. Tests: codec/store/e2e under `tests/telemetry/`, `tests/test_robot_server.py`,
`tests/dashboard/sources/`, `tests/test_main.py` (vision-only-without-mic).

**Follow-ups done 2026-06-20:** (1) **Robot logs** — `LogStream`/handler moved to shared
`utils/log_buffer.py`; the robot captures its own logging and serves `GET /logs.json?since=N`;
new dashboard `RobotLogSource` polls it into the Logs panel (merged with the dashboard's own
connection logs). (2) **Control channel** — `RobotServer` generalized to a JSON route
registry (`on_get`/`on_post`); device enumeration moved to shared `devices.py`; the robot
holds `RobotControls` and serves `GET /devices.json` + `POST /control`, with the vision loop
re-opening the camera and the audio loop restarting the mic on change; the dashboard gains a
`ControlsBackend` ABC with `DashboardControls` (demo) + `RobotControlsClient` (live HTTP).
The robot stays a pure server — it accepts control from any client and depends on none.
All 60 tests pass (bare + `--all-extras`); the NiceGUI visual suite needs a real environment
(this sandbox blocks the `multiprocessing` semaphore NiceGUI creates at startup).

## 1. Decision

Two processes on the Pi, with the **robot as a self-contained server** and the
**dashboard as an optional viewer that attaches to it**:

- **`main` (`robot-friend`)** is the one "robot brain": it owns *all* hardware —
  camera **and** mic — runs the vision loop and an audio (ASR) loop in separate
  threads, and serves what it produces. It runs **identically whether or not the
  dashboard is up**. It contains no reference to the dashboard.
- **dashboard (`robot-friend-dashboard`)** is long-lived. It *attaches* to a running
  `main`: video over the existing MJPEG stream, lightweight metadata over a new
  JSON telemetry endpoint. It republishes onto the existing in-process `Bus`, so the
  panel/grid/UI layer is unchanged.

### Why the robot is the server (not the connector)

The hard requirement is "I can run the robot without the dashboard." Making `main`
the **server** satisfies this in the strongest possible form: `main` never connects
out, never holds the dashboard's address, never runs a reconnect loop. It just serves;
if nobody attaches, it's idle. All dashboard-awareness lives in the dashboard. You
restart `main` freely — the dashboard's attach drops and re-establishes on its own.

This reverses the "main pushes to the dashboard" sketch we first considered: pushing
would bake dashboard-awareness into the process we want to keep independent.

## 2. Architecture

```
┌─ main (robot-friend) ─ self-contained, runs with or without a viewer ─┐
│  vision thread:  camera.read → detect → annotate                       │
│  audio thread:   mic.listen → transcribe                               │
│        │ (cheap, lock-guarded writes to a latest-value store)          │
│        ▼                                                               │
│  RobotServer  (one ThreadingHTTPServer, generalizes MJPEGServer)       │
│    GET /video/raw          → MJPEG (multipart)                         │
│    GET /video/annotated    → MJPEG (multipart)                         │
│    GET /telemetry.json     → {detections, perf, transcript, ts}        │
└───────────────────────────────────────────────────────────────────────┘
            ▲ pulled on demand (serialization paid only when attached)
            │
┌─ dashboard (robot-friend-dashboard) ─ long-lived viewer ──────────────┐
│  TelemetrySource: poll /telemetry.json ~100ms                         │
│      → reconstruct DetectedObject / Transcript                        │
│      → bus.publish("detections" | "audio.transcript" | "perf.*")      │
│  video panels → <img> at http://<pi>:8081/video/{raw,annotated}       │
│  Bus + panels + grid: UNCHANGED                                       │
└───────────────────────────────────────────────────────────────────────┘
```

Pull (polling), not push: a failed GET just skips a tick, so reconnection is free and
stateless. Panel poll cadence is already 0.1s; telemetry is low-rate, so polling is
ample. (SSE/WebSocket is a later upgrade only if poll latency ever matters.)

## 3. The wire contract

`GET /telemetry.json` returns the latest snapshot:

```json
{
  "ts": 1750000000.0,
  "perf": { "fps": 23.5, "detect_ms": 41.7 },
  "detections": [ { "type": "PERSON", "box": [10,20,130,250], "confidence": 0.97 } ],
  "transcript": { "text": "hey finch", "language": "en",
                  "language_probability": 0.88, "keywords": ["YES"] }
}
```

- `to_renderable` (`dataclass.py:37`) is for *display* and is lossy for round-trips
  (enums become `{NAME: {...}}`). So define **explicit, typed wire (de)serializers**
  for the two types we send — `DetectedObject` and `Transcript` — in a new
  `telemetry/codec.py`. The dashboard reconstructs the real dataclasses and publishes
  *those* to the bus, so panels keep receiving the exact objects they do today.
- `ts` lets the dashboard show staleness / "robot not reachable" without extra state.

## 4. Bus channels (unchanged — that's the point)

| Channel | Producer today | Producer after |
|---|---|---|
| `detections` (`DETECTIONS_CHANNEL`) | dashboard's own detector thread | `TelemetrySource` (from `main`) |
| `perf.fps`, `perf.detect_ms` | dashboard's own detector thread | `TelemetrySource` (from `main`) |
| `audio.transcript` (`TRANSCRIPT_CHANNEL`) | dashboard's own ASR thread | `TelemetrySource` (from `main`) |

## 5. Component changes

| Where | Change |
|---|---|
| `mjpeg.py` `MJPEGServer` | Generalize → **`RobotServer`**: one `ThreadingHTTPServer`, route on `self.path` for two MJPEG streams (`/video/raw`, `/video/annotated`) **and** `/telemetry.json`. Holds a lock-guarded latest-store for frames + metadata. Serializing telemetry happens **in the GET handler** → zero cost when unattached. |
| `main.py` | Build the `RobotServer`; run vision loop (publish raw + annotated frames, detections, perf to the store) **and** start an audio thread. Serve regardless of `is_pi_host()` so the dashboard works in dev too (keep the local OpenCV window as a dev-only extra). |
| **new** `audio/...` shared helper | Extract the mic+ASR loop (currently duplicated in `dashboard/sources/audio.py:44` and the `robot-friend-audio` entrypoint) into one generator, e.g. `iter_transcripts(stop_event, device)`. Reused by `main`'s audio thread and `robot-friend-audio`. Per CLAUDE.md: no copy-paste. |
| **new** `telemetry/codec.py` | `detection_to_wire` / `detection_from_wire`, `transcript_to_wire` / `transcript_from_wire`. Typed, small, round-trip-safe. |
| **new** `dashboard/sources/telemetry_source.py` | `TelemetrySource(DashboardDataSource)`: daemon thread polls `http://<host>:<port>/telemetry.json`, reconstructs via the codec, `bus.publish(...)` onto the existing channels. Configurable robot host/port (default `localhost:8081`). Tolerates connection errors (skip tick; optional one-shot "robot unreachable" log; mark staleness). |
| `dashboard/main.py:16-23` `_build_sources` | Live mode returns `[TelemetrySource(...), LogSource(logs)]`. **Delete** `VideoSource`/`CameraVideoSource` detection loop and `AudioSource` ASR from the live path. Demo mode unchanged. |
| dashboard video panel / `VideoStreams` | Point raw/annotated panels at `main`'s MJPEG (`http://<pi>:8081/video/{raw,annotated}`). Decide proxy-through-dashboard vs. direct `<img>` to `:8081` (direct is simplest; browser on the laptop can reach both Pi ports). |
| `camera_video_source.py`, `sources/audio.py` (live) | Retire as dashboard data sources (their hardware loops move into `main`). Keep the demo/fake sources. |

## 6. Guarantees this delivers

- **`main` runs bare with zero dashboard overhead.** The loops only do `store.update(...)`
  (cheap dict writes under a lock). Serialization is paid by the GET handler — i.e. only
  when a viewer is attached.
- **Restart `main` freely.** The dashboard's next poll fails → panels go stale/placeholder
  → a later poll succeeds → live again. No reconnect bookkeeping.
- **Single hardware owner.** Only `main` opens the camera/mic, eliminating today's latent
  contention (running `just run` + live `just dashboard` both grabbed the camera).
- **No UI churn.** Bus contract and every panel stay as-is.
- **`just listen` still works** as a focused audio debug tool (shares the extracted helper).

## 7. Phasing

1. **Server generalization** — `MJPEGServer` → `RobotServer` with `/telemetry.json` +
   raw/annotated routes; latest-store. Unit-test the JSON route.
2. **Vision telemetry** — `main.py` feeds detections/perf/frames into the store.
   `TelemetrySource` + codec on the dashboard; switch live mode to it; point video panels
   at `main`. End-to-end: restart `main`, watch the dashboard recover.
3. **Audio fold-in** — extract `iter_transcripts`, add `main`'s audio thread, route
   transcripts through telemetry, delete the dashboard's ASR source.

## 8. Open questions / risks

- **Video panel transport:** direct `<img>`→`:8081` vs. proxy through the dashboard's
  existing `VideoStreams`. Direct is least code; proxy keeps everything on `:8080` (one
  origin) if that's preferred for remote access.
- **Telemetry rate:** detections at frame rate could be chatty; if needed, throttle the
  store-update or have the handler return the latest only (poll model already does the latter).
- **Staleness UX:** use `ts` to show a "robot offline" badge rather than silently freezing
  the last frame's metadata.
