# Dashboard

A live web UI for the headless Finch robot, viewed from a dev laptop over the LAN.
Built with [NiceGUI](https://nicegui.io/): reusable panels — video (raw + annotated),
live logs, tables, last-transcript, detections and system metrics — arranged in a
draggable/resizable grid.

```sh
just dashboard                          # live data from the robot
just dashboard --demo-scenario nominal  # deterministic fake data, no hardware
```

## How it works

Data **sources** (`sources/`) publish onto named channels of a thread-safe `Bus`;
**panels** (`panels/`) subscribe to a channel and render it. Adding a panel = instantiate
a component and push to its channel — there's no wiring beyond that.

- `app.py` assembles the page and owns the process-global singletons (the `Bus` and the
  video transport); importing it registers the page and mounts the video routes.
- `main.py` chooses live sources (camera, mic, Python logging) or demo sources (fake data
  for `--demo-scenario` and the visual test suite) and starts the server.
- `static/` holds the front-end assets — the Gridstack grid and the binary-JPEG video client.

Full design (and the honest Hailo-8 telemetry limits that bound the metrics panel):
see `FinchObsidian/implementation-plans/2026-06-18-dashboard.md`.
