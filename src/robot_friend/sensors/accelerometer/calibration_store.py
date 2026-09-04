"""Reading and writing a measured accelerometer calibration as JSON."""
import json
from pathlib import Path

from robot_friend.exceptions.sensor_exception import SensorCalibrationException
from robot_friend.resource_handler import get_accelerometer_calibration_file
from robot_friend.sensors.accelerometer.calibration import AccelerometerCalibration


def save_calibration(
    calibration: AccelerometerCalibration, path: Path | None = None
) -> Path:
    """Write ``calibration`` to ``path`` (the default location if omitted).

    Returns:
        The path written to.
    """
    path = path or get_accelerometer_calibration_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {'offset': list(calibration.offset), 'scale': list(calibration.scale)},
            indent=2,
        )
    )
    return path


def load_calibration(path: Path | None = None) -> AccelerometerCalibration | None:
    """Read a saved calibration.

    Returns:
        The stored calibration, or None if no file has been written yet.

    Raises:
        SensorCalibrationException: If the file exists but cannot be read — better than
            silently running uncalibrated on a robot someone did calibrate.
    """
    path = path or get_accelerometer_calibration_file()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return AccelerometerCalibration(
            offset=tuple(float(value) for value in data['offset']),
            scale=tuple(float(value) for value in data['scale']),
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SensorCalibrationException(
            f'could not read the calibration at {path}: {exc}'
        ) from exc
