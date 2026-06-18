"""Live log panel: a scrolling ``ui.log`` fed from a :class:`LogStream`.

Logs stream rather than snapshot, so this panel polls ``log_stream.since(cursor)``
from a per-client ``ui.timer`` and pushes only the new lines — the same side-channel
pattern as the video panel, not the bus latest-value poll.
"""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.sources.logs import LogStream


@register("logs")
class LogPanel(Panel):
    def __init__(self, bus: Bus, log_stream: LogStream, *, title: str | None = "Logs",
                 max_lines: int = 400) -> None:
        self._log_stream = log_stream
        self._cursor = 0
        self._max_lines = max_lines
        super().__init__(bus, channel="", title=title)  # logs use their own transport

    def build(self) -> None:
        self.log = ui.log(max_lines=self._max_lines).classes("w-full").style(
            "flex:1 1 auto;min-height:0;white-space:pre-wrap;word-break:break-word;"
            "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:0.78rem;"
            "background:var(--ctp-crust);color:var(--ctp-text);border-radius:0.5rem;padding:0.4rem;"
        )
        ui.timer(self.poll_interval, self._poll)

    def _poll(self) -> None:
        lines, self._cursor = self._log_stream.since(self._cursor)
        for line in lines:
            self.log.push(line)
