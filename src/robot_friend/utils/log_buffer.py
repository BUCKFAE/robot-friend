"""Append-only log ring buffer + a logging handler that fills it.

Both the dashboard and the robot (``robot_friend.main``) capture their own process's
Python ``logging`` into a :class:`LogStream`: the dashboard renders it in the Logs panel,
and the robot serves its own via ``GET /logs.json`` so the dashboard can show the robot's
logs too. Kept dependency-light (stdlib + ``finch_logger``) so the lean detection process
can use it without the web stack.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import deque

from robot_friend.utils.finch_logger.finch_logger import finch_logger

_DEFAULT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%H:%M:%S"


class LogStream:
    """Append-only ring buffer of recent log lines with an absolute cursor.

    The cursor is the count of lines ever appended; :meth:`since` returns the lines
    added after a given cursor (clamped to what's still buffered), so a freshly
    connected reader sees the recent history and then only new lines.
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


def logs_since_json(log_stream: LogStream, since: int) -> bytes:
    """Serialize new log lines after ``since`` as JSON: ``{"lines": [...], "cursor": N}``.

    The wire shape the robot serves on ``GET /logs.json`` and the dashboard polls.
    """
    lines, cursor = log_stream.since(since)
    return json.dumps({"lines": lines, "cursor": cursor}).encode("utf-8")
