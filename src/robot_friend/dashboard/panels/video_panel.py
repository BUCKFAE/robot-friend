"""Live video panel: a plain ``<img>`` fed by a named binary JPEG WebSocket.

The browser receives complete JPEG frames over a WebSocket and swaps them after
decode, so the UI gets live video without repeated HTTP image reloads. A snapshot
URL provides the initial paint/fallback. ``object-fit: contain`` shows the whole
frame, letterboxed on the dark backdrop; frames bypass the JSON bus.
"""
from __future__ import annotations

from html import escape

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.sources.video import VideoStreams
from robot_friend.resource_handler import get_dashboard_static_file

_VIDEO_IMG_TEMPLATE = get_dashboard_static_file(
    "partials", "video_img.html"
).read_text()


@register("video")
class VideoPanel(Panel):
    def __init__(self, bus: Bus, streams: VideoStreams, stream: str, *, title: str | None = None) -> None:
        self._streams = streams
        self._stream = stream
        super().__init__(bus, channel="", title=title)  # image bypasses the bus

    def build(self) -> None:
        snap = self._streams.snapshot_url(self._stream)
        ws = self._streams.websocket_url(self._stream)
        ui.html(
            _VIDEO_IMG_TEMPLATE.format(
                snap=escape(snap, quote=True),
                ws=escape(ws, quote=True),
                stream=escape(self._stream, quote=True),
            )
        ).classes("w-full").style("flex:1 1 auto;min-height:0")
