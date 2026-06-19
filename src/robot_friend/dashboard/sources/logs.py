"""Live logs for the dashboard.

Logs are a *stream*, not a latest-value, so they get their own lightweight transport
(:class:`LogStream`) the way video gets :class:`VideoStreams` — a thread-safe
append-only ring buffer with a monotonic cursor. Sync producers append; each
per-client :class:`~robot_friend.dashboard.panels.log_panel.LogPanel` polls
``since(cursor)`` from a ``ui.timer`` and pushes only the new lines, so bursts
between polls are never dropped.

* :class:`BusLogHandler` / :func:`setup_logging` — route Python ``logging`` in.
* :class:`LogSource` — live: install the handler on the root logger.
* :class:`FakeLogSource` — demo: append deterministic scripted lines per scenario.
"""
from __future__ import annotations

import logging
import threading
from collections import deque

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.utils.finch_logger.finch_logger import finch_logger

_DEFAULT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%H:%M:%S"


class LogStream:
    """Append-only ring buffer of recent log lines with an absolute cursor.

    The cursor is the count of lines ever appended; :meth:`since` returns the lines
    added after a given cursor (clamped to what's still buffered), so a freshly
    connected panel sees the recent history and then only new lines.
    """

    def __init__(self, capacity: int = 1000) -> None:
        self._lock = threading.Lock()
        self._lines: deque[str] = deque(maxlen=capacity)
        self._evicted = 0  # lines dropped off the left; cursor offset of _lines[0]

    def append(self, line: str) -> None:
        with self._lock:
            if self._lines.maxlen is not None and len(self._lines) == self._lines.maxlen:
                self._evicted += 1  # the leftmost line is about to fall out
            self._lines.append(line)

    def since(self, cursor: int) -> tuple[list[str], int]:
        """Return ``(new_lines_after_cursor, new_cursor)``."""
        with self._lock:
            total = self._evicted + len(self._lines)
            if cursor >= total:
                return [], total
            start = max(cursor, self._evicted)
            return list(self._lines)[start - self._evicted:], total

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self._lines)


class BusLogHandler(logging.Handler):
    """A ``logging.Handler`` that fans formatted records out to a :class:`LogStream`."""

    def __init__(self, log_stream: LogStream, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self._log_stream = log_stream

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._log_stream.append(self.format(record))
        except Exception:  # pragma: no cover - logging must never raise
            self.handleError(record)


def setup_logging(
    log_stream: LogStream,
    *,
    level: int = logging.INFO,
    fmt: str = _DEFAULT_FORMAT,
    datefmt: str = _DEFAULT_DATEFMT,
) -> BusLogHandler:
    """Route ``finch_logger`` and propagated standard logging into ``log_stream``."""

    existing = next(
        (h for h in finch_logger.handlers if isinstance(h, BusLogHandler)), None
    )
    if existing is not None:
        return existing

    handler = BusLogHandler(log_stream)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

    finch_logger.addHandler(handler)
    return handler


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
