"""End-to-end: the dashboard must be able to read the robot's devices and command a
selection back, over a real socket — the control channel for the inert-selectors fix.
Import-light (no web stack), so it runs in the default suite."""
import json

from robot_friend.control import RobotControls
from robot_friend.dashboard.controls_client import RobotControlsClient
from robot_friend.robot_server import RobotServer


def test_dashboard_reads_devices_and_commands_the_robot():
    controls = RobotControls()
    server = RobotServer(0)
    server.on_get("/devices.json", lambda _q: json.dumps(controls.devices_payload()).encode())
    server.on_post("/control", lambda body: controls.apply(body))
    client = RobotControlsClient(f"http://127.0.0.1:{server.port}")
    try:
        # The dashboard sees the robot's devices (at least one fallback option each).
        assert len(client.camera_options()) >= 1
        assert len(client.sound_options()) >= 1

        # A selection on the dashboard reaches the robot (POST is synchronous).
        client.set_sound_device(3)
        assert controls.sound_device == 3

        # ...and the client re-reads it from the robot on the next fetch.
        client.camera_options()  # triggers a /devices.json refresh
        assert client.sound_device == 3
    finally:
        server.shutdown()
