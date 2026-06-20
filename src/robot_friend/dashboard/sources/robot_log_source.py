"""Dashboard source that streams the robot's logs into the Logs panel.

Polls the robot's ``GET /logs.json?since=<cursor>`` with an advancing cursor and appends
new lines to the dashboard's :class:`LogStream` — the same since/cursor contract the
``LogPanel`` already consumes, just sourced from the robot process instead of this one.
Reconnection is free: a failed poll skips a tick, and a backwards cursor (the robot
restarted, so its buffer reset) resyncs from the start.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.log_buffer import LogStream


class RobotLogSource(DashboardDataSource):
    """Polls the robot's ``/logs.json`` and appends new lines to a :class:`LogStream`."""

    channel = "logs"

    def __init__(self, log_stream: LogStream, base_url: str, *, interval: float = 0.5) -> None:
        self._log_stream = log_stream
        self._url = base_url.rstrip("/") + "/logs.json"
        self._interval = interval
        self._cursor = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._unreachable = False

    def start(self, bus: Bus) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="robot-log-source"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                with urllib.request.urlopen(
                    f"{self._url}?since={self._cursor}", timeout=2
                ) as response:
                    data = json.loads(response.read())
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                if not self._unreachable:
                    finch_logger.info("robot logs unreachable at %s (%s); retrying", self._url, exc)
                    self._unreachable = True
                continue
            self._unreachable = False
            cursor = data.get("cursor", self._cursor)
            if cursor < self._cursor:
                self._cursor = 0  # robot restarted; its buffer reset — resync next poll
                continue
            for line in data.get("lines", []):
                self._log_stream.append(line)
            self._cursor = cursor
