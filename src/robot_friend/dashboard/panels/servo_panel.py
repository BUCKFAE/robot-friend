"""Dashboard servo panel — a slider per servo with a live angle readout.

Drags update the readout live; releasing the slider commits the angle to the backend (so the
live HTTP backend posts once per move, not once per pixel). Shows the active driver name, so
it's obvious when you're driving the fake driver versus real hardware.
"""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.servos import ServoBackend, ServoState


@register("servos")
class ServoPanel(Panel):
    def __init__(
        self,
        bus: Bus,
        servos: ServoBackend,
        *,
        title: str | None = "Servos",
    ) -> None:
        self._servos = servos
        super().__init__(bus, channel="", title=title)

    def build(self) -> None:
        with ui.column().classes("w-full").style("gap:0.5rem"):
            self._rows = ui.column().classes("w-full").style("gap:0.4rem")
            self._driver_label = ui.label().classes("text-xs").style(
                "color:var(--ctp-subtext)"
            )
            ui.button("Refresh", on_click=self._render).props("flat dense no-caps")
        self._render()

    def _render(self) -> None:
        self._rows.clear()
        states = self._servos.servos()
        with self._rows:
            if not states:
                ui.label("No servos").classes("text-xs").style("color:var(--ctp-subtext)")
            for state in states:
                self._servo_row(state)
        self._driver_label.set_text(f"driver: {self._servos.driver_label()}")

    def _servo_row(self, state: ServoState) -> None:
        with ui.row().classes("w-full items-center").style("gap:0.5rem"):
            ui.label(state.label).classes("text-sm").style("width:4rem")
            readout = ui.label(f"{state.angle:.0f}°").classes("text-xs").style(
                "width:3rem;text-align:right;color:var(--ctp-subtext)"
            )
            slider = ui.slider(
                min=state.min_angle,
                max=state.max_angle,
                value=state.angle,
                step=1,
                # Live drag updates only the readout — cheap, no command sent.
                on_change=lambda e, lbl=readout: lbl.set_text(f"{e.value:.0f}°"),
            ).classes("flex-1").props("dense")
            # Quasar's `change` fires once on release: that's when we commit the angle. Read
            # the slider's synced `.value` rather than the raw event payload.
            slider.on(
                "change",
                lambda _e, ch=state.channel, sl=slider: self._servos.set_angle(
                    ch, float(sl.value)
                ),
            )
            # Mid-point trim (degrees). Committed on blur so we don't post on every keystroke.
            trim_limit = state.max_angle / 2
            trim = ui.number(
                value=state.calibration,
                min=-trim_limit,
                max=trim_limit,
                step=1,
                format="%.0f",
            ).classes("text-xs").style("width:4rem").props("dense outlined")
            trim.tooltip("mid-point calibration (°)")
            trim.on(
                "blur",
                lambda _e, ch=state.channel, n=trim: self._servos.set_calibration(
                    ch, float(n.value or 0)
                ),
            )
