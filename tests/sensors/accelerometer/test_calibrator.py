"""The six-position routine recovers the offset and sensitivity it was given."""
import pytest

from robot_friend.exceptions.sensor_exception import SensorCalibrationException
from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2
from robot_friend.sensors.accelerometer.backends.fake.fake_accelerometer import (
    FakeAccelerometer,
)
from robot_friend.sensors.accelerometer.calibrator import (
    AccelerometerCalibrator,
    AccelerometerOrientation,
)

# What we pretend the physical part is doing wrong.
_OFFSET = (0.30, -0.20, 0.50)
_SCALE = (1.02, 0.98, 1.10)


def _raw_for(orientation: AccelerometerOrientation) -> tuple[float, float, float]:
    """What a sensor with the errors above reports in this orientation."""
    true = [0.0, 0.0, 0.0]
    true[orientation.value.axis] = orientation.value.sign * GRAVITY_MS2
    return tuple(value / scale + offset for value, scale, offset in zip(true, _SCALE, _OFFSET))


def _calibrate(accelerometer: FakeAccelerometer) -> AccelerometerCalibrator:
    calibrator = AccelerometerCalibrator(accelerometer, samples=2, delay=0.0)
    for orientation in AccelerometerOrientation:
        x, y, z = _raw_for(orientation)
        accelerometer.set_acceleration(x=x, y=y, z=z)
        calibrator.record(orientation)
    return calibrator


def test_six_orientations_recover_the_offset_and_scale():
    calibration = _calibrate(FakeAccelerometer()).calibration()
    assert calibration.offset == pytest.approx(_OFFSET)
    assert calibration.scale == pytest.approx(_SCALE)


def test_the_measured_calibration_makes_the_sensor_read_one_g():
    accelerometer = FakeAccelerometer()
    accelerometer.apply_calibration(_calibrate(accelerometer).calibration())
    x, y, z = _raw_for(AccelerometerOrientation.Z_UP)
    accelerometer.set_acceleration(x=x, y=y, z=z)
    assert accelerometer.read().magnitude == pytest.approx(GRAVITY_MS2)


def test_missing_orientations_are_reported_rather_than_guessed():
    calibrator = AccelerometerCalibrator(FakeAccelerometer(), samples=1, delay=0.0)
    calibrator.record(AccelerometerOrientation.Z_UP)
    assert AccelerometerOrientation.Z_UP not in calibrator.missing
    with pytest.raises(SensorCalibrationException, match="X_UP"):
        calibrator.calibration()


def test_a_sensor_that_was_never_turned_over_is_rejected():
    accelerometer = FakeAccelerometer()
    calibrator = AccelerometerCalibrator(accelerometer, samples=1, delay=0.0)
    for orientation in AccelerometerOrientation:
        calibrator.record(orientation)  # never moved between placements
    with pytest.raises(SensorCalibrationException, match="2 g"):
        calibrator.calibration()
