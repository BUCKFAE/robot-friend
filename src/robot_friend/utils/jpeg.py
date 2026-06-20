"""Dependency-light JPEG encoding shared by the robot server and the dashboard.

Lives outside the dashboard package (which pulls in the web stack) so the lean
detection process ``robot_friend.main`` can encode frames without importing FastAPI.
"""
from __future__ import annotations

import cv2
import numpy as np

JPEG_QUALITY = 80


def encode_jpeg(frame: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    """Encode a BGR uint8 frame as JPEG bytes; returns ``b""`` if encoding fails."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""
