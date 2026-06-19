# Dashboard UI — Visual & E2E Test Harness Plan

> Status: **Approved, ready to implement.** Decision date: 2026-06-17.
> Companion to [[2026-06-18-dashboard]] — that doc is *what* we build; this is *how
> we validate it renders correctly*. Self-contained so it survives a context compaction.

---

## 1. Goal

Stand up a test framework that makes it trivial to **validate the dashboard actually
renders** — before and during implementation — without any robot hardware. Two
concrete requirements (from the user):

1. **Look at screenshots** of the page fed with dummy data, across **various aspect
   ratios**, to catch text overlap / clipping / bad contrast by eye.
2. **Run automated tests** that "stuff renders correctly."

## 2. Decisions (locked)

- **Driver: Playwright for Python** (`pytest-playwright`), *not* NiceGUI's built-in
  `screen` fixture. NiceGUI's `screen` is **Selenium-based** (verified against v3.x
  source: `selenium>=4.11.2,<5`, Chrome-only; no Playwright anywhere). Playwright wins
  for *our* goals: full-page screenshots, clean per-viewport browser contexts (exact CSS
  pixels + DPR), the only maintained Python visual-regression plugin, and the most
  reliable CI install (`playwright install --with-deps chromium`). Cost: we launch the
  NiceGUI server ourselves (~20-line subprocess fixture) — which is a *feature*: it
  exercises the **real entrypoint** as it runs on the Pi, not an in-process simulation.
- **Visual scope, first build: gallery + programmatic overlap/overflow only.** No pixel-
  diff baselines yet — they churn while the UI is still moving and need OS-pinned fonts.
  Add `pytest-playwright-visual-snapshot` (the one maintained Python option, pixelmatch,
  needs py≥3.12 ✓) **later**, once layouts stabilize.
- NiceGUI's fast **`user` fixture** (no browser, Python element-tree only) is available
  as an *optional* future tier for panel-logic unit tests; not part of the first build.

## 3. Keystone: a fake-data "demo mode" in the app itself

The harness is **not** a bolt-on. Fake data is a first-class mode of the dashboard:
each `DataSource` (see [[2026-06-18-dashboard]] §4) gets a **fake sibling** that pushes
deterministic dummy data into the `Bus`; `dashboard.main` wires fakes in when
`DASHBOARD_FAKE=<scenario>` is set (CLI: `--demo[=scenario]`).

Why this is the center of gravity:
- **No hardware** — renders the full dashboard on a laptop or CI. Video panel points at
  one **fixed JPEG** (not a live stream); metrics replay a canned series; logs emit
  scripted lines; dataclass panel shows sample `DetectedObject`/`Transcript` instances.
- **Doubles as a dev tool** — `just dashboard --demo` to preview/iterate on the
  UI anytime, no robot needed. Big DX win.
- **It IS the extensibility payoff** (the project's #1 priority): *a new panel isn't
  "done" until it ships a fake source + sample data.* Add those and the panel
  **automatically** appears in the screenshot gallery and the overlap/overflow sweep.
  Test coverage scales with the component registry for free.

### Scenarios (the "dummy data you feed it")
Named datasets chosen to stress layout. Selected via `DASHBOARD_FAKE=<name>`:

| Scenario | Stresses |
|---|---|
| `nominal` | typical values — happy path |
| `stress_text` | long log lines, long sensor names, huge numbers, unicode/emoji — **the overlap/overflow stressor** |
| `empty` | just-booted, no data — panels must show placeholders, not break |
| `dense` | many panels at once — grid-layout stress |

### Viewports (the "various aspect ratios")
| Label | Size | Why |
|---|---|---|
| `fullhd` | 1920×1080 | 16:9 baseline |
| `ultrawide` | 3440×1440 | 21:9 — wide-grid stress |
| `laptop` | 1366×768 | common dev screen, short height |
| `tablet` | 768×1024 | portrait — narrow-column stress |

## 4. The two tiers

**Tier 1 — Render-correctness E2E** (`test_render.py`). *Requirement #2.* Boot app with
fakes → for each viewport: assert every panel rendered; **fail on any browser console /
page error** (catches a broken Vue/JS panel instantly); run the overflow/overlap sweep;
confirm the MJPEG `<img>` painted (`naturalWidth > 0`). Objective, fast, CI-friendly.

**Tier 2 — Screenshot gallery** (`test_gallery.py`). *Requirement #1.* Render the
**scenario × viewport** matrix and write full-page PNGs to
`tests/dashboard/visual/gallery/<scenario>__<viewport>.png`. Claude reviews them by opening
the PNGs directly (the Read tool renders images) and reporting overlaps/clipping/contrast
issues. `just gallery` regenerates the whole set.

## 5. Programmatic overlap/overflow detection (the important bit)

Eyeballing doesn't scale and pixel-diffs don't detect overlap. We query **DOM geometry**
via `page.evaluate`: (a) flag text elements where `scrollWidth > clientWidth` (overflow/
clipping); (b) check every pair of visible text boxes for rectangle intersection
(overlap), skipping legitimate parent/child nesting. Returns e.g.:
```
overflowing: [{el: 'span.metric "Temperature: 1234567…"', axis:'horizontal', scrollWidth:412, clientWidth:300}]
overlapping: [{a:'label "CPU"', b:'span "98.6°C"', overlapPx:240}]
```
→ `assert not problems`, run **per viewport**, so a label that collides only on the
laptop screen fails the build. JS detector preserved in §9.

## 6. Determinism (so screenshots are stable)
Flagged by research; all handled in the harness/app:
- `page.screenshot(..., animations="disabled")` — **Python's default is `"allow"`**
  (unlike the JS runner). Always pass it. Also inject anti-animation CSS via
  `add_style_tag`.
- **ECharts:** set `animation: false` in chart options (NiceGUI `ui.echart`) for demo
  builds — ECharts animation is a top flaky-diff source.
- **Wait on a sentinel, not `networkidle`** — NiceGUI holds a persistent websocket open,
  so `networkidle` is unreliable. App sets `data-testid="dashboard-ready"` once initial
  fake data has rendered; tests wait on that. *(App-side contract — small integration
  point.)*
- `page.evaluate("() => document.fonts.ready")` before any shot (avoids text reflow).
- **Video:** demo mode serves one fixed JPEG; wait for `img.naturalWidth > 0` then shoot.
- Mask any genuinely time-varying region with `mask=[...]` (default mask color #FF00FF).

## 7. Layout, deps, tooling, CI

**Convention (in place since 2026-06-17):** `tests/` mirrors the
`src/robot_friend/` package tree (e.g. `tests/audio/capture/test_vad_segmenter.py`).
pytest runs in `--import-mode=importlib` (set in `pyproject.toml`), so nested test
modules need no `__init__.py` and may share basenames. Dashboard tests follow suit.

```
tests/                             # mirrors src/robot_friend/ (importlib mode, no __init__.py)
  image/ · audio/ · …              # existing unit tests, one folder per src package
  dashboard/                       # mirrors src/robot_friend/dashboard/
    test_bus.py                    # browser-free unit tests for dashboard modules
    visual/                        # Playwright visual + E2E suite for the assembled app
      conftest.py        # live_server (subprocess + readiness), sized_page (viewports), helpers
      fakes.py           # Fake*Source classes + SCENARIOS   (GROWS as panels are added)
      test_render.py     # Tier 1: presence + console-errors + overflow/overlap
      test_gallery.py    # Tier 2: scenario × viewport PNGs -> gallery/
      gallery/           # output PNGs (gitignored)
```
- **Deps** — new dev group in `pyproject.toml`:
  ```toml
  [dependency-groups]
  viz-test = ["pytest-playwright", "pytest-base-url"]   # + pytest-playwright-visual-snapshot LATER
  ```
  Fake-data/demo mode itself needs **no** new runtime deps.
- **`just` (root):**
  `dashboard *args: uv run robot-friend-dashboard {{args}}` (use `--demo` for fakes),
  `gallery: uv run pytest tests/dashboard/visual/test_gallery.py -m visual`,
  `test-visual: uv run playwright install chromium && uv run pytest -m visual`.
- **Marker + default isolation:** register a `visual` marker; default `uv run pytest`
  stays browser-free via `--ignore=tests/dashboard/visual` (import-safe even when
  Playwright/browser absent). Existing unit tests (now mirrored under their src paths,
  e.g. `tests/audio/capture/`) keep running by default.
- **CI:** keep the current `python` job browser-free (it already runs `uv run pytest`).
  Add a **separate `e2e` job**: `uv sync --group viz-test` → `uv run playwright install
  --with-deps chromium` → `uv run pytest -m visual`, uploading `gallery/` + traces as
  artifacts. (If we later adopt pixel baselines, run it in `mcr.microsoft.com/playwright/
  python` for cross-OS font determinism.)

## 8. Sequencing — co-develop with the dashboard

The harness can't precede the app it tests. So, folding into [[2026-06-18-dashboard]] §8
build phases:
- **Phase 1 (skeleton + video)** also delivers the **harness shell**: `conftest.py`
  (`live_server`, `sized_page`), the `--demo` mode + first `FakeVideoSource`, the
  `dashboard-ready` sentinel, `test_render.py` (overlap/console-error sweep) and
  `test_gallery.py`. ✔ Verify: `just gallery` produces FHD/ultrawide/laptop/tablet
  PNGs of the two video tiles; Claude opens them; Tier-1 passes.
- **Every later phase** (logs, metrics, dataclasses/tables, audio) adds its `Fake*Source`
  + a `stress_text` contribution. Rule: **a panel isn't done until it has a fake source +
  shows up clean in the gallery and the overlap sweep.** (Audio: headless Chrome has no
  audio device + suspended AudioContext → assert the *UI state* the worklet drives, and
  whitelist AudioContext console warnings; don't assert real playback in CI.)

## 9. Key code sketches (load-bearing; correct Python-vs-JS gotchas baked in)

**`live_server` fixture** — launch the real entrypoint with fakes, poll until ready:
```python
# conftest.py
import socket, subprocess, sys, time, urllib.request, pytest
HOST, PORT = "127.0.0.1", 8181

def _wait_ready(url, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status < 500: return
        except Exception: time.sleep(0.25)
    raise RuntimeError(f"server {url} not ready")

@pytest.fixture(scope="session")
def live_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "robot_friend.dashboard.main", "--demo"],
        env={"DASHBOARD_HOST": HOST, "DASHBOARD_PORT": str(PORT), "DASHBOARD_FAKE": "nominal"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://{HOST}:{PORT}"
    try: _wait_ready(url); yield url
    finally:
        proc.terminate()
        try: proc.wait(10)
        except subprocess.TimeoutExpired: proc.kill()

@pytest.fixture(scope="session")
def base_url(live_server): return live_server   # pytest-base-url -> page.goto("/") resolves
```

**`sized_page`** — parametrize viewports (stash name for screenshot filename):
```python
VIEWPORTS = {"fullhd":(1920,1080), "ultrawide":(3440,1440), "laptop":(1366,768), "tablet":(768,1024)}

@pytest.fixture(params=VIEWPORTS.items(), ids=lambda kv: kv[0])
def sized_page(page, request):
    name, (w, h) = request.param
    page.set_viewport_size({"width": w, "height": h})
    request.node.viewport_name = name
    yield page
```

**Fail on front-end errors** — NOTE: in Python `msg.type`/`msg.text` are **properties**,
not methods (JS-runner trap):
```python
@pytest.fixture(autouse=True)
def fail_on_frontend_errors(page):
    errors = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e.message}"))
    yield
    assert not errors, "Front-end errors:\n" + "\n".join(errors)
```

**Overlap/overflow detector** (inject via `page.evaluate`):
```python
def find_layout_problems(page, selector="h1,h2,h3,p,span,label,.metric,[data-testid]"):
    return page.evaluate("""(selector) => {
      const vis = el => { const c=getComputedStyle(el), r=el.getBoundingClientRect();
        return c.display!=='none'&&c.visibility!=='hidden'&&parseFloat(c.opacity)>0&&
               r.width>0&&r.height>0&&el.textContent.trim().length>0; };
      const els=[...document.querySelectorAll(selector)].filter(vis);
      const name=el=>el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+' "'+el.textContent.trim().slice(0,40)+'"';
      const overflowing=[];
      for(const el of els){ const xo=el.scrollWidth-el.clientWidth>1, yo=el.scrollHeight-el.clientHeight>1;
        if(xo||yo) overflowing.push({el:name(el), axis: xo&&yo?'both':(xo?'horizontal':'vertical'),
          scrollWidth:el.scrollWidth, clientWidth:el.clientWidth}); }
      const hit=(a,b)=>!(a.right<=b.left||a.left>=b.right||a.bottom<=b.top||a.top>=b.bottom);
      const rs=els.map(el=>({el, r:el.getBoundingClientRect()})), overlapping=[];
      for(let i=0;i<rs.length;i++) for(let j=i+1;j<rs.length;j++){ const A=rs[i],B=rs[j];
        if(A.el.contains(B.el)||B.el.contains(A.el)) continue;
        if(hit(A.r,B.r)) overlapping.push({a:name(A.el), b:name(B.el)}); }
      return {overflowing, overlapping};
    }""", selector)
```

**Stable full-page screenshot helper:**
```python
KILL_ANIM = "*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;}"
def shoot(page, path):
    page.locator("[data-testid='dashboard-ready']").wait_for(state="visible")
    page.evaluate("() => document.fonts.ready")
    page.add_style_tag(content=KILL_ANIM)
    page.screenshot(path=path, full_page=True, animations="disabled")
```

## 10. References
- **NiceGUI testing** (screen=Selenium, fixtures, fake-injection seam): NiceGUI v3.x
  source `nicegui/testing/{screen,user,screen_plugin}.py`; <https://nicegui.io/documentation/section_testing>.
- **Playwright Python:** server-fixture + `base_url` <https://github.com/pytest-dev/pytest-base-url> ·
  viewport parametrization (Pamela Fox) <http://blog.pamelafox.org/2024/07/playwright-and-pytest-parametrization.html> ·
  screenshots/emulation/assertions <https://playwright.dev/python/docs/{screenshots,emulation,test-assertions}> ·
  console/pageerror fixture (alexwlchan) <https://alexwlchan.net/2026/playwright/>.
- **Visual regression (Python, deferred):** `pytest-playwright-visual-snapshot`
  <https://github.com/iloveitaly/pytest-playwright-visual-snapshot/> (pixelmatch, py≥3.12).
- **Overlap/overflow:** AABB intersection <https://time2hack.com/checking-overlap-between-elements/> ·
  overflow via scroll-vs-client <https://github.com/wojtekmaj/detect-element-overflow>.
- **ECharts animation off:** <https://github.com/apache/echarts/issues/14101>.
