"""Deterministic synthetic dashboard video for demos and visual tests."""
from __future__ import annotations

import threading
from enum import Enum

import cv2
import numpy as np

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.video.dashboard_video_source import DashboardVideoSource
from robot_friend.dashboard.sources.video.dashboard_video_streams import VideoStreams, encode_jpeg

SCENARIOS = ("nominal", "stress_text", "empty", "dense")
_BGR_GREEN = (161, 227, 166)
_BGR_TEXT = (244, 214, 205)


class DemoVideoSource(DashboardVideoSource):
    """Publish deterministic raw/annotated frames for a named demo scenario."""

    def __init__(
        self,
        streams: VideoStreams,
        scenario: str | Enum | None = "nominal",
        *,
        raw_stream: str = "raw",
        annotated_stream: str = "annotated",
    ) -> None:
        super().__init__(
            streams, raw_stream=raw_stream, annotated_stream=annotated_stream
        )
        self._scenario = _scenario_name(scenario)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, bus: Bus) -> None:
        if self._scenario == "empty":
            return

        raw_jpeg = encode_jpeg(_demo_frame(self._scenario, annotated=False))
        annotated_jpeg = encode_jpeg(_demo_frame(self._scenario, annotated=True))
        self.publish_jpeg(self._raw_stream, raw_jpeg)
        self.publish_jpeg(self._annotated_stream, annotated_jpeg)
        bus.publish("perf.fps", 24.0)
        bus.publish("perf.detect_ms", 41.7)

        def keepalive() -> None:
            while not self._stop.wait(1.0):
                self.publish_jpeg(self._raw_stream, raw_jpeg)
                self.publish_jpeg(self._annotated_stream, annotated_jpeg)

        self._thread = threading.Thread(target=keepalive, daemon=True, name="fake-video")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


def _scenario_name(scenario: str | Enum | None) -> str:
    if scenario is None:
        return "nominal"
    if isinstance(scenario, str):
        return scenario if scenario in SCENARIOS else "nominal"
    if scenario.name == "DEMO_SIMPLE":
        return "nominal"
    return scenario.name.lower()


def _demo_frame(
    scenario: str, *, annotated: bool, size: tuple[int, int] = (480, 640)
) -> np.ndarray:
    h, w = size
    top = np.array([68, 50, 49], dtype=np.float32)
    bottom = np.array([27, 17, 17], dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    frame = (top * (1 - ramp) + bottom * ramp).astype(np.uint8)
    frame = np.repeat(frame, w, axis=1)

    cv2.circle(frame, (w // 2, h // 2), min(h, w) // 5, _BGR_GREEN, 2, cv2.LINE_AA)
    label = "ANNOTATED" if annotated else "RAW"
    cv2.putText(
        frame,
        f"DEMO {label} [{scenario}]",
        (16, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        _BGR_TEXT,
        2,
        cv2.LINE_AA,
    )
    if annotated:
        x1, y1, x2, y2 = w // 3, h // 4, 2 * w // 3, 9 * h // 10
        cv2.rectangle(frame, (x1, y1), (x2, y2), _BGR_GREEN, 2)
        cv2.putText(
            frame,
            "person 0.97",
            (x1, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            _BGR_GREEN,
            2,
            cv2.LINE_AA,
        )
    return frame
