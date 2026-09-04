
class SensorException(Exception):
    """Something went wrong with a sensor."""


class SensorReadException(SensorException):
    """Taking a reading failed. Backends translate their transport errors into this."""


class SensorCalibrationException(SensorException):
    """A calibration could not be measured, loaded or saved."""
