from functools import cache
from pathlib import Path

# The Pi's firmware exposes a device-tree model string here, e.g.
# "Raspberry Pi 5 Model B Rev 1.0". The file is absent on dev machines.
_DEVICE_TREE_MODEL = Path("/proc/device-tree/model")


@cache
def is_pi_host() -> bool:
    """Returns true if the current host is a Raspberry Pi.

    Reads the device-tree model string the Pi's firmware publishes; on non-Pi
    hosts that file does not exist, so this safely returns False. The result is
    cached since the host can't change while the process runs.

    Returns:
        True when running on Raspberry Pi hardware, otherwise False.
    """
    try:
        model = _DEVICE_TREE_MODEL.read_bytes()
    except OSError:
        return False
    return b"raspberry pi" in model.lower()
