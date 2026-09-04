
class MissingHardwareException(Exception):
    pass

class MissingSoundDeviceException(MissingHardwareException):
    pass

class MissingI2cBusException(MissingHardwareException):
    """The I2C bus can't be opened (I2C disabled, or the bus number is wrong)."""
    pass

class MissingI2cDeviceException(MissingHardwareException):
    """The bus is fine but nothing (or the wrong part) answers at the address."""
    pass
