"""The ADXL345 driver against a fake bus: setup, scaling, and how it fails."""
import pytest

from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException
from robot_friend.exceptions.sensor_exception import SensorReadException
from robot_friend.i2c.backends.fake.fake_i2c_device import FakeI2cDevice, I2cCall
from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2
from robot_friend.sensors.accelerometer.backends.adxl345.adxl345_accelerometer import (
    Adxl345Accelerometer,
)
from robot_friend.sensors.accelerometer.calibration import AccelerometerCalibration

_DEVID, _BW_RATE, _POWER_CTL, _DATA_FORMAT, _DATAX0 = 0x00, 0x2C, 0x2D, 0x31, 0x32

# One real sample from the wired-up sensor: x=-113, y=-211, z=145 counts.
_SAMPLE = {0x32: 0x8F, 0x33: 0xFF, 0x34: 0x2D, 0x35: 0xFF, 0x36: 0x91, 0x37: 0x00}
_COUNT_TO_MS2 = GRAVITY_MS2 / 256


def _device(**overrides) -> FakeI2cDevice:
    registers = {_DEVID: 0xE5} | overrides.pop("registers", {})
    return FakeI2cDevice(address=0x53, registers=registers, **overrides)


def test_setup_checks_the_device_id_then_starts_measuring():
    device = _device()
    Adxl345Accelerometer(device)
    assert device.calls == [
        I2cCall("read", _DEVID),
        I2cCall("write", _DATA_FORMAT, (0x08,)),  # full resolution, +/-2 g
        I2cCall("write", _BW_RATE, (0x0A,)),  # 100 Hz
        I2cCall("write", _POWER_CTL, (0x08,)),  # leave standby
    ]


def test_a_part_that_is_not_an_adxl345_is_rejected():
    device = _device(registers={_DEVID: 0x00})
    with pytest.raises(MissingI2cDeviceException, match="expected 0xe5"):
        Adxl345Accelerometer(device)
    assert I2cCall("close") in device.calls


def test_reading_scales_raw_counts_to_ms2():
    accelerometer = Adxl345Accelerometer(_device(registers=_SAMPLE))
    reading = accelerometer.read()
    assert reading.x == pytest.approx(-113 * _COUNT_TO_MS2)
    assert reading.y == pytest.approx(-211 * _COUNT_TO_MS2)
    assert reading.z == pytest.approx(145 * _COUNT_TO_MS2)


def test_reading_asks_for_all_six_data_registers_at_once():
    device = _device(registers=_SAMPLE)
    accelerometer = Adxl345Accelerometer(device)
    device.calls.clear()
    accelerometer.read()
    assert device.calls == [I2cCall("read_block", _DATAX0, (6,))]


def test_calibration_is_applied_to_reads():
    accelerometer = Adxl345Accelerometer(
        _device(registers=_SAMPLE),
        calibration=AccelerometerCalibration(offset=(1.0, 0.0, 0.0)),
    )
    assert accelerometer.read().x == pytest.approx(accelerometer.read_raw().x - 1.0)


def test_a_sensor_that_stops_answering_raises_a_read_error():
    device = _device(registers=_SAMPLE)
    accelerometer = Adxl345Accelerometer(device)
    device.set_answering(False)
    with pytest.raises(SensorReadException):
        accelerometer.read()
