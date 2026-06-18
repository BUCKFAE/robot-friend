"""Dashboard controls for live hardware selection."""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.controls import DashboardControls, DeviceOption
from robot_friend.dashboard.panels.panel import Panel, register


@register("controls")
class ControlPanel(Panel):
    def __init__(
        self,
        bus: Bus,
        controls: DashboardControls,
        *,
        title: str | None = "Controls",
    ) -> None:
        self._controls = controls
        super().__init__(bus, channel="", title=title)

    def build(self) -> None:
        with ui.column().classes("w-full").style("gap:0.5rem"):
            self._camera_select = ui.select(
                _options(self._controls.camera_options()),
                value=self._controls.camera_index,
                label="Webcam",
                on_change=lambda e: self._controls.set_camera_index(e.value),
            ).classes("w-full").props("dense outlined")
            self._sound_select = ui.select(
                _options(self._controls.sound_options()),
                value=self._controls.sound_device,
                label="Sound input",
                on_change=lambda e: self._controls.set_sound_device(e.value),
            ).classes("w-full").props("dense outlined")
            ui.button("Refresh devices", on_click=self._refresh_devices).props(
                "flat dense no-caps"
            )

    def _refresh_devices(self) -> None:
        self._camera_select.options = _options(self._controls.camera_options())
        self._camera_select.update()
        self._sound_select.options = _options(self._controls.sound_options())
        self._sound_select.update()


def _options(options: list[DeviceOption]) -> dict:
    return {option.value: option.label for option in options}
