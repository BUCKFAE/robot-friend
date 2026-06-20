"""End-to-end: the dashboard reads the robot's servos and commands an angle back, over a
real socket — the live ``/servos.json`` + ``POST /servo`` channel. Import-light (no web
stack), so it runs in the default suite."""
import json

from robot_friend.dashboard.servos_client import RobotServosClient
from robot_friend.robot_server import RobotServer
from robot_friend.servo.backends.fake.fake_pwm_driver import FakePwmDriver
from robot_friend.servo.servo_controller import ServoController, ServoSpec


def test_dashboard_reads_servos_and_commands_an_angle():
    controller = ServoController(
        FakePwmDriver(pwm_freq_hz=50), [ServoSpec(0, "pan"), ServoSpec(1, "tilt")]
    )
    server = RobotServer(0)
    server.on_get("/servos.json", lambda _q: json.dumps(controller.snapshot()).encode())
    server.on_post("/servo", lambda body: controller.apply(body))
    client = RobotServosClient(f"http://127.0.0.1:{server.port}")
    try:
        # The dashboard sees the robot's servos and the active driver.
        states = client.servos()
        assert {s.label for s in states} == {"pan", "tilt"}
        assert client.driver_label() == "FakePwmDriver"

        # A slider move on the dashboard reaches the robot (POST is synchronous).
        client.set_angle(1, 120)
        tilt = next(s for s in controller.states() if s.channel == 1)
        assert tilt.angle == 120.0

        # ...and the client re-reads it from the robot on the next fetch.
        refreshed = {s.channel: s.angle for s in client.servos()}
        assert refreshed[1] == 120.0
    finally:
        server.shutdown()
