"""Dashboard servo panel — a slider per servo with a live angle readout.

Drags update the readout live; releasing the slider commits the angle to the backend (so
the live HTTP backend posts once per move, not once per pixel) *and* broadcasts it, so every
other open dashboard follows along (see :class:`~robot_friend.dashboard.panels.state_sync.StateSync`).
Inbound peer moves are written back onto the sliders by :meth:`_apply`. Shows the active driver
name, so it's obvious when you're driving the fake driver versus real hardware.
"""
from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.panels.state_sync import StateSync
from robot_friend.dashboard.servos import (
    SERVOS_STATE_CHANNEL,
    ServoBackend,
    ServoSnapshot,
    ServoState,
    with_angle,
    with_calibration,
)


@dataclass
class _ServoRow:
    """The widgets for one servo row, kept so inbound snapshots can update them in place."""
    slider: ui.slider
    readout: ui.label
    trim: ui.number


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
        self._sync = StateSync(bus, SERVOS_STATE_CHANNEL)
        self._rows: dict[int, _ServoRow] = {}
        super().__init__(bus, channel=SERVOS_STATE_CHANNEL, title=title)

    def build(self) -> None:
        with ui.column().classes("w-full").style("gap:0.5rem"):
            self._rows_container = ui.column().classes("w-full").style("gap:0.4rem")
            self._driver_label = ui.label().classes("text-xs").style(
                "color:var(--ctp-subtext)"
            )
            ui.button("Refresh", on_click=self._refresh).props("flat dense no-caps")
        # Render from the shared value if a peer already established it, else seed it from
        # the backend (the first client reads hardware/HTTP once; later clients inherit it).
        latest = self.bus.latest(self.channel)
        initial = latest if latest is not None else self._servos.snapshot()
        self._sync.seed(initial)
        self._render(initial)

    def on_data(self, snapshot: ServoSnapshot) -> None:
        self._sync.receive(snapshot, self._apply)

    # --- rendering -----------------------------------------------------------
    def _refresh(self) -> None:
        """Re-pull the backend (useful in live mode) and broadcast/redraw the result."""
        snapshot = self._servos.snapshot()
        self._sync.publish(snapshot)
        self._render(snapshot)

    def _render(self, snapshot: ServoSnapshot) -> None:
        self._rows = {}
        self._rows_container.clear()
        with self._rows_container:
            if not snapshot.states:
                ui.label("No servos").classes("text-xs").style("color:var(--ctp-subtext)")
            for state in snapshot.states:
                self._rows[state.channel] = self._servo_row(state)
        self._driver_label.set_text(f"driver: {snapshot.driver}")

    def _servo_row(self, state: ServoState) -> _ServoRow:
        with ui.row().classes("w-full items-center").style("gap:0.5rem"):
            ui.label(state.label).classes("text-sm").style("width:4rem")
            readout = ui.label(f"{state.angle:.0f}°").classes("text-xs").style(
                "width:3rem;text-align:right;color:var(--ctp-subtext)"
            ).props(f"data-testid=servo-readout-{state.channel}")
            slider = ui.slider(
                min=state.min_angle,
                max=state.max_angle,
                value=state.angle,
                step=1,
                # Live drag updates only the readout — cheap, no command sent, not broadcast.
                on_change=lambda e, lbl=readout: lbl.set_text(f"{e.value:.0f}°"),
            ).classes("flex-1").props(f"dense data-testid=servo-slider-{state.channel}")
            # Quasar's `change` fires once on release: that's when we commit + broadcast.
            slider.on(
                "change",
                lambda _e, ch=state.channel, sl=slider: self._commit_angle(ch, float(sl.value)),
            )
            # Mid-point trim (degrees). Committed on blur so we don't post on every keystroke.
            trim_limit = state.max_angle / 2
            trim = ui.number(
                value=state.calibration,
                min=-trim_limit,
                max=trim_limit,
                step=1,
                format="%.0f",
            ).classes("text-xs").style("width:4rem").props(
                f"dense outlined data-testid=servo-trim-{state.channel}"
            )
            trim.tooltip("mid-point calibration (°)")
            trim.on(
                "blur",
                lambda _e, ch=state.channel, n=trim: self._commit_calibration(
                    ch, float(n.value or 0)
                ),
            )
        return _ServoRow(slider=slider, readout=readout, trim=trim)

    # --- commits (this client) -> backend + broadcast ------------------------
    def _commit_angle(self, channel: int, angle: float) -> None:
        if self._sync.applying:  # a programmatic apply, not a real user move
            return
        new = with_angle(self._sync.state, channel, angle)
        if new == self._sync.state:  # nothing changed (e.g. released without moving)
            return
        self._servos.set_angle(channel, angle)
        self._sync.publish(new)

    def _commit_calibration(self, channel: int, deviation: float) -> None:
        if self._sync.applying:
            return
        new = with_calibration(self._sync.state, channel, deviation)
        if new == self._sync.state:
            return
        self._servos.set_calibration(channel, deviation)
        self._sync.publish(new)

    # --- inbound peer snapshot -> widgets ------------------------------------
    def _apply(self, snapshot: ServoSnapshot) -> None:
        by_channel = {state.channel: state for state in snapshot.states}
        if set(by_channel) != set(self._rows):  # servo set changed: rebuild from scratch
            self._render(snapshot)
            return
        for channel, row in self._rows.items():
            state = by_channel[channel]
            if row.slider.value != state.angle:
                row.slider.value = state.angle
                row.readout.set_text(f"{state.angle:.0f}°")
            if (row.trim.value or 0) != state.calibration:
                row.trim.value = state.calibration
        self._driver_label.set_text(f"driver: {snapshot.driver}")
