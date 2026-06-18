"""Table panel: renders the latest list of dataclasses on its channel as a table.

Generic via :func:`to_table` — any list of dataclasses flattens to columns/rows, with
nested values shown as compact JSON. Rebuilds the table only when the published list
changes (columns can differ run to run).
"""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.sources.dataclass import to_table


@register("table")
class TablePanel(Panel):
    def __init__(self, bus: Bus, channel: str, *, title: str | None = None) -> None:
        self._last = None
        super().__init__(bus, channel=channel, title=title)

    def build(self) -> None:
        self.container = ui.element("div").classes("w-full").style(
            "flex:1 1 auto;min-height:0;overflow:auto"
        )
        with self.container:
            ui.label("waiting for data…").style("color:var(--ctp-subtext)")

    def on_data(self, value) -> None:
        if value is self._last:
            return
        self._last = value
        items = list(value) if isinstance(value, (list, tuple)) else [value]
        columns, rows = to_table(items)
        self.container.clear()
        with self.container:
            if not rows:
                ui.label("(no rows)").style("color:var(--ctp-subtext)")
                return
            ui.table(
                columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in columns],
                rows=rows,
                row_key=columns[0],
            ).classes("w-full").props("dense flat").style("background:transparent;color:var(--ctp-text)")
