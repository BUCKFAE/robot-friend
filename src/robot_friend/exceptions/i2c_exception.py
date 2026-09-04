
class I2cException(Exception):
    """Something went wrong talking to a device on an I2C bus."""


class I2cTransferException(I2cException):
    """A read or write to a device that was present at open time failed."""
