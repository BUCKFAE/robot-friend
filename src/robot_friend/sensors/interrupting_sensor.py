from abc import abstractmethod
from collections.abc import Callable

from robot_friend.sensors.sensor import Sensor
from robot_friend.sensors.sensor_reading import SensorReading


class InterruptingSensor[ReadingT: SensorReading](Sensor[ReadingT]):
    """A sensor that also pushes readings when its interrupt line fires.

    Implementations typically call :meth:`read` from the interrupt handler, so pushed
    readings are calibrated like polled ones. :class:`SensorSampler` watches instead of
    polling when it is given one of these.
    """

    @abstractmethod
    def start_watching(self, on_reading: Callable[[ReadingT], None]) -> None:
        """Start delivering readings to ``on_reading`` as the interrupt fires."""

    @abstractmethod
    def stop_watching(self) -> None:
        """Stop delivering readings. Safe to call when not watching."""
