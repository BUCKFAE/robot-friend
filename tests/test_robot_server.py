"""RobotServer is the lean stdlib transport main exposes; the dashboard attaches to it.

These exercise the JSON route registry (GET + POST) end-to-end over a real socket (port 0
picks a free port). The MJPEG route is a blocking stream, covered via the proxy parser test."""
import json
import urllib.error
import urllib.request

import pytest

from robot_friend.robot_server import RobotServer


def _get(port: int, path: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
        return response.status, response.read()


def _post(port: int, path: str, body: dict) -> tuple[int, bytes]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read()


def test_get_route_serves_handler_body_with_query():
    server = RobotServer(0)
    server.on_get("/echo.json", lambda q: json.dumps(q).encode())
    try:
        status, body = _get(server.port, "/echo.json?since=7&name=hi")
        assert status == 200
        assert json.loads(body) == {"since": "7", "name": "hi"}
    finally:
        server.shutdown()


def test_post_route_receives_parsed_body():
    received: dict = {}
    server = RobotServer(0)
    server.on_post("/control", lambda body: received.update(body) or b'{"ok": true}')
    try:
        status, response = _post(server.port, "/control", {"camera_index": 2})
        assert status == 200
        assert json.loads(response) == {"ok": True}
        assert received == {"camera_index": 2}
    finally:
        server.shutdown()


def test_unregistered_paths_are_404():
    server = RobotServer(0)
    try:
        for path in ("/nope", "/telemetry.json"):
            with pytest.raises(urllib.error.HTTPError) as excinfo:
                _get(server.port, path)
            assert excinfo.value.code == 404
    finally:
        server.shutdown()
