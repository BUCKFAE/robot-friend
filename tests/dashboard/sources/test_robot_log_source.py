"""End-to-end: the robot's logs must stream to the dashboard's LogStream over a socket,
incrementally (cursor advances). Import-light, so it runs in the default suite."""
import time

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.robot_log_source import RobotLogSource
from robot_friend.robot_server import RobotServer
from robot_friend.utils.log_buffer import LogStream, logs_since_json


def _joined(stream: LogStream) -> str:
    return "\n".join(stream.snapshot())


def _wait_until(predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        time.sleep(0.02)


def test_robot_logs_stream_to_the_dashboard():
    robot_logs = LogStream()
    robot_logs.append("12:00:01 INFO    robot_friend.image: detector ready")
    server = RobotServer(0)
    server.on_get(
        "/logs.json", lambda q: logs_since_json(robot_logs, int(q.get("since", "0")))
    )
    dash_logs = LogStream()
    source = RobotLogSource(dash_logs, f"http://127.0.0.1:{server.port}", interval=0.02)
    source.start(Bus())
    try:
        _wait_until(lambda: "detector ready" in _joined(dash_logs))
        assert "detector ready" in _joined(dash_logs)

        # A line logged later arrives incrementally (cursor advanced; no duplicates).
        robot_logs.append("12:00:02 WARNING robot_friend.audio: no microphone")
        _wait_until(lambda: "no microphone" in _joined(dash_logs))
        snapshot = dash_logs.snapshot()
        assert "no microphone" in "\n".join(snapshot)
        assert snapshot.count("12:00:01 INFO    robot_friend.image: detector ready") == 1
    finally:
        source.stop()
        server.shutdown()
