"""Servo maps angle -> microseconds -> PWM counts on top of any PwmDriver."""
from robot_friend.servo.backends.fake.fake_pwm_driver import FakePwmDriver
from robot_friend.servo.servo import Servo, ServoConfig, move_group, wait_all_servos

# At 50 Hz the period is 20 ms = 4096 counts, so the default 1000/1500/2000 us servo pulses
# land on these off-tick counts: int(us / 20000 * 4096).
_OFF_AT_0_DEG = 204
_OFF_AT_90_DEG = 307
_OFF_AT_180_DEG = 409


def _servo(channel: int = 0, **kwargs) -> tuple[Servo, FakePwmDriver]:
    driver = FakePwmDriver(pwm_freq_hz=50)
    return Servo(driver, channel, **kwargs), driver


def test_min_mid_max_angles_map_to_expected_counts():
    servo, driver = _servo()
    servo.angle(0)
    assert driver.channel_state(0).off == _OFF_AT_0_DEG
    servo.angle(90)
    assert driver.channel_state(0).off == _OFF_AT_90_DEG
    servo.angle(180)
    assert driver.channel_state(0).off == _OFF_AT_180_DEG


def test_angle_is_clamped_to_range():
    servo, driver = _servo()
    servo.angle(999)
    assert servo.current_angle == 180.0
    assert driver.channel_state(0).off == _OFF_AT_180_DEG
    servo.angle(-50)
    assert servo.current_angle == 0.0


def test_default_state_is_neutral_before_first_move():
    servo, _ = _servo()
    assert servo.current_angle == 90.0


def test_current_angle_and_last_off_counts_track_commands():
    servo, _ = _servo()
    servo.angle(45)
    assert servo.current_angle == 45.0
    assert servo.last_off_counts == servo.state().off_counts


def test_move_neutral_centers():
    servo, _ = _servo()
    servo.angle(10)
    servo.move_neutral()
    assert servo.current_angle == 90.0


def test_calibration_shifts_pulse_but_not_reported_angle():
    servo, driver = _servo()
    servo.angle(90)
    neutral_counts = driver.channel_state(0).off
    servo.calibrate(10)  # shift the mechanical mid-point by +10 deg
    servo.angle(90)
    assert servo.current_angle == 90.0  # reports the request, not the trimmed value
    assert servo.calibration == 10.0
    assert driver.channel_state(0).off != neutral_counts


def test_reapplying_angle_after_calibration_does_not_drift():
    servo, driver = _servo()
    servo.calibrate(10)
    servo.angle(120)
    counts_first = driver.channel_state(0).off
    servo.angle(servo.current_angle)  # re-apply the requested angle (what set_calibration does)
    assert driver.channel_state(0).off == counts_first  # idempotent, no compounding
    assert servo.current_angle == 120.0


def test_state_reports_channel_label_and_range():
    servo, _ = _servo(channel=4, label="pan")
    state = servo.state()
    assert state.channel == 4
    assert state.label == "pan"
    assert (state.min_angle, state.max_angle) == (0.0, 180.0)


def test_writes_only_the_bound_channel():
    servo, driver = _servo(channel=5)
    servo.angle(0)
    assert driver.channel_state(5).off == _OFF_AT_0_DEG
    assert driver.channel_state(0).off == 0  # untouched


def test_custom_config_changes_pulse_mapping():
    driver = FakePwmDriver(pwm_freq_hz=50)
    servo = Servo(driver, 0, ServoConfig(max_angle=270.0))
    servo.angle(135)  # the 270-deg servo's neutral -> mid_us (1500) -> 307 counts
    assert driver.channel_state(0).off == _OFF_AT_90_DEG


def test_move_group_commands_all_and_sets_deadlines(monkeypatch):
    monkeypatch.setattr("robot_friend.servo.servo.time.sleep", lambda _s: None)
    s1, d1 = _servo(0)
    s2, d2 = _servo(1)
    move_group([(s1, 0), (s2, 180)])
    assert d1.channel_state(0).off == _OFF_AT_0_DEG
    assert d2.channel_state(1).off == _OFF_AT_180_DEG
    assert s1.wait_until is not None
    assert s2.wait_until is not None


def test_wait_all_servos_with_no_moves_is_noop():
    servo, _ = _servo()  # never commanded -> wait_until is None
    wait_all_servos([servo])  # returns immediately, no sleep
