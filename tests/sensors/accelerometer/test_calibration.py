"""AccelerometerCalibration corrects a reading without disturbing anything else."""
import pytest

from robot_friend.sensors.accelerometer.acceleration import Acceleration
from robot_friend.sensors.accelerometer.calibration import AccelerometerCalibration
from robot_friend.sensors.calibration import IdentityCalibration

_RAW = Acceleration(x=1.0, y=2.0, z=3.0, timestamp=123.0)


def test_offset_is_subtracted_before_scaling():
    calibration = AccelerometerCalibration(offset=(1.0, 1.0, 1.0), scale=(2.0, 2.0, 2.0))
    corrected = calibration.apply(_RAW)
    assert (corrected.x, corrected.y, corrected.z) == pytest.approx((0.0, 2.0, 4.0))


def test_the_timestamp_survives_correction():
    assert AccelerometerCalibration(offset=(9.0, 9.0, 9.0)).apply(_RAW).timestamp == 123.0


def test_the_default_calibration_changes_nothing():
    corrected = AccelerometerCalibration().apply(_RAW)
    assert (corrected.x, corrected.y, corrected.z) == (1.0, 2.0, 3.0)


def test_identity_calibration_hands_the_reading_straight_back():
    assert IdentityCalibration().apply(_RAW) is _RAW
