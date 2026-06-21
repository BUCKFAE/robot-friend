"""Tier-3 E2E: control state syncs live across simultaneous clients.

Two independent browser contexts (separate sessions, like two people) load the same
dashboard. A servo move in one must appear in the other within a poll tick. This guards
the regression the live-sync work fixed: before it, each client rendered the servo panel
once and never saw peers' moves.

Servos are the deterministic target — the demo backend always exposes two fake servos
(``pan`` ch0, ``tilt`` ch1) at 90°, with no host hardware involved. The camera/sound
selects share the same StateSync plumbing but depend on host devices, so their sync is
covered by the browser-free unit tests instead.
"""
import pytest
from playwright.sync_api import expect


def _open_client(browser, url):
    """A fresh browser context (independent session) with the dashboard loaded + painted."""
    page = browser.new_context().new_page()
    page.goto(url, wait_until="domcontentloaded")
    page.locator("[data-testid='dashboard-ready']").wait_for(state="attached", timeout=15000)
    return page


def _move_slider(page, channel, fraction):
    """Click a servo slider at ``fraction`` of its width — a committed user move (Quasar
    emits its ``change`` event on release, which is when the panel broadcasts)."""
    slider = page.locator(f"[data-testid='servo-slider-{channel}']")
    slider.scroll_into_view_if_needed()
    slider.wait_for(state="visible", timeout=10000)
    box = slider.bounding_box()
    assert box is not None, "servo slider has no layout box"
    slider.click(position={"x": box["width"] * fraction, "y": box["height"] / 2})


@pytest.mark.visual
def test_servo_moves_sync_across_clients(live_server, browser):
    alice = _open_client(browser, live_server)
    bob = _open_client(browser, live_server)

    alice_pan = alice.locator("[data-testid='servo-readout-0']")
    bob_pan = bob.locator("[data-testid='servo-readout-0']")
    expect(alice_pan).to_have_text("90°")
    expect(bob_pan).to_have_text("90°")

    # Alice moves servo 0 toward its maximum; Bob must follow within a poll tick.
    _move_slider(alice, channel=0, fraction=0.85)
    expect(alice_pan).not_to_have_text("90°", timeout=4000)
    moved_pan = alice_pan.inner_text()
    expect(bob_pan).to_have_text(moved_pan, timeout=4000)

    # And the other direction: Bob moves servo 1, Alice follows — proving it's bidirectional.
    bob_tilt = bob.locator("[data-testid='servo-readout-1']")
    alice_tilt = alice.locator("[data-testid='servo-readout-1']")
    _move_slider(bob, channel=1, fraction=0.15)
    expect(bob_tilt).not_to_have_text("90°", timeout=4000)
    moved_tilt = bob_tilt.inner_text()
    expect(alice_tilt).to_have_text(moved_tilt, timeout=4000)
