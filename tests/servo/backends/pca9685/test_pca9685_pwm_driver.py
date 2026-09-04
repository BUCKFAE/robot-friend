"""The PCA9685's register sequence, driven against a fake bus."""
import pytest

from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException
from robot_friend.i2c.backends.fake.fake_i2c_device import FakeI2cDevice, I2cCall
from robot_friend.servo.backends.pca9685.pca9685_pwm_driver import Pca9685PwmDriver

_MODE1, _MODE2, _PRE_SCALE, _LED0_ON_L = 0x00, 0x01, 0xFE, 0x06


def test_setup_writes_the_documented_register_sequence():
    device = FakeI2cDevice(address=0x40)
    Pca9685PwmDriver(device, pwm_freq_hz=50.0)
    assert device.calls == [
        I2cCall("probe"),
        I2cCall("write", _MODE1, (0x20,)),  # auto-increment
        I2cCall("write", _MODE2, (0x04,)),  # totem-pole output
        I2cCall("read", _MODE1),
        I2cCall("write", _MODE1, (0x30,)),  # sleep, so the prescaler can be set
        I2cCall("write", _PRE_SCALE, (121,)),  # 25 MHz / (4096 * 50 Hz) - 1
        I2cCall("write", _MODE1, (0x20,)),
        I2cCall("write", _MODE1, (0xA0,)),  # restart
    ]


def test_prescale_follows_the_requested_frequency():
    device = FakeI2cDevice(address=0x40)
    Pca9685PwmDriver(device, pwm_freq_hz=60.0)
    assert device.registers[_PRE_SCALE] == 101


def test_set_pwm_writes_one_block_per_channel():
    device = FakeI2cDevice(address=0x40)
    driver = Pca9685PwmDriver(device)
    device.calls.clear()
    driver.set_pwm(2, 0, 1024)
    assert device.calls == [I2cCall("write_block", _LED0_ON_L + 8, (0, 0, 0, 4))]


def test_set_pwm_clamps_out_of_range_counts():
    device = FakeI2cDevice(address=0x40)
    driver = Pca9685PwmDriver(device)
    device.calls.clear()
    driver.set_pwm(0, -5, 99999)
    assert device.calls == [I2cCall("write_block", _LED0_ON_L, (0, 0, 0xFF, 0x0F))]


def test_absent_board_raises_and_releases_the_bus():
    device = FakeI2cDevice(address=0x40, answering=False)
    with pytest.raises(MissingI2cDeviceException):
        Pca9685PwmDriver(device)
    assert I2cCall("close") in device.calls
