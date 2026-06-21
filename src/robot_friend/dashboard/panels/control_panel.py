"""Dashboard controls for live hardware selection.

Camera/sound selections are shared across clients: picking a device commits it to the backend
and broadcasts it, so every other open dashboard's selects follow along (see
:class:`~robot_friend.dashboard.panels.state_sync.StateSync`). Device *enumeration* stays behind
the "Refresh devices" button — it probes hardware and is per-client, off the live-update path.
"""
from __future__ import annotations

from dataclasses import replace

from nicegui import ui

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
            self._camera_select = ui.select(
                _options(self._controls.camera_options()),
                value=self._controls.camera_index,
                label="Webcam",
                on_change=lambda e: self._commit_camera(e.value),
            ).classes("w-full").props("dense outlined")
            self._sound_select = ui.select(
                _options(self._controls.sound_options()),
                value=self._controls.sound_device,
                label="Sound input",
                on_change=lambda e: self._commit_sound(e.value),
            ).classes("w-full").props("dense outlined")
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
        if self._camera_select.value != selection.camera_index:
            self._camera_select.value = selection.camera_index
        if self._sound_select.value != selection.sound_device:
            self._sound_select.value = selection.sound_device

    def _refresh_devices(self) -> None:
        self._camera_select.options = _options(self._controls.camera_options())
        self._camera_select.update()
        self._sound_select.options = _options(self._controls.sound_options())
        self._sound_select.update()


def _options(options: list[DeviceOption]) -> dict:
    return {option.value: option.label for option in options}
