
class MissingHardwareException(Exception):
    pass

class MissingSoundDeviceException(MissingHardwareException):
    pass

class MissingI2cBusException(MissingHardwareException):
    """The I2C bus / PCA9685 can't be opened (I2C disabled, or no board wired)."""
    pass