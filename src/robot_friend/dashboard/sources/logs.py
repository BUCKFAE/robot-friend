"""Dashboard log sources.

The log transport itself (:class:`LogStream`, :class:`BusLogHandler`, :func:`setup_logging`)
lives in :mod:`robot_friend.utils.log_buffer` so the robot can reuse it without the web
stack; this module holds the dashboard-specific *sources* that fill the panel's stream:

* :class:`LogSource` — live: route this (dashboard) process's ``logging`` into the panel.
* :class:`FakeLogSource` — demo: append deterministic scripted lines per scenario.

(The robot's own logs arrive via :class:`~robot_friend.dashboard.sources.robot_log_source.RobotLogSource`.)
"""
from __future__ import annotations

import logging

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.utils.finch_logger.finch_logger import finch_logger
from robot_friend.utils.log_buffer import BusLogHandler, LogStream, setup_logging

# Re-exported so existing imports (`from ...sources.logs import LogStream, setup_logging`)
# keep working now that the transport lives in utils.log_buffer.
__all__ = ["BusLogHandler", "FakeLogSource", "LogSource", "LogStream", "setup_logging"]


class LogSource(DashboardDataSource):
    """Live source: route the application's Python ``logging`` into the log panel."""

    channel = "logs"

    def __init__(self, log_stream: LogStream, *, level: int = logging.INFO) -> None:
        self._log_stream = log_stream
        self._level = level

    def start(self, bus: Bus) -> None:
        setup_logging(self._log_stream, level=self._level)
        finch_logger.info("dashboard logging initialised")


# Deterministic scripted log lines per scenario (no real timestamps, so demo
# screenshots are stable). `stress_text` carries the long/unicode overflow stressors.
_NOMINAL_LOGS = [
    "12:00:01 INFO    robot_friend.dashboard: dashboard started (demo mode)",
    "12:00:01 INFO    robot_friend.camera: opened PiCamera (1280x960, RGB888)",
    "12:00:02 INFO    robot_friend.image: HailoImageDetector ready (yolov8n, conf=0.40)",
    "12:00:02 DEBUG   robot_friend.image: detect() 41.7ms -> 1 person (0.97)",
    "12:00:03 WARNING robot_friend.audio.capture: input overrun, dropped 1 block",
    "12:00:03 INFO    robot_friend.audio: transcript 'hey finch' (de, conf=0.88)",
    "12:00:04 ERROR   robot_friend.serial: no device on /dev/ttyACM0 (will retry)",
]

_STRESS_LOGS = [
    "12:00:01 INFO    robot_friend.dashboard: " + "a very long log line meant to test horizontal overflow and wrapping behaviour " * 4,
    "12:00:02 DEBUG   robot_friend.image.backends.ultralytics.yolo_detector: boxes=["
    + ", ".join(f"(x1={i*37},y1={i*11},x2={i*37+120},y2={i*11+240},conf=0.9{i})" for i in range(8)) + "]",
    "12:00:03 WARNING robot_friend.audio.capture.vad_segmenter: rms=0.0123456789 thr=0.02 — segment too short ✋🔊 (unicode: äöü ß 你好 こんにちは 🤖)",
    "12:00:04 ERROR   robot_friend.x: " + "ERRORERROR" * 30,
]


def _fake_log_lines(scenario: str) -> list[str]:
    if scenario == "empty":
        return []
    if scenario == "stress_text":
        return _STRESS_LOGS
    if scenario == "dense":
        # Many lines to stress the scroll/grid; deterministic content.
        return [f"12:00:{i // 60:02d}.{i % 60:02d} INFO robot_friend.loop: tick #{i} cpu=37% temp=52C fps=24" for i in range(60)]
    return _NOMINAL_LOGS


class FakeLogSource(DashboardDataSource):
    """Demo source: append a fixed, deterministic set of log lines for ``scenario``."""

    channel = "logs"

    def __init__(self, log_stream: LogStream, scenario: str = "nominal") -> None:
        self._log_stream = log_stream
        self._scenario = scenario

    def start(self, bus: Bus) -> None:
        for line in _fake_log_lines(self._scenario):
            self._log_stream.append(line)
