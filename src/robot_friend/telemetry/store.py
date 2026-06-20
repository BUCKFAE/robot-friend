"""Thread-safe latest-value store for robot telemetry, serialized on demand.

Producer threads (the vision loop, the audio loop) write the newest detections, perf
numbers and transcript with cheap lock-guarded assignments. The HTTP handler calls
:meth:`TelemetryStore.to_json` only when a client polls ``GET /telemetry.json``, so an
unattached robot pays nothing beyond those writes — serialization happens just for
whoever is actually watching.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from robot_friend.audio.transcript import Transcript
from robot_friend.image.detection import DetectedObject
from robot_friend.telemetry.codec import detection_to_wire, transcript_to_wire


class TelemetryStore:
    """Latest robot telemetry; written by worker threads, read by the HTTP handler.

    Attributes:
        (private) the most recent detections, perf timing, transcript and the wall-clock
        time of the last update (so the dashboard can reason about staleness).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._detections: list[DetectedObject] = []
        self._fps: float = 0.0
        self._detect_ms: float = 0.0
        self._transcript: Transcript | None = None
        self._updated_at: float = 0.0

    def set_vision(
        self, detections: list[DetectedObject], fps: float, detect_ms: float
    ) -> None:
        """Record the latest detections and timing from the vision loop."""
        with self._lock:
            self._detections = detections
            self._fps = fps
            self._detect_ms = detect_ms
            self._updated_at = time.time()

    def set_transcript(self, transcript: Transcript) -> None:
        """Record the latest speech transcript from the audio loop."""
        with self._lock:
            self._transcript = transcript
            self._updated_at = time.time()

    def snapshot(self) -> dict[str, Any]:
        """Return the current telemetry as a JSON-safe dict (the wire format)."""
        with self._lock:
            transcript = self._transcript
            return {
                "ts": self._updated_at,
                "perf": {"fps": self._fps, "detect_ms": self._detect_ms},
                "detections": [detection_to_wire(d) for d in self._detections],
                "transcript": transcript_to_wire(transcript) if transcript else None,
            }

    def to_json(self) -> bytes:
        """Serialize the current snapshot to UTF-8 JSON bytes for the HTTP handler."""
        return json.dumps(self.snapshot()).encode("utf-8")
