"""The identity check every I2C driver leans on, exercised through the fake backend."""
import pytest

from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException
from robot_friend.i2c.backends.fake.fake_i2c_device import FakeI2cDevice


def test_require_device_id_accepts_the_expected_part():
    FakeI2cDevice(address=0x53, registers={0x00: 0xE5}).require_device_id(0x00, 0xE5)


def test_require_device_id_rejects_a_different_part():
    device = FakeI2cDevice(address=0x53, registers={0x00: 0x42})
    with pytest.raises(MissingI2cDeviceException, match="0x42"):
        device.require_device_id(0x00, 0xE5)


def test_require_device_id_on_a_silent_bus_reports_a_missing_device():
    device = FakeI2cDevice(address=0x53, answering=False)
    with pytest.raises(MissingI2cDeviceException, match="nothing answering"):
        device.require_device_id(0x00, 0xE5)


def test_probe_fails_when_nothing_answers():
    with pytest.raises(MissingI2cDeviceException):
        FakeI2cDevice(address=0x40, answering=False).probe()
