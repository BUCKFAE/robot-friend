import time
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True, slots=True)
class SensorReading:
    """One sample taken from a sensor.

    Attributes:
        timestamp: ``time.monotonic()`` at the moment of the reading, for sample
            deltas and staleness (not wall-clock; the telemetry layer adds that).
    """
    timestamp: float = field(default_factory=time.monotonic)
