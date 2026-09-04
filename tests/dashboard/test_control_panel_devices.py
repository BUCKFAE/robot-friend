"""Browser-free tests that the ControlPanel renders when the devices it expects are gone.

``ui.select`` rejects an initial value that is not one of its options, so a selection the
backend reports but cannot enumerate used to raise out of the page function and turn the
whole dashboard into a 500 — the state you get in live mode whenever the robot is not
reachable, or when the selected camera has been unplugged. These build the real panel in
a standalone NiceGUI client (no server, no browser) and assert it survives.
"""
from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.client import Client
from nicegui.page import page

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.controls import ControlsBackend, DeviceOption
from robot_friend.dashboard.panels.control_panel import ControlPanel


class StubControls(ControlsBackend):
    """A backend whose device lists and selection can disagree, as a live robot's do."""

    def __init__(
        self,
        cameras: list[DeviceOption],
        sounds: list[DeviceOption],
        camera_index: int = 0,
        sound_device: int | str | None = None,
    ) -> None:
        self.cameras = cameras
        self.sounds = sounds
        self._camera_index = camera_index
        self._sound_device = sound_device

    def camera_options(self) -> list[DeviceOption]:
        return self.cameras

    def sound_options(self) -> list[DeviceOption]:
        return self.sounds

    @property
    def camera_index(self) -> int:
        return self._camera_index

    @property
    def sound_device(self) -> int | str | None:
        return self._sound_device

    def set_camera_index(self, index: int) -> None:
        self._camera_index = index

    def set_sound_device(self, device: int | str | None) -> None:
        self._sound_device = device


@pytest.fixture
def client():
    """A slot context for building elements without a server or a browser."""
    with Client(page("/test"), request=None) as client:
        yield client


def _build(controls: StubControls) -> ControlPanel:
    with ui.column():
        return ControlPanel(Bus(), controls, title=None)


def test_no_devices_at_all_renders(client):
    """Live mode with an unreachable robot: no options, but a reported selection."""
    panel = _build(StubControls(cameras=[], sounds=[], camera_index=0))
    assert panel._camera_select.value is None
    assert panel._camera_select.options == {}
    assert not panel._camera_select.enabled
    assert panel._sound_select.value is None
    assert not panel._sound_select.enabled


def test_selected_camera_missing_from_options_renders(client):
    """The selected camera was unplugged: keep the offered ones, drop the selection."""
    panel = _build(
        StubControls(
            cameras=[DeviceOption(1, "Camera 1")],
            sounds=[DeviceOption(None, "Default input")],
            camera_index=0,
        )
    )
    assert panel._camera_select.value is None
    assert panel._camera_select.options == {1: "Camera 1"}
    assert panel._camera_select.enabled
    assert panel._sound_select.value is None


def test_present_devices_keep_their_selection(client):
    panel = _build(
        StubControls(
            cameras=[DeviceOption(0, "Camera 0"), DeviceOption(2, "Camera 2")],
            sounds=[DeviceOption(3, "3: USB mic")],
            camera_index=2,
            sound_device=3,
        )
    )
    assert panel._camera_select.value == 2
    assert panel._camera_select.enabled
    assert panel._sound_select.value == 3


def test_refresh_drops_a_vanished_device(client):
    controls = StubControls(
        cameras=[DeviceOption(0, "Camera 0")],
        sounds=[DeviceOption(None, "Default input")],
        camera_index=0,
    )
    panel = _build(controls)
    assert panel._camera_select.value == 0

    controls.cameras = []
    panel._refresh_devices()
    assert panel._camera_select.options == {}
    assert panel._camera_select.value is None
    assert not panel._camera_select.enabled
