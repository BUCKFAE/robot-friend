from abc import ABC, abstractmethod

import numpy as np

from robot_friend.utils.get_current_host import is_pi_host


class Camera(ABC):
    """A source of BGR uint8 frames (OpenCV convention)."""

    @abstractmethod
    def read(self) -> np.ndarray | None:
        """Return the next frame, or None if the source stopped."""

    @property
    @abstractmethod
    def width(self) -> int:
        """Frame width in pixels (the x-extent of frames from ``read``)."""

    @property
    @abstractmethod
    def height(self) -> int:
        """Frame height in pixels (the y-extent of frames from ``read``)."""

    @abstractmethod
    def close(self) -> None:
        pass

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class OpenCVCamera(Camera):
    """USB webcam (or anything V4L2) via cv2.VideoCapture."""

    def __init__(self, index: int = 0):
        import cv2

        self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open camera index {index}")
        # Cache the negotiated capture resolution; it does not change at runtime.
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def read(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        return frame if ok else None

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def close(self) -> None:
        self._cap.release()


class PiCamera(Camera):
    """Raspberry Pi camera module via picamera2 (apt-installed, Pi-only)."""

    def __init__(self, size: tuple[int, int] = (1280, 960)):
        from picamera2 import Picamera2  # only importable on the Pi

        self._picam = Picamera2()
        # picamera2 format names describe the byte order backwards: 'RGB888'
        # yields BGR arrays, which is what the cv2 pipeline expects.
        config = self._picam.create_video_configuration(main={"format": "RGB888", "size": size})
        self._picam.configure(config)
        self._picam.start()
        self._width, self._height = size

    def read(self) -> np.ndarray | None:
        return self._picam.capture_array()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def close(self) -> None:
        self._picam.stop()
        self._picam.close()


def open_camera(index: int = 0) -> Camera:
    if is_pi_host():
        return PiCamera()
    else:
        return OpenCVCamera(index)
