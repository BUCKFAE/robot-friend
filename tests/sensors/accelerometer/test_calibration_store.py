"""A measured calibration survives a round-trip to disk, and a broken file is loud."""
import pytest

from robot_friend.exceptions.sensor_exception import SensorCalibrationException
from robot_friend.sensors.accelerometer.calibration import AccelerometerCalibration
from robot_friend.sensors.accelerometer.calibration_store import (
    load_calibration,
    save_calibration,
)

_CALIBRATION = AccelerometerCalibration(offset=(0.3, -0.2, 0.5), scale=(1.02, 0.98, 1.1))


def test_round_trip(tmp_path):
    path = save_calibration(_CALIBRATION, tmp_path / "accelerometer.json")
    assert load_calibration(path) == _CALIBRATION


def test_saving_creates_the_directory(tmp_path):
    path = save_calibration(_CALIBRATION, tmp_path / "nested" / "accelerometer.json")
    assert path.is_file()


def test_an_uncalibrated_robot_loads_nothing(tmp_path):
    assert load_calibration(tmp_path / "absent.json") is None


def test_a_corrupt_file_is_reported_rather_than_ignored(tmp_path):
    path = tmp_path / "accelerometer.json"
    path.write_text("{not json")
    with pytest.raises(SensorCalibrationException):
        load_calibration(path)


def test_a_file_missing_a_field_is_reported(tmp_path):
    path = tmp_path / "accelerometer.json"
    path.write_text('{"offset": [0, 0, 0]}')
    with pytest.raises(SensorCalibrationException):
        load_calibration(path)
