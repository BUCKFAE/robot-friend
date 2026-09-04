"""In-memory I2C device: register state plus the transcript of what a driver did to it."""
from dataclasses import dataclass, field

from robot_friend.exceptions.i2c_exception import I2cTransferException
from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException
from robot_friend.i2c.i2c_device import I2cDevice


@dataclass(frozen=True, slots=True)
class I2cCall:
    """One transfer a driver made, in order.

    Attributes:
        kind: ``probe``, ``read``, ``read_block``, ``write`` or ``write_block``.
        register: The register touched, or None for a probe.
        values: Bytes written, or the length asked for by a block read.
    """
    kind: str
    register: int | None = None
    values: tuple[int, ...] = field(default_factory=tuple)


class FakeI2cDevice(I2cDevice):
    """Answers from a register dict and records every call, so drivers are testable."""

    def __init__(
        self,
        *,
        address: int = 0x00,
        bus: int = 1,
        registers: dict[int, int] | None = None,
        answering: bool = True,
    ) -> None:
        """
        Args:
            address: The address the device pretends to sit at.
            bus: The bus number it pretends to sit on.
            registers: Starting register contents; unset registers read as ``0x00``.
            answering: When False every transfer fails, standing in for an absent board.
        """
        super().__init__(address=address, bus=bus)
        self.registers = dict(registers or {})
        self.calls: list[I2cCall] = []
        self._answering = answering

    def set_answering(self, answering: bool) -> None:
        """Make the device start or stop responding, e.g. to simulate a wire falling out."""
        self._answering = answering

    def read_byte(self, register: int) -> int:
        self._record(I2cCall("read", register))
        return self.registers.get(register, 0x00)

    def read_block(self, register: int, length: int) -> list[int]:
        self._record(I2cCall("read_block", register, (length,)))
        return [self.registers.get(register + offset, 0x00) for offset in range(length)]

    def write_byte(self, register: int, value: int) -> None:
        self._record(I2cCall("write", register, (value & 0xFF,)))
        self.registers[register] = value & 0xFF

    def write_block(self, register: int, values: list[int]) -> None:
        self._record(I2cCall("write_block", register, tuple(values)))
        for offset, value in enumerate(values):
            self.registers[register + offset] = value & 0xFF

    def probe(self) -> None:
        self.calls.append(I2cCall("probe"))
        if not self._answering:
            raise MissingI2cDeviceException(
                f"nothing answering at {self._address:#04x} on I2C bus {self._bus_number}"
            )

    def close(self) -> None:
        self.calls.append(I2cCall("close"))

    def _record(self, call: I2cCall) -> None:
        self.calls.append(call)
        if not self._answering:
            raise I2cTransferException(
                f"{call.kind} failed on device {self._address:#04x} "
                f"of I2C bus {self._bus_number} (not answering)"
            )
