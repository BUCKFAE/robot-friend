"""Browser-free unit tests for the log transport + handler (runs under default pytest)."""
import logging

from robot_friend.dashboard.sources.logs import (
    BusLogHandler,
    FakeLogSource,
    LogStream,
    _fake_log_lines,
    setup_logging,
)
from robot_friend.utils.finch_logger import finch_logger


def test_logstream_since_returns_only_new_lines():
    stream = LogStream()
    lines, cursor = stream.since(0)
    assert lines == [] and cursor == 0

    stream.append("a")
    stream.append("b")
    lines, cursor = stream.since(0)
    assert lines == ["a", "b"] and cursor == 2

    # Nothing new since the last cursor.
    assert stream.since(cursor) == ([], 2)

    stream.append("c")
    assert stream.since(cursor) == (["c"], 3)


def test_logstream_late_subscriber_sees_buffered_history():
    stream = LogStream()
    for line in ("x", "y", "z"):
        stream.append(line)
    # A panel connecting at cursor 0 should get the buffered history, not nothing.
    lines, cursor = stream.since(0)
    assert lines == ["x", "y", "z"] and cursor == 3


def test_logstream_eviction_clamps_cursor():
    stream = LogStream(capacity=3)
    for i in range(5):  # 0,1,2 evicted-then-kept; only last 3 remain
        stream.append(str(i))
    assert stream.snapshot() == ["2", "3", "4"]
    # Cursor 0 points before the evicted region: clamp to the oldest still buffered.
    lines, cursor = stream.since(0)
    assert lines == ["2", "3", "4"] and cursor == 5


def test_bus_log_handler_routes_records_into_stream():
    stream = LogStream()
    handler = BusLogHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger = logging.getLogger("robot_friend.test.loghandler")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        logger.info("hello")
        logger.warning("careful")
    finally:
        logger.removeHandler(handler)
    assert stream.snapshot() == ["INFO:hello", "WARNING:careful"]


def test_setup_logging_routes_finch_logger_into_stream():
    stream = LogStream()
    handler = setup_logging(stream)
    try:
        finch_logger.info("visible in dashboard")
    finally:
        finch_logger.removeHandler(handler)
        logging.getLogger().removeHandler(handler)
    assert any("visible in dashboard" in line for line in stream.snapshot())


def test_fake_log_source_populates_per_scenario():
    nominal = LogStream()
    FakeLogSource(nominal, "nominal").start(bus=None)  # type: ignore[arg-type]
    assert nominal.snapshot() == _fake_log_lines("nominal")
    assert len(nominal.snapshot()) > 0

    empty = LogStream()
    FakeLogSource(empty, "empty").start(bus=None)  # type: ignore[arg-type]
    assert empty.snapshot() == []
