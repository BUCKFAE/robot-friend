"""Tier 1 — render-correctness E2E (requirement #2: "stuff renders correctly").

Boots the dashboard with nominal fake data and, for every viewport: asserts both
video tiles are present and actually painted (``naturalWidth > 0``), that no browser
console error / page error fired (a broken Vue/JS panel trips this instantly, via the
autouse ``fail_on_frontend_errors`` fixture), and that nothing overflows or overlaps.
Objective and fast — the CI gate for "did I break the layout?".
"""
import pytest


@pytest.mark.visual
def test_dashboard_renders(live_server, sized_page, find_layout_problems):
    page = sized_page
    page.goto(live_server, wait_until="domcontentloaded")

    # NiceGUI renders the element tree client-side over a websocket; the sentinel
    # only exists once that has happened.
    page.locator("[data-testid='dashboard-ready']").wait_for(state="attached", timeout=15000)

    for stream in ("raw", "annotated"):
        page.locator(f"img[data-testid='video-{stream}']").wait_for(state="visible", timeout=10000)

    # The MJPEG <img>s actually decoded a frame (not just present in the DOM).
    page.wait_for_function(
        "() => { const xs=[...document.querySelectorAll('img[data-video]')];"
        " return xs.length>0 && xs.every(i => i.naturalWidth > 0); }",
        timeout=15000,
    )

    problems = find_layout_problems(page)
    viewport = page.viewport_size
    assert not problems["overflowing"], f"overflow @ {viewport}: {problems['overflowing']}"
    assert not problems["overlapping"], f"overlap @ {viewport}: {problems['overlapping']}"
