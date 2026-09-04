"""Register-level access to one device on an I2C bus.

The hardware seam under the PCA9685 servo driver and the ADXL345 accelerometer:
:class:`SmbusI2cDevice` talks to a real bus, :class:`FakeI2cDevice` records what it was
told, so both drivers can be driven with nothing wired up. Mirrors the ``servo``
subsystem's :class:`PwmDriver` ABC + ``backends/`` layout.
"""
from abc import ABC, abstractmethod
from typing import Self

from robot_friend.exceptions.i2c_exception import I2cTransferException
from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException


class I2cDevice(ABC):
    """One device at a fixed address on one bus.

    Implementations raise :class:`I2cTransferException` for a transfer that fails, so
    callers never see a raw ``OSError``.
    """

    def __init__(self, *, address: int, bus: int = 1) -> None:
        """
        Args:
            address: 7-bit I2C address of the device.
            bus: I2C bus number (``1`` on a Raspberry Pi).
        """
        self._address = address
        self._bus_number = bus

    @property
    def address(self) -> int:
        return self._address

    @property
    def bus_number(self) -> int:
        return self._bus_number

    @abstractmethod
    def read_byte(self, register: int) -> int:
        """Read one register."""

    @abstractmethod
    def read_block(self, register: int, length: int) -> list[int]:
        """Read ``length`` consecutive registers in one transaction."""

    @abstractmethod
    def write_byte(self, register: int, value: int) -> None:
        """Write one register."""

    @abstractmethod
    def write_block(self, register: int, values: list[int]) -> None:
        """Write consecutive registers in one transaction (needs device auto-increment)."""

    @abstractmethod
    def probe(self) -> None:
        """Check something acknowledges at this address, touching no register.

        Raises:
            MissingI2cDeviceException: If nothing answers.
        """

    def require_device_id(self, register: int, expected: int) -> None:
        """Check the device identifies itself as the part we expect.

        Raises:
            MissingI2cDeviceException: If nothing answers, or the id does not match —
                a different board at that address, or the part is in another mode.
        """
        try:
            device_id = self.read_byte(register)
        except I2cTransferException as exc:
            raise MissingI2cDeviceException(
                f"nothing answering at {self._address:#04x} on I2C bus {self._bus_number}"
            ) from exc
        if device_id != expected:
            raise MissingI2cDeviceException(
                f"device at {self._address:#04x} on I2C bus {self._bus_number} reports id "
                f"{device_id:#04x}, expected {expected:#04x}"
            )

    def close(self) -> None:
        """Release the bus. Safe to call repeatedly; a no-op by default."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
