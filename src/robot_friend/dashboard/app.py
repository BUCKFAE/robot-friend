"""Assembles the NiceGUI dashboard page and owns the process-global singletons.

NiceGUI v3 builds the page per client (the ``@ui.page`` function below runs on each
connection), so shared state — the :class:`Bus` and the :class:`VideoStreams`
transport — lives at module scope. ``main`` imports these singletons to wire data
sources into them at startup. Importing this module registers the page and mounts
the video routes; importing it is therefore a prerequisite of ``ui.run``.
"""
from __future__ import annotations

from nicegui import app as ng_app
from nicegui import ui

from robot_friend.resource_handler import get_dashboard_static_file
from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.controls import DashboardControls
from robot_friend.dashboard.servos import DashboardServos
from robot_friend.dashboard.grid import (
    GRIDSTACK_HEAD_HTML,
    GRIDSTACK_INIT_JS,
    GRIDSTACK_RESET_JS,
    GridContainer,
    mount_gridstack_static,
)
from robot_friend.dashboard.panels.control_panel import ControlPanel
from robot_friend.dashboard.panels.dataclass_panel import DataclassPanel
from robot_friend.dashboard.panels.log_panel import LogPanel
from robot_friend.dashboard.panels.servo_panel import ServoPanel
from robot_friend.dashboard.panels.table_panel import TablePanel
from robot_friend.dashboard.panels.transcript_panel import TranscriptPanel
from robot_friend.dashboard.panels.video_panel import VideoPanel
from robot_friend.dashboard.sources.dataclass import DETECTIONS_CHANNEL, TRANSCRIPT_CHANNEL
from robot_friend.dashboard.sources.logs import LogStream, setup_logging
from robot_friend.dashboard.sources.video import VIDEO_STREAM_HTML, VideoStreams
from robot_friend.dashboard.theme import apply_catppuccin_mocha

bus = Bus()
controls = DashboardControls()
servos = DashboardServos()
streams = VideoStreams()
streams.mount(ng_app)
mount_gridstack_static(ng_app)
logs = LogStream()
setup_logging(logs)
_DASHBOARD_READY_HTML = get_dashboard_static_file(
    "partials", "dashboard_ready.html"
).read_text()


@ui.page("/")
def index() -> None:
    apply_catppuccin_mocha()
    ui.add_head_html(GRIDSTACK_HEAD_HTML)       # Gridstack CSS + library
    ui.add_body_html(VIDEO_STREAM_HTML)         # binary JPEG WebSocket client for video tiles
    ui.add_body_html(GRIDSTACK_INIT_JS)         # init the draggable grid once it's rendered
    with ui.column().classes("w-full").style("min-height:100vh;padding:0.75rem;gap:0.75rem"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.button("⟲ Reset layout", on_click=lambda: ui.run_javascript(GRIDSTACK_RESET_JS)) \
                .props("flat dense no-caps").style("color:var(--ctp-subtext)")
        grid = GridContainer()
        grid.add(lambda: VideoPanel(bus, streams, "raw", title="Raw camera"), w=6, h=4, x=0, y=0, item_id="raw")
        grid.add(lambda: VideoPanel(bus, streams, "annotated", title="Annotated"), w=6, h=4, x=6, y=0, item_id="annotated")
        grid.add(lambda: ControlPanel(bus, controls, title="Controls"), w=3, h=3, x=0, y=4, item_id="controls")
        grid.add(lambda: TranscriptPanel(bus, TRANSCRIPT_CHANNEL, title="Last transcript"), w=5, h=3, x=3, y=4, item_id="transcript")
        grid.add(lambda: TablePanel(bus, DETECTIONS_CHANNEL, title="Detections"), w=4, h=3, x=8, y=4, item_id="detections")
        grid.add(lambda: LogPanel(bus, logs, title="Logs"), w=12, h=4, x=0, y=7, item_id="logs")
        grid.add(lambda: ServoPanel(bus, servos, title="Servos"), w=4, h=4, x=0, y=11, item_id="servos")
        # Readiness sentinel: the visual harness waits on this before screenshotting.
        # NiceGUI renders the element tree client-side over a websocket, so this
        # element only exists once the dashboard has actually painted.
        ui.html(_DASHBOARD_READY_HTML)
