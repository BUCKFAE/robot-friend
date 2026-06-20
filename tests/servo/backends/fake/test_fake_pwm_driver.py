"""FakePwmDriver records writes in memory so servos run with no hardware attached."""
import pytest

from robot_friend.servo.backends.fake.fake_pwm_driver import FakePwmDriver
from robot_friend.servo.pwm_driver import MAX_COUNTS


def test_records_last_window_per_channel():
    driver = FakePwmDriver()
    driver.set_pwm(3, 0, 1234)
    state = driver.channel_state(3)
    assert (state.on, state.off) == (0, 1234)


def test_unwritten_channel_reads_zero():
    assert FakePwmDriver().channel_state(7).off == 0


def test_set_pwm_clamps_counts_into_range():
    driver = FakePwmDriver()
    driver.set_pwm(0, -10, 99999)
    state = driver.channel_state(0)
    assert state.on == 0
    assert state.off == MAX_COUNTS


def test_set_duty_cycle_maps_to_counts():
    driver = FakePwmDriver()
    driver.set_duty_cycle(1, 0.5)
    assert driver.channel_state(1).off == round(0.5 * MAX_COUNTS)


def test_set_duty_cycle_clamps_fraction():
    driver = FakePwmDriver()
    driver.set_duty_cycle(2, 5.0)
    assert driver.channel_state(2).off == MAX_COUNTS


@pytest.mark.parametrize("channel", [-1, 16, 99])
def test_invalid_channel_raises(channel):
    with pytest.raises(ValueError):
        FakePwmDriver().set_pwm(channel, 0, 0)


def test_pwm_frequency_is_reported():
    assert FakePwmDriver(pwm_freq_hz=60).pwm_frequency_hz == 60.0


def test_channel_state_duty_is_fraction_of_range():
    driver = FakePwmDriver()
    driver.set_pwm(0, 0, MAX_COUNTS)
    assert driver.channel_state(0).duty == pytest.approx(1.0)
