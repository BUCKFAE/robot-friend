"""ServoController bridges HTTP payloads to servos and owns the /servos.json shape."""
import json

from robot_friend.servo.backends.fake.fake_pwm_driver import FakePwmDriver
from robot_friend.servo.servo_controller import ServoController, ServoSpec

_STATE_KEYS = {
    "channel",
    "label",
    "angle",
    "min_angle",
    "max_angle",
    "off_counts",
    "calibration",
}


def _controller() -> ServoController:
    driver = FakePwmDriver(pwm_freq_hz=50)
    return ServoController(driver, [ServoSpec(0, "pan"), ServoSpec(1, "tilt")])


def test_centers_servos_on_start():
    assert all(s.angle == 90.0 for s in _controller().states())


def test_snapshot_has_servos_and_driver_name():
    snapshot = _controller().snapshot()
    assert snapshot["driver"] == "FakePwmDriver"
    assert {s["label"] for s in snapshot["servos"]} == {"pan", "tilt"}
    assert all(set(s) == _STATE_KEYS for s in snapshot["servos"])


def test_snapshot_is_json_serializable():
    json.dumps(_controller().snapshot())  # must not raise


def test_apply_angle_command():
    controller = _controller()
    controller.apply({"channel": 1, "angle": 120})
    tilt = next(s for s in controller.states() if s.channel == 1)
    assert tilt.angle == 120.0


def test_apply_neutral_command():
    controller = _controller()
    controller.apply({"channel": 0, "angle": 30})
    controller.apply({"channel": 0, "neutral": True})
    pan = next(s for s in controller.states() if s.channel == 0)
    assert pan.angle == 90.0


def test_apply_ignores_missing_channel():
    controller = _controller()
    controller.apply({"angle": 50})  # no channel -> no-op, no raise
    assert all(s.angle == 90.0 for s in controller.states())


def test_set_angle_unknown_channel_is_noop():
    controller = _controller()
    controller.set_angle(9, 45)  # no servo on channel 9
    assert all(s.angle == 90.0 for s in controller.states())


def test_apply_calibration_retrims_pulse_without_changing_reported_angle():
    controller = _controller()
    controller.apply({"channel": 0, "angle": 90})
    before = next(s for s in controller.states() if s.channel == 0)
    controller.apply({"channel": 0, "calibration": 10})
    after = next(s for s in controller.states() if s.channel == 0)
    assert after.angle == before.angle  # reported (requested) angle is unchanged
    assert after.calibration == 10.0
    assert after.off_counts != before.off_counts  # but the pulse is re-trimmed
