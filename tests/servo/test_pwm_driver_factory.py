"""PwmDriverFactory returns the fake driver off-Pi, and when the I2C bus is unavailable."""
from robot_friend.servo.backends.fake.fake_pwm_driver import FakePwmDriver
from robot_friend.servo.pwm_driver_factory import PwmDriverFactory


def test_off_pi_returns_fake_driver(monkeypatch):
    monkeypatch.setattr("robot_friend.servo.pwm_driver_factory.is_pi_host", lambda: False)
    assert isinstance(PwmDriverFactory.get_pwm_driver(), FakePwmDriver)


def test_pi_falls_back_to_fake_when_bus_unavailable(monkeypatch):
    # Force the Pi branch on a machine with no I2C bus: opening the real PCA9685 raises
    # MissingI2cBusException, and the factory must fall back instead of propagating it.
    monkeypatch.setattr("robot_friend.servo.pwm_driver_factory.is_pi_host", lambda: True)
    assert isinstance(PwmDriverFactory.get_pwm_driver(), FakePwmDriver)
