"""Real I2C over ``smbus3`` — the only place a raw ``OSError`` becomes one of ours."""
from smbus3 import SMBus

from robot_friend.exceptions.i2c_exception import I2cTransferException
from robot_friend.exceptions.missing_hardware_exception import (
    MissingI2cBusException,
    MissingI2cDeviceException,
)
from robot_friend.i2c.i2c_device import I2cDevice


class SmbusI2cDevice(I2cDevice):
    """A device on a real bus, opened through ``/dev/i2c-<bus>``."""

    def __init__(self, *, address: int, bus: int = 1) -> None:
        """
        Raises:
            MissingI2cBusException: If the bus itself cannot be opened.
        """
        super().__init__(address=address, bus=bus)
        try:
            self._bus = SMBus(bus)
        except OSError as exc:
            raise MissingI2cBusException(
                f"could not open I2C bus {bus} (is I2C enabled?)"
            ) from exc

    def read_byte(self, register: int) -> int:
        try:
            return self._bus.read_byte_data(self._address, register)
        except OSError as exc:
            raise self._transfer_failed("read", register) from exc

    def read_block(self, register: int, length: int) -> list[int]:
        try:
            return self._bus.read_i2c_block_data(self._address, register, length)
        except OSError as exc:
            raise self._transfer_failed("block read", register) from exc

    def write_byte(self, register: int, value: int) -> None:
        try:
            self._bus.write_byte_data(self._address, register, value & 0xFF)
        except OSError as exc:
            raise self._transfer_failed("write", register) from exc

    def write_block(self, register: int, values: list[int]) -> None:
        try:
            self._bus.write_i2c_block_data(self._address, register, values)
        except OSError as exc:
            raise self._transfer_failed("block write", register) from exc

    def probe(self) -> None:
        # An address-only read: the device ACKs its address and nothing is written,
        # which is how i2cdetect looks for a board.
        try:
            self._bus.read_byte(self._address)
        except OSError as exc:
            raise MissingI2cDeviceException(
                f"nothing answering at {self._address:#04x} on I2C bus {self._bus_number}"
            ) from exc

    def close(self) -> None:
        self._bus.close()

    def _transfer_failed(self, what: str, register: int) -> I2cTransferException:
        return I2cTransferException(
            f"{what} of register {register:#04x} failed on device {self._address:#04x} "
            f"of I2C bus {self._bus_number}"
        )
