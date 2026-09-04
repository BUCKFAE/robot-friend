"""SensorSampler keeps the history, whether readings are polled or pushed."""
import time

from robot_friend.exceptions.sensor_exception import SensorReadException
from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2, Acceleration
from robot_friend.sensors.accelerometer.backends.fake.fake_accelerometer import (
    FakeAccelerometer,
)
from robot_friend.sensors.interrupting_sensor import InterruptingSensor
from robot_friend.sensors.sensor_sampler import SensorSampler

_AT_REST = Acceleration(x=0.0, y=0.0, z=GRAVITY_MS2)


class TappingAccelerometer(InterruptingSensor[Acceleration]):
    """Stands in for a sensor with its interrupt line wired: it pushes when told to."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._on_reading = None

    def read_raw(self) -> Acceleration:
        return _AT_REST

    def start_watching(self, on_reading) -> None:
        self._on_reading = on_reading

    def stop_watching(self) -> None:
        self._on_reading = None

    def fire(self) -> None:
        if self._on_reading is not None:
            self._on_reading(self.read())


class FlakyAccelerometer(FakeAccelerometer):
    """Fails its first few reads, like a sensor with a loose wire."""

    def __init__(self, failures: int) -> None:
        super().__init__()
        self._failures = failures

    def read_raw(self) -> Acceleration:
        if self._failures > 0:
            self._failures -= 1
            raise SensorReadException("bus fell over")
        return super().read_raw()


def _wait_for(predicate, timeout: float = 2.0) -> bool:
    """Wait for a background thread to get somewhere, without a fixed sleep."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False


def test_sample_records_without_anything_started():
    sampler = SensorSampler(FakeAccelerometer())
    reading = sampler.sample()
    assert sampler.history == [reading]
    assert sampler.latest is reading


def test_history_keeps_only_the_most_recent_readings():
    sampler = SensorSampler(FakeAccelerometer(), history_size=3)
    for _ in range(5):
        sampler.sample()
    assert len(sampler.history) == 3


def test_latest_is_none_before_anything_is_read():
    assert SensorSampler(FakeAccelerometer()).latest is None


def test_polling_collects_in_the_background():
    sampler = SensorSampler(FakeAccelerometer(), interval=0.001)
    assert not sampler.is_interrupt_driven
    with sampler:
        assert _wait_for(lambda: len(sampler.history) >= 3)


def test_polling_survives_failing_reads():
    sampler = SensorSampler(FlakyAccelerometer(failures=3), interval=0.001)
    with sampler:
        assert _wait_for(lambda: bool(sampler.history))


def test_an_interrupting_sensor_is_watched_not_polled():
    sensor = TappingAccelerometer()
    sampler = SensorSampler(sensor, interval=0.001)
    assert sampler.is_interrupt_driven
    sampler.start()
    sensor.fire()
    sensor.fire()
    sampler.stop()
    sensor.fire()
    assert len(sampler.history) == 2


def test_pushed_readings_are_calibrated_like_polled_ones():
    from robot_friend.sensors.accelerometer.calibration import AccelerometerCalibration

    sensor = TappingAccelerometer(calibration=AccelerometerCalibration(offset=(0.0, 0.0, 0.8)))
    sampler = SensorSampler(sensor)
    with sampler:
        sensor.fire()
    assert sampler.latest.z == GRAVITY_MS2 - 0.8
