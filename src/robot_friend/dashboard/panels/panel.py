"""Panel base class + registry — the dashboard's extension point.

Subclass :class:`Panel`, set a ``channel``, implement :meth:`~Panel.build` (create
the UI elements once) and :meth:`~Panel.on_data` (update them from the latest bus
value), and decorate with :func:`register`. The base wires a per-client
``ui.timer`` that polls ``bus.latest(channel)`` and calls ``on_data`` when a value
is present. Panels whose channel is empty (e.g. video, which streams over its own
HTTP route) skip the timer.
"""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.theme import PANEL_STYLE

#: type-name -> Panel subclass. Populated by @register; the "add a panel" recipe.
PANEL_REGISTRY: dict[str, type["Panel"]] = {}


class Panel:
    #: Bus channel this panel reads (overridable per-instance via the constructor).
    channel: str = ""
    #: Per-client refresh-timer interval, in seconds.
    poll_interval: float = 0.1

    def __init__(self, bus: Bus, channel: str | None = None, *, title: str | None = None) -> None:
        self.bus = bus
        if channel is not None:
            self.channel = channel
        self.title = title
        self.card = ui.card().classes("w-full h-full").style(
            PANEL_STYLE + "display:flex;flex-direction:column;padding:0.5rem;gap:0.4rem;"
        )
        with self.card:
            if title:
                ui.label(title).classes("text-sm font-semibold").style("color:var(--ctp-subtext)")
            self.build()
        if self.channel:
            ui.timer(self.poll_interval, self._tick)

    def build(self) -> None:
        """Create the panel's UI elements once (called inside the card)."""

    def on_data(self, value) -> None:
        """Update the UI from the latest value on ``self.channel``."""

    def _tick(self) -> None:
        value = self.bus.latest(self.channel)
        if value is not None:
            self.on_data(value)


def register(type_name: str):
    """Register a Panel subclass under ``type_name`` in :data:`PANEL_REGISTRY`."""
    def decorator(cls: type[Panel]) -> type[Panel]:
        PANEL_REGISTRY[type_name] = cls
        return cls
    return decorator
