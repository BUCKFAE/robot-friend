"""Browser-free unit tests for the servo snapshot helpers used to sync moves across clients."""
from robot_friend.dashboard.servos import (
    ServoSnapshot,
    with_angle,
    with_calibration,
)
from robot_friend.servo.servo import ServoState


def _snapshot() -> ServoSnapshot:
    return ServoSnapshot(
        states=(
            ServoState(0, "pan", 90.0, 0.0, 180.0, 307, 0.0),
            ServoState(1, "tilt", 90.0, 0.0, 180.0, 307, 0.0),
        ),
        driver="FakePwmDriver",
    )


def test_with_angle_replaces_only_target_channel():
    snap = _snapshot()
    out = with_angle(snap, 0, 150.0)

    assert out.states[0].angle == 150.0
    assert out.states[1].angle == 90.0     # untouched
    assert out.driver == "FakePwmDriver"
    assert snap.states[0].angle == 90.0    # original snapshot is frozen / unchanged


def test_with_calibration_replaces_only_target_channel():
    snap = _snapshot()
    out = with_calibration(snap, 1, -5.0)

    assert out.states[1].calibration == -5.0
    assert out.states[0].calibration == 0.0


def test_snapshots_compare_by_value():
    # The sync layer dedupes with ==, so equal contents must be equal snapshots.
    assert _snapshot() == _snapshot()
    assert with_angle(_snapshot(), 0, 90.0) == _snapshot()  # no-op move stays equal
    assert with_angle(_snapshot(), 0, 91.0) != _snapshot()
