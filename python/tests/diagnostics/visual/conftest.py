"""Fixtures for the diagnostics dashboard's Playwright visual + E2E suite.

Launches the real entrypoint with ``--demo-scenario`` as a subprocess, then points
Playwright at it — so the tests exercise the same code path that runs on the Pi,
not an in-process simulation.

Import-safe by design: when Playwright isn't installed (the default ``uv run pytest``
env has no browser deps) this whole directory collect-ignores itself, so a plain test
run never imports the browser fixtures. Run the suite with ``just sync-viz`` then
``just test-visual`` / ``just gallery`` (or ``uv run pytest -m visual``).
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

# Import-safety: skip collecting this directory entirely if Playwright is absent,
# rather than erroring on the browser fixtures during a browser-free `uv run pytest`.
try:
    import playwright  # noqa: F401
except ImportError:  # pragma: no cover - only hit in the browser-free env
    collect_ignore_glob = ["*"]

HOST = "127.0.0.1"
RENDER_PORT = 8181          # Tier-1 (nominal) server
GALLERY_PORT_BASE = 8190    # one port per gallery scenario (8190, 8191, …)

#: Fake-data scenarios rendered into the gallery. Mirrors SCENARIOS in the app's
#: video source; kept here so parametrization doesn't import the app package.
SCENARIOS = ["nominal", "stress_text", "empty", "dense"]

#: The "various aspect ratios" the dashboard must survive.
VIEWPORTS = {
    "fullhd": (1920, 1080),     # 16:9 baseline
    "ultrawide": (3440, 1440),  # 21:9 — wide-grid stress
    "laptop": (1366, 768),      # common dev screen, short height
    "tablet": (768, 1024),      # portrait — narrow-column stress
}

#: Inject before screenshots: collapse every animation/transition to 0s. Playwright
#: Python's screenshot default is animations="allow" (unlike the JS runner), so we
#: also pass animations="disabled" at the call site — belt and braces.
KILL_ANIM = ("*,*::before,*::after{animation-duration:0s!important;"
             "animation-delay:0s!important;transition-duration:0s!important;}")


def _wait_ready(proc: subprocess.Popen, url: str, timeout: float = 40.0) -> None:
    """Poll ``url`` until the server answers, failing fast (with its output) if the
    process dies first or never becomes ready."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if proc.poll() is not None:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            raise RuntimeError(f"diagnostics server exited early (rc={proc.returncode}):\n{out}")
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status < 500:
                    return
        except Exception:
            time.sleep(0.25)
    proc.terminate()
    out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
    raise RuntimeError(f"diagnostics server not ready at {url} within {timeout}s:\n{out}")


@contextlib.contextmanager
def _server(scenario: str, port: int):
    """Run the dashboard with fake data on ``port`` for the duration of the block."""
    env = {**os.environ, "DIAGNOSTICS_HOST": HOST, "DIAGNOSTICS_PORT": str(port)}
    # We launch the real standalone server, NOT NiceGUI's Selenium `screen` harness.
    # pytest exports PYTEST_CURRENT_TEST into our environment; if it leaks into the
    # child, NiceGUI's helpers.is_pytest() flips ui.run() into screen-test mode and
    # then crashes on the missing NICEGUI_SCREEN_TEST_PORT. Drop it so the child boots
    # as an ordinary process.
    env.pop("PYTEST_CURRENT_TEST", None)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "robot_friend.dashboard.main",
            "--demo-scenario",
            scenario,
        ],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    url = f"http://{HOST}:{port}"
    try:
        _wait_ready(proc, url)
        yield url
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(10)
        if proc.poll() is None:
            proc.kill()


@pytest.fixture(scope="session")
def live_server():
    """A single nominal-scenario server for the Tier-1 render checks."""
    with _server("nominal", RENDER_PORT) as url:
        yield url


@pytest.fixture(scope="session")
def base_url(live_server):
    """Lets pytest-playwright resolve relative ``page.goto('/')`` against the server."""
    return live_server


@pytest.fixture(scope="module", params=SCENARIOS, ids=lambda s: s)
def scenario_server(request):
    """One server per fake-data scenario, reused across the viewport matrix."""
    scenario = request.param
    port = GALLERY_PORT_BASE + SCENARIOS.index(scenario)
    with _server(scenario, port) as url:
        yield scenario, url


@pytest.fixture(params=list(VIEWPORTS.items()), ids=lambda kv: kv[0])
def sized_page(page, request):
    """The Playwright page resized to each named viewport (stashing its name)."""
    name, (width, height) = request.param
    page.set_viewport_size({"width": width, "height": height})
    request.node.viewport_name = name
    yield page


@pytest.fixture(autouse=True)
def fail_on_frontend_errors(page):
    """Fail the test on any uncaught JS exception or console error — instantly catches
    a broken Vue/JS panel. NOTE: in Playwright-Python ``msg.type``/``msg.text`` are
    PROPERTIES, not methods (a common JS-runner trap)."""
    errors: list[str] = []

    def on_console(msg):
        # Ignore resource-load failures (e.g. a 404 favicon, or a stream with no frame
        # yet): those are network/visual concerns caught elsewhere, not JS/app errors.
        # This guard targets broken panels — uncaught exceptions + genuine console.error.
        if msg.type == "error" and "Failed to load resource" not in msg.text:
            errors.append(f"console.error: {msg.text}")

    page.on("console", on_console)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc.message}"))
    yield
    assert not errors, "Front-end errors detected:\n" + "\n".join(errors)


@pytest.fixture
def find_layout_problems():
    """Returns a callable that queries DOM geometry for text overflow/clipping and
    overlapping text boxes — the checks pixel-diffs can't do. Run per viewport."""
    def _find(page, selector="h1,h2,h3,h4,p,span,label,.metric,[data-testid]"):
        return page.evaluate(
            """(selector) => {
              const vis = el => { const c=getComputedStyle(el), r=el.getBoundingClientRect();
                return c.display!=='none'&&c.visibility!=='hidden'&&parseFloat(c.opacity)>0&&
                       r.width>0&&r.height>0&&el.textContent.trim().length>0; };
              const els=[...document.querySelectorAll(selector)].filter(vis);
              const name=el=>el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+' "'+el.textContent.trim().slice(0,40)+'"';
              const overflowing=[];
              for(const el of els){ const cs=getComputedStyle(el);
                // A legitimately scrollable element (overflow auto/scroll) is not clipping — skip that axis.
                const scrollX=cs.overflowX==='auto'||cs.overflowX==='scroll';
                const scrollY=cs.overflowY==='auto'||cs.overflowY==='scroll';
                const xo=!scrollX && el.scrollWidth-el.clientWidth>1, yo=!scrollY && el.scrollHeight-el.clientHeight>1;
                if(xo||yo) overflowing.push({el:name(el), axis: xo&&yo?'both':(xo?'horizontal':'vertical'),
                  scrollWidth:el.scrollWidth, clientWidth:el.clientWidth}); }
              const hit=(a,b)=>!(a.right<=b.left||a.left>=b.right||a.bottom<=b.top||a.top>=b.bottom);
              const rs=els.map(el=>({el, r:el.getBoundingClientRect()})), overlapping=[];
              for(let i=0;i<rs.length;i++) for(let j=i+1;j<rs.length;j++){ const A=rs[i],B=rs[j];
                if(A.el.contains(B.el)||B.el.contains(A.el)) continue;
                if(hit(A.r,B.r)) overlapping.push({a:name(A.el), b:name(B.el)}); }
              return {overflowing, overlapping};
            }""",
            selector,
        )
    return _find


@pytest.fixture
def shoot():
    """Returns a callable that takes a deterministic full-page screenshot: wait for
    the readiness sentinel, give MJPEG frames a chance to paint (but don't hang on an
    intentionally-empty scenario), settle fonts, kill animations, then capture."""
    def _shoot(page, path) -> None:
        page.locator("[data-testid='dashboard-ready']").wait_for(state="attached", timeout=15000)
        with contextlib.suppress(Exception):
            page.wait_for_function(
                "() => { const xs=[...document.querySelectorAll('img[data-video]')];"
                " return xs.length===0 || xs.every(i=>i.naturalWidth>0); }",
                timeout=4000,
            )
        page.evaluate("() => document.fonts.ready")
        page.add_style_tag(content=KILL_ANIM)
        page.wait_for_timeout(150)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True, animations="disabled")
    return _shoot
