import threading
from collections import deque
from typing import Self

from robot_friend.exceptions.sensor_exception import SensorReadException
from robot_friend.sensors.interrupting_sensor import InterruptingSensor
from robot_friend.sensors.sensor import Sensor
from robot_friend.sensors.sensor_reading import SensorReading
from robot_friend.utils.finch_logger import finch_logger


class SensorSampler[ReadingT: SensorReading]:
    """Collects readings from a sensor and keeps the last N of them.

    Sensors stay stateless; history lives here, so it is written and tested once. How
    the readings arrive depends on the sensor: an :class:`InterruptingSensor` is watched
    and pushes them, anything else is polled on a background thread.
    """

    def __init__(
        self,
        sensor: Sensor[ReadingT],
        *,
        interval: float = 0.05,
        history_size: int = 100,
    ) -> None:
        """
        Args:
            sensor: The sensor to collect from.
            interval: Seconds between polls. Ignored for an interrupting sensor.
            history_size: How many readings to keep before the oldest fall off.
        """
        self._sensor = sensor
        self._interval = interval
        self._readings: deque[ReadingT] = deque(maxlen=history_size)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._failing = False

    @property
    def is_interrupt_driven(self) -> bool:
        return isinstance(self._sensor, InterruptingSensor)

    def sample(self) -> ReadingT:
        """Read once and record it. Usable on its own, with nothing started."""
        reading = self._sensor.read()
        self._record(reading)
        return reading

    @property
    def latest(self) -> ReadingT | None:
        with self._lock:
            return self._readings[-1] if self._readings else None

    @property
    def history(self) -> list[ReadingT]:
        with self._lock:
            return list(self._readings)

    def start(self) -> None:
        """Begin collecting: watch an interrupting sensor, poll anything else."""
        if isinstance(self._sensor, InterruptingSensor):
            self._sensor.start_watching(self._record)
            return
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._poll, daemon=True, name="sensor-sampler"
        )
        self._thread.start()

    def stop(self) -> None:
        if isinstance(self._sensor, InterruptingSensor):
            self._sensor.stop_watching()
            return
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            # The loop wakes every interval, so one interval plus slack is enough.
            thread.join(timeout=self._interval + 1.0)

    def _record(self, reading: ReadingT) -> None:
        """Store a reading. Called from the polling thread or the sensor's interrupt."""
        with self._lock:
            self._readings.append(reading)

    def _poll(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self.sample()
            except SensorReadException as exc:
                # A sensor that drops off the bus must not kill the thread: log the
                # first failure of a streak, then keep trying.
                if not self._failing:
                    finch_logger.warning("sensor read failed (%s); retrying", exc)
                    self._failing = True
                continue
            except Exception:  # noqa: BLE001
                finch_logger.exception("unexpected sensor failure; retrying")
                self._failing = True
                continue
            self._failing = False

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
