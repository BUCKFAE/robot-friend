"""Dashboard controls for live hardware selection.

Camera/sound selections are shared across clients: picking a device commits it to the backend
and broadcasts it, so every other open dashboard's selects follow along (see
:class:`~robot_friend.dashboard.panels.state_sync.StateSync`). Device *enumeration* stays behind
the "Refresh devices" button — it probes hardware and is per-client, off the live-update path.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.controls import (
    CONTROLS_STATE_CHANNEL,
    ControlSelection,
    ControlsBackend,
    DeviceOption,
)
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.panels.state_sync import StateSync


@register("controls")
class ControlPanel(Panel):
    def __init__(
        self,
        bus: Bus,
        controls: ControlsBackend,
        *,
        title: str | None = "Controls",
    ) -> None:
        self._controls = controls
        self._sync = StateSync(bus, CONTROLS_STATE_CHANNEL)
        super().__init__(bus, channel=CONTROLS_STATE_CHANNEL, title=title)

    def build(self) -> None:
        with ui.column().classes("w-full").style("gap:0.5rem"):
            self._camera_select = _device_select(
                "Webcam",
                self._controls.camera_options(),
                self._controls.camera_index,
                lambda e: self._commit_camera(e.value),
            )
            self._sound_select = _device_select(
                "Sound input",
                self._controls.sound_options(),
                self._controls.sound_device,
                lambda e: self._commit_sound(e.value),
            )
            ui.button("Refresh devices", on_click=self._refresh_devices).props(
                "flat dense no-caps"
            )
        # Inherit a peer's selection if one exists, else seed from the backend.
        latest = self.bus.latest(self.channel)
        initial = latest if latest is not None else self._controls.selection()
        self._sync.seed(initial)
        self._apply(initial)

    def on_data(self, selection: ControlSelection) -> None:
        self._sync.receive(selection, self._apply)

    # --- commits (this client) -> backend + broadcast ------------------------
    def _commit_camera(self, index: int) -> None:
        if self._sync.applying:  # a programmatic apply, not a real user pick
            return
        new = replace(self._sync.state, camera_index=index)
        if new == self._sync.state:
            return
        self._controls.set_camera_index(index)
        self._sync.publish(new)

    def _commit_sound(self, device: int | str | None) -> None:
        if self._sync.applying:
            return
        new = replace(self._sync.state, sound_device=device)
        if new == self._sync.state:
            return
        self._controls.set_sound_device(device)
        self._sync.publish(new)

    # --- inbound peer selection -> widgets -----------------------------------
    def _apply(self, selection: ControlSelection) -> None:
        _apply_value(self._camera_select, selection.camera_index)
        _apply_value(self._sound_select, selection.sound_device)

    def _refresh_devices(self) -> None:
        _set_options(self._camera_select, self._controls.camera_options())
        _set_options(self._sound_select, self._controls.sound_options())


def _device_select(
    label: str,
    options: list[DeviceOption],
    selected: Any,
    on_change: Callable[[ValueChangeEventArguments], None],
) -> ui.select:
    """Build a device select that tolerates the device not being there.

    ``ui.select`` raises on an initial value that is not one of its options, and that
    would abort the whole page render. Absent devices are a normal state: live mode seeds
    the selects from the robot's selection, so an unreachable robot enumerates nothing
    while still reporting a selected camera index, and a device can disappear between two
    page loads. Either way the panel renders with an empty, disabled select that the
    "Refresh devices" button can repopulate.
    """
    choices = _options(options)
    select = (
        ui.select(
            choices,
            value=selected if selected in choices else None,
            label=label,
            on_change=on_change,
        )
        .classes("w-full")
        .props("dense outlined")
    )
    select.set_enabled(bool(choices))
    return select


def _set_options(select: ui.select, options: list[DeviceOption]) -> None:
    """Re-enumerate ``select``: ``set_options`` drops a selection that is no longer
    offered, so an unplugged device clears instead of sticking around as a phantom."""
    select.set_options(_options(options))
    select.set_enabled(bool(select.options))


def _apply_value(select: ui.select, value: Any) -> None:
    """Mirror a peer's selection onto ``select``, skipping a device it does not offer."""
    if select.value != value and value in select.options:
        select.value = value


def _options(options: list[DeviceOption]) -> dict:
    return {option.value: option.label for option in options}
