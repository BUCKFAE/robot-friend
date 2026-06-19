"""Dataclass panel: renders the latest dataclass on its channel as a JSON tree.

Uses :func:`to_json` (the generic adapter), so it renders *any* dataclass — nested
types, dataclass-valued enums, custom renderers — without per-type panel code. Updates
the label text in place; only re-renders when the published object actually changes.
"""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.sources.dataclass import to_json


@register("dataclass")
class DataclassPanel(Panel):
    def __init__(self, bus: Bus, channel: str, *, title: str | None = None) -> None:
        self._last = None
        super().__init__(bus, channel=channel, title=title)

    def build(self) -> None:
        self.text = ui.label("waiting for data…").classes("w-full").style(
            "flex:1 1 auto;min-height:0;overflow:auto;white-space:pre-wrap;word-break:break-word;"
            "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:0.78rem;"
            "color:var(--ctp-text);background:var(--ctp-crust);border-radius:0.5rem;padding:0.4rem;"
        )

    def on_data(self, value) -> None:
        if value is self._last:
            return
        self._last = value
        self.text.set_text(to_json(value))
