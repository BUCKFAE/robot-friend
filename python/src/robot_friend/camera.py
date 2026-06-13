from abc import ABC, abstractmethod

import numpy as np


class Camera(ABC):
    """A source of BGR uint8 frames (OpenCV convention)."""

    @abstractmethod
    def read(self) -> np.ndarray | None:
        """Return the next frame, or None if the source stopped."""

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

    def read(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        return frame if ok else None

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

    def read(self) -> np.ndarray | None:
        return self._picam.capture_array()

    def close(self) -> None:
        self._picam.stop()
        self._picam.close()


def open_camera(kind: str = "auto", index: int = 0) -> Camera:
    if kind == "picamera":
        return PiCamera()
    if kind == "opencv":
        return OpenCVCamera(index)
    try:
        return PiCamera()
    except ImportError:
        return OpenCVCamera(index)
