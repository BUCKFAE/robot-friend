"""Dashboard source that attaches to the robot's telemetry endpoint.

Polls ``GET /telemetry.json`` on the running ``robot_friend.main`` process, reconstructs
the domain dataclasses via :mod:`robot_friend.telemetry.codec`, and republishes them
onto the Bus channels the panels already read. Polling makes reconnection free: a failed
request just skips a tick (panels keep their last value / show a placeholder) and the
next success resumes — so the dashboard tolerates the robot restarting with no handshake.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Any

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.dashboard.sources.dataclass import DETECTIONS_CHANNEL, TRANSCRIPT_CHANNEL
from robot_friend.telemetry.codec import detection_from_wire, transcript_from_wire
from robot_friend.utils.finch_logger import finch_logger

PERF_FPS_CHANNEL = "perf.fps"
PERF_DETECT_MS_CHANNEL = "perf.detect_ms"


def apply_telemetry(bus: Bus, data: dict[str, Any]) -> None:
    """Publish one decoded telemetry snapshot onto the dashboard bus channels.

    Pure (no I/O) so the parsing contract can be unit-tested without a live robot.
    """
    perf = data.get("perf") or {}
    if "fps" in perf:
        bus.publish(PERF_FPS_CHANNEL, perf["fps"])
    if "detect_ms" in perf:
        bus.publish(PERF_DETECT_MS_CHANNEL, perf["detect_ms"])
    detections = data.get("detections")
    if detections is not None:
        bus.publish(DETECTIONS_CHANNEL, [detection_from_wire(d) for d in detections])
    transcript = data.get("transcript")
    if transcript:
        bus.publish(TRANSCRIPT_CHANNEL, transcript_from_wire(transcript))


class TelemetrySource(DashboardDataSource):
    """Polls the robot's ``/telemetry.json`` and fans it out onto the Bus."""

    channel = DETECTIONS_CHANNEL  # nominal; it actually feeds several channels

    def __init__(self, base_url: str, *, interval: float = 0.1) -> None:
        self._url = base_url.rstrip("/") + "/telemetry.json"
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._unreachable = False

    def start(self, bus: Bus) -> None:
        self._thread = threading.Thread(
            target=self._run, args=(bus,), daemon=True, name="telemetry-source"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self, bus: Bus) -> None:
        while not self._stop.wait(self._interval):
            try:
                with urllib.request.urlopen(self._url, timeout=2) as response:
                    data = json.loads(response.read())
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                if not self._unreachable:
                    finch_logger.info(
                        "robot telemetry unreachable at %s (%s); retrying", self._url, exc
                    )
                    self._unreachable = True
                continue
            if self._unreachable:
                finch_logger.info("robot telemetry reconnected at %s", self._url)
                self._unreachable = False
            apply_telemetry(bus, data)
