# Dashboard Web UI — Implementation Plan

> Status: **Approved, ready to implement.** Decision date: 2026-06-17.
> Framework chosen: **NiceGUI** (single Python codebase). This document is the
> handoff spec — it is intentionally self-contained so implementation can
> continue after a context compaction.
> Testing strategy: see [[2026-06-18-dashboard-testing]] — Playwright visual + E2E harness, built
> on a fake-data `--demo` mode, co-developed starting with Phase 1.

---

## 1. Goal

A live web dashboard for the headless **Raspberry Pi 5 + Hailo-8 AI
HAT** robot ("Finch"), viewed from a dev laptop over the LAN. It must be a set of
**predefined, reusable components** (VideoPanel, LogPanel, …) arranged in a
**draggable/resizable grid**, where adding a panel = *instantiate a component +
push data to its channel from the backend*. Extensibility is the top priority.

### Target features
1. **Video** — raw + annotated (+ later cropped) live streams.
2. **Live logs** — Python `logging` and (later) Arduino serial text.
3. **Tables** — live-updating sensor/value tables.
4. **Audio** — a button to "hear what the Pi hears" (live mic).
5. **System metrics** — CPU/mem/temp + Hailo telemetry (see constraints).
6. **DTO viz** — render arbitrary `@dataclass` instances generically.

---

## 2. Why NiceGUI (build-vs-buy summary)

NiceGUI's programming model *is* the user's stated vision: predefined components,
instantiate-and-push, all in one Python codebase, built on FastAPI/Starlette
(so the underlying app is reachable via `nicegui.app` for raw routes). It matches
the repo's existing **ABC + host-aware factory + pluggable backends** style.

| Option | One Py codebase | Extend in Python | Grid | Effort | Verdict |
|---|---|---|---|---|---|
| **NiceGUI** ✅ chosen | yes | yes (+2 tiny Vue bits) | wrap Gridstack | medium | best fit |
| Foxglove / Lichtblick | feeds it | ❌ TS panels | built-in | low | strong, but external app + TS + account/offline caveat |
| Rerun | yes | ❌ Rust views | Py blueprints | low | *complement* (CV debugging); no audio/buttons/tables |
| Grafana + Prom/Loki | — | plugins | yes | low | *complement* (long-term metrics/logs) |
| FastAPI + Gridstack scratch | yes (+JS) | yes/JS | manual | high | "NiceGUI by hand" — only if we outgrow NiceGUI |

Styling & custom plots were a specific concern and are **NiceGUI strengths** (it
renders real HTML/CSS/Vue), unlike Foxglove/Rerun which impose fixed themes/panels.
Rerun/Grafana remain optional later complements.

---

## 3. Research-derived constraints (CRITICAL — these bound the scope)

### Hailo-8 telemetry (feature #5) — be honest about limits
- ✅ **Chip temperature (live):** `device.control.get_chip_temperature().ts0_temperature`
  (also `.ts1_temperature`). Confirmed working on Pi AI HAT / Hailo-8(L).
- ✅ **Inference FPS:** *measure it yourself* in the detection loop (count detect()
  calls/sec). Most reliable signal.
- 🟡 **"Utilization %":** only via `hailortcli monitor` TUI (needs `HAILO_MONITOR=1`
  in the inferring process + active scheduler). It's a scheduler/throughput figure,
  **not** a hardware core %, and **not cleanly programmatic**. Prefer FPS-vs-rated as
  the gauge; label any "utilization" honestly.
- ❌ **Hardware `nnc_utilization` / cpu/ram/dsp:** `query_performance_stats()` is
  **Hailo-10/15 only** — NOT available on Hailo-8.
- ❌ **Power (W):** no INA sensor on the AI HAT; the API opcode errors out.
- ✅ Static identity via `device.control.identify()` / `fw-control identify`
  (arch, FW ver, serial, part no.).
- **System metrics** otherwise: `psutil` (cpu_percent, virtual_memory, load) +
  `vcgencmd measure_temp` / `get_throttled` / `measure_clock` + `/sys/class/thermal/thermal_zone0/temp`.
- Refs: pyhailort source <https://raw.githubusercontent.com/hailo-ai/hailort/master/hailort/libhailort/bindings/python/platform/hailo_platform/pyhailort/pyhailort.py> ·
  Hailo forum temp/power <https://community.hailo.ai/t/how-to-measure-the-power-and-temp-of-hailo-8-m-2-async/100> ·
  utilization stats <https://community.hailo.ai/t/getting-hailo-8-device-utilization-statistics/6316>

### Audio (feature #4) — settled recipe
- Capture today: `sounddevice.InputStream`, **float32, mono, 16 kHz, 480-sample
  (30 ms) blocks**, single consumer via a `Queue` (`sound_device.py`). NOTE: it is
  **float32**, not int16.
- Stream approach (simplest viable, LAN, single listener): **raw PCM over a binary
  WebSocket → Web Audio API AudioWorklet.** Resample **server-side 16k→48k** with
  `scipy.signal.resample_poly(x, 3, 1)` (exact 3× ratio), convert float→int16 on the
  wire, ring-buffer in the worklet, gate behind a **"Listen" button** (browsers need
  a user gesture to start an `AudioContext`). Sub-100 ms on LAN.
- Do NOT use `<audio>`+chunked-HTTP for live (multi-second latency). WebRTC/aiortc
  and Opus are overkill here — keep in back pocket only if going off-LAN.
- Gotchas: browser `AudioContext` runs at 48 kHz (don't rely on forcing 16 kHz);
  int16↔float is `f = i16/32768`. Prime ~80 ms before playback to avoid underrun.
- Refs: Google ADK streaming Part 5 <https://google.github.io/adk-docs/streaming/dev-guide/part5/> ·
  16-bit PCM streaming <https://medium.com/developer-rants/streaming-audio-with-16-bit-mono-pcm-encoding-from-the-browser-and-how-to-mix-audio-while-we-are-f6a160409135>

### Serial / sensors (features #2, #3) — mostly greenfield
- Arduino emits **line-based text @ 9600 baud, Arduino→host only** (`arduino/src/main.cpp`);
  currently just LED-state messages.
- **Host side does NOT read serial at all** (no `pyserial` dep). Need `pyserial` +
  a threaded reader → log/table channels when real data exists.
- **No physical sensors wired yet.** The only "live values" today: LED state,
  audio RMS / VAD flags (`VadSegmenter.last_rms` etc.), transcript text/confidence/
  language, detection boxes. So these panels are about being *ready* — populate later.
- Roadmap (Obsidian): lidar→motor (Leon), face recognition (Julian) → future sensor panels.

### Logging (feature #2) — needs a small refactor
- Everything is bare `print(..., flush=True)`; **no `logging` setup, no central logger.**
- Add a `logging` config + a `BusLogHandler` that fans out to a log channel. Optionally
  tee `sys.stdout` to also capture existing `print()`s (or migrate prints to `logging`
  over time). Net improvement regardless of the UI.

### DTO visualization (feature #6) — trivial
- All 8 data objects are **plain `@dataclass`** (no pydantic/frozen/slots).
- Generic adapter = `dataclasses.asdict(obj)` rendered as a tree/table, **plus an
  optional per-type custom-renderer registry** (e.g. `Transcript` already has
  `as_log_line()`; respect it). Inventory: `BoundingBox`, `DetectedObjectType(Config)`,
  `DetectedObject` (image/detection.py); `Transcript`, `Language` (audio/transcript.py);
  `SpeechKeyword(Config)`, `DetectedSpeechKeyword` (audio/keywords/keyword.py);
  `VoskModel(Config)`, `WhisperModel`, `YOLOModel` (backend enums).

### Video (feature #1) — foundation exists
- `MJPEGServer` (`mjpeg.py`) already serves the annotated frame as
  `multipart/x-mixed-replace` via stdlib `http.server`, using a `threading.Condition`
  fan-out. **Generalize it to multiple named streams** (raw / annotated / cropped),
  served over NiceGUI's underlying FastAPI as `<img>` (NOT over the JSON bus).

---

## 4. Architecture

### Module layout (new self-contained package)
```
src/robot_friend/dashboard/
  __init__.py
  bus.py                # Channel fan-out — generalizes MJPEGServer's Condition pattern
  app.py                # builds the NiceGUI page, theme, wires sources -> panels
  main.py               # entrypoint: start sources + ui.run()
  theme.py              # Catppuccin palette (ui.colors + CSS vars)
  grid.py               # GridContainer: NiceGUI element wrapping Gridstack.js
  sources/
    __init__.py
    data_source.py      # DataSource ABC
    metrics.py          # psutil + vcgencmd + Hailo temp + FPS
    logs.py             # BusLogHandler(logging.Handler) + setup_logging()
    video.py            # multi-stream MJPEG (raw/annotated) + detections + fps
    audio.py            # taps the mic fan-out, resamples 16k->48k, publishes PCM
    dataclass.py        # asdict() of arbitrary dataclasses + custom-renderer registry
  panels/
    __init__.py
    panel.py            # Panel base + PANEL_REGISTRY
    video_panel.py · log_panel.py · table_panel.py
    metrics_panel.py · audio_panel.py · dataclass_panel.py
  components/           # the ONLY JavaScript, quarantined here
    gridstack.js / .vue # draggable/resizable grid wrapper
    pcm_player.js       # AudioWorklet for live mic playback
```

### Core abstractions (match the repo's ABC style)

**Bus** — thread-safe channels; sync producers publish, async panels consume.
```python
# bus.py  (generalizes MJPEGServer's threading.Condition fan-out)
import threading
from typing import Any, Callable

class Bus:
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._latest: dict[str, Any] = {}      # channel -> last value (for snapshot)
        self._subs: dict[str, list[Callable[[Any], None]]] = {}

    def publish(self, channel: str, value: Any) -> None:
        with self._cond:
            self._latest[channel] = value
            self._cond.notify_all()
        for cb in self._subs.get(channel, []):
            cb(value)

    def latest(self, channel: str) -> Any:      # panels poll this via ui.timer
        return self._latest.get(channel)
```
> Bridge note: sync producers (camera loop, sounddevice callback) call `publish()`.
> Panels read `bus.latest(channel)` from a **per-client `ui.timer`** (NiceGUI v3.0
> removed shared auto-index UI — global state lives in module scope / `app.storage.general`
> and is pushed per-client). High-rate media bypasses the bus: **video = MJPEG `<img>`**,
> **audio = dedicated binary WS → AudioWorklet**.

**DataSource ABC** — sibling to `Camera` / `ImageDetector`.
```python
# sources/data_source.py
from abc import ABC, abstractmethod
class DataSource(ABC):
    channel: str
    @abstractmethod
    def start(self, bus: "Bus") -> None: ...   # begin publishing to self.channel
```

**Panel base + registry** — the extension point.
```python
# panels/panel.py
from nicegui import ui
PANEL_REGISTRY: dict[str, type["Panel"]] = {}

class Panel:
    channel: str
    def __init__(self, bus, channel: str | None = None):
        self.bus = bus
        if channel: self.channel = channel
        with ui.card().classes('w-full h-full'):
            self.build()
        ui.timer(0.1, self._tick)              # per-client poll
    def build(self) -> None: ...               # create ui elements (override)
    def on_data(self, value) -> None: ...       # update them (override)
    def _tick(self):
        v = self.bus.latest(self.channel)
        if v is not None: self.on_data(v)

def register(type_name: str):
    def deco(cls): PANEL_REGISTRY[type_name] = cls; return cls
    return deco
```

### "Add a new panel" recipe (the whole extension story, all Python)
1. Add a `DataSource` that `bus.publish("my.channel", value)`.
2. Subclass `Panel`, set `channel = "my.channel"`, implement `build()` + `on_data()`,
   decorate with `@register("my_panel")`.
3. `grid.add(MyPanel(bus))` (or via the grid's add-panel UI).

---

## 5. Integration points (exact, non-invasive)

| Hook | Where | Change |
|---|---|---|
| Detector import **bug fix** | `image/detection_factory.py:1` | `from robot_friend.image.detector` → `...image.image_detector` (file is `image_detector.py`; current import raises `ImportError`, breaking `main.py`). |
| FPS / latency / detections | `main.py` loop around `detector.detect(frame)` | wrap with timing → `bus.publish("perf.fps", …)`, `("perf.detect_ms", …)`, `("detections", boxes)`. |
| Raw + annotated video | `main.py` (replaces single `MJPEGServer.publish`) | publish a copy of the raw frame to `video.raw` before drawing boxes, annotated to `video.annotated`. Generalize `MJPEGServer` → multi-stream. |
| Mic tap | `sound_device.py:122` (right after `self._queue.put(indata[:, 0].copy())`) | add a **guarded** fan-out (`if self._tap: self._tap.publish(block)`) — zero overhead when no listener; fixes the single-consumer limitation. |
| Logging | new `dashboard/sources/logs.py` | `BusLogHandler(logging.Handler)` + `setup_logging()`; optional stdout tee for existing prints. |

> Keep existing behavior intact when the dashboard is off (guards / opt-in). The
> dashboard server starts alongside the existing loop, host-aware like everything else.

---

## 6. Styling & plots

**Catppuccin (Mocha)** via `ui.colors` + Tailwind classes + CSS vars (`theme.py`):
```python
from nicegui import ui
def apply_catppuccin_mocha():
    ui.colors(primary='#cba6f7', secondary='#89b4fa', accent='#f5c2e7',
              dark='#1e1e2e', dark_page='#181825',
              positive='#a6e3a1', negative='#f38ba8',
              warning='#f9e2af', info='#94e2d5')
    ui.dark_mode(True)
    ui.add_css(''':root{--ctp-base:#1e1e2e;--ctp-surface0:#313244;
      --ctp-text:#cdd6f4;--ctp-mauve:#cba6f7;--ctp-red:#f38ba8;--ctp-green:#a6e3a1}
      body,.q-page{background:var(--ctp-base);color:var(--ctp-text)}''')
# panels: .classes('bg-[#313244] text-[#cdd6f4] rounded-xl shadow-lg')
```
**Plots:** `ui.echart` (Apache ECharts) is the workhorse for live metrics (efficient
incremental updates, deep styling — feed it Catppuccin colors). `ui.plotly` for
heavier static figures. **Bespoke** (lidar polar scan, audio spectrogram, etc.) =
custom Vue component in `components/` — same mechanism as the grid/audio bits, no ceiling.
Avoid `ui.pyplot`/matplotlib on the Pi (set `MATPLOTLIB=false`).

---

## 7. Dependencies & run

- **`pyproject.toml`** — new optional extra, added per-phase:
  ```toml
  [project.optional-dependencies]
  dashboard = ["nicegui", "psutil"]   # + "scipy" (Phase 5 audio), "pyserial" (future serial)
  ```
- **Entrypoint:** `robot-friend-dashboard = "robot_friend.dashboard.main:main"`.
- **justfile (root):** `just dashboard` runs `uv run robot-friend-dashboard {{args}}`.
- **justfile (`pi/`):** a dashboard recipe mirroring `run` — upload, start the
  server on a port, open the laptop browser at `http://<pi-ip>:<port>/`.
- **Pi notes:** ARM64 only; env `MATPLOTLIB=false`; use `ui.echart` (not pyplot);
  avoid SCSS (use `ui.add_css`); install into the `just setup` system-site-packages venv.
  Precedent: Zauberzeug's RoSys robotics framework runs on NiceGUI on edge hardware.

---

## 8. Build phases (each independently verifiable)

1. **Skeleton + Video** — package, `Bus`, `theme.py` (Catppuccin), `GridContainer`
   (Gridstack wrapper), NiceGUI page. Generalize `MJPEGServer` → multi-stream
   `VideoSource`; `VideoPanel` shows `video.raw` + `video.annotated` as draggable tiles.
   **Also: fix the `detection_factory.py:1` import bug.**
   ✔ Verify: open dashboard from laptop, two live video tiles in a resizable grid.
2. **Logs** — `BusLogHandler` + `setup_logging()`; `LogPanel` (`ui.log`).
   ✔ Verify: live log lines stream in.
3. **Metrics** — `MetricsSource` (psutil + vcgencmd + Hailo chip temp + detection FPS);
   `MetricsPanel` (`ui.echart`). ✔ Verify: live CPU/temp/FPS charts. (No util%/power.)
4. **Dataclasses + Tables** — `DataclassSource` + `DataclassPanel` (live `DetectedObject`/
   `Transcript`); generic `TablePanel`. ✔ Verify: arbitrary dataclass renders live.
5. **Audio** — guarded mic fan-out → `AudioSource` (resample 16k→48k) → binary WS →
   `pcm_player.js` AudioWorklet; `AudioPanel` with a "Listen" button.
   ✔ Verify: click Listen, hear the Pi's mic. (The one fiddly piece — last.)

**Future (ready by design):** serial sensor panels (once Arduino sends real data +
`pyserial`); richer sensor tables; interactive controls / commands-back (NiceGUI is
fully interactive — buttons can call backend handlers).

---

## 9. Custom JS (isolated to `components/`)
- **`gridstack.js`** — Gridstack.js (MIT, ~10 KB, vanilla-friendly) wrapper; layout
  persists via `grid.save()/load()` → JSON stored on the Pi. <https://gridstackjs.com/>
- **`pcm_player.js`** — AudioWorkletProcessor with a ring buffer (absorbs jitter,
  silence on underrun). Reference sketches preserved in §3 audio refs.

Both are well-trodden, low-risk, and the only non-Python code in the project.

---

## 10. Appendix — preserved code sketches

### Audio: Python sender (adapt to our float32 tap) + JS worklet
```python
# AudioSource: blocks arrive float32 mono @16k from the sound_device tap
from scipy.signal import resample_poly
import numpy as np
def to_wire(block_f32_16k: np.ndarray) -> bytes:
    up = resample_poly(block_f32_16k, 3, 1)            # 16k -> 48k (float)
    return np.clip(up * 32767, -32768, 32767).astype('<i2').tobytes()
# send bytes over a binary WebSocket route added to nicegui.app (FastAPI)
```
```js
// pcm_player.js — ring buffer; prime ~80ms; convert i16/32768 -> float
class PCMPlayer extends AudioWorkletProcessor {
  constructor(){ super(); this.buf=new Float32Array(48000*2); this.r=0; this.w=0; this.filled=0;
    this.port.onmessage=e=>{const c=e.data; for(let i=0;i<c.length;i++){this.buf[this.w]=c[i];
      this.w=(this.w+1)%this.buf.length; this.filled<this.buf.length?this.filled++:this.r=(this.r+1)%this.buf.length;}};}
  process(_in,out){const o=out[0][0]; if(this.filled<3840){o.fill(0);return true;}
    for(let i=0;i<o.length;i++){ if(this.filled>0){o[i]=this.buf[this.r];this.r=(this.r+1)%this.buf.length;this.filled--;} else o[i]=0; } return true; }
}
registerProcessor('pcm-player', PCMPlayer);
```

### MJPEG from a thread (don't block NiceGUI's event loop)
Camera read runs in a daemon thread writing the latest JPEG into a shared slot; an
async generator yields it as `multipart/x-mixed-replace; boundary=frame` from a
`nicegui.app` route. One producer, many `<img>` readers. (See `mjpeg.py` — already
does the Condition fan-out; generalize to named streams.)

### Metrics: Hailo temp
```python
from hailo_platform import VDevice   # apt-installed on the Pi
# temp = device.control.get_chip_temperature().ts0_temperature   # °C, live
# FPS: count detector.detect() calls per second in the loop (most reliable)
```
