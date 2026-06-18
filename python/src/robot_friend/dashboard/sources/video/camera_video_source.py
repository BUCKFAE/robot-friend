"""Live camera + detector dashboard video source."""
from __future__ import annotations

import threading

import cv2

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.controls import DashboardControls
from robot_friend.dashboard.sources.video.dashboard_video_source import DashboardVideoSource
from robot_friend.dashboard.sources.video.dashboard_video_streams import VideoStreams
from robot_friend.utils.finch_logger import finch_logger

_BGR_GREEN = (161, 227, 166)


class CameraVideoSource(DashboardVideoSource):
    """Read the robot camera, run detection, and publish raw/annotated streams."""

    def __init__(
        self,
        streams: VideoStreams,
        controls: DashboardControls | None = None,
        *,
        raw_stream: str = "raw",
        annotated_stream: str = "annotated",
    ) -> None:
        super().__init__(
            streams, raw_stream=raw_stream, annotated_stream=annotated_stream
        )
        self._controls = controls
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, bus: Bus) -> None:
        self._thread = threading.Thread(
            target=self._run, args=(bus,), daemon=True, name="video-source"
        )
        self._thread.start()

    def _run(self, bus: Bus) -> None:
        import time

        from robot_friend.camera import open_camera
        from robot_friend.image.detection_factory import DetectionFactory

        detector = DetectionFactory.get_detector()
        active_index: int | None = None
        camera = None
        try:
            while not self._stop.is_set():
                wanted_index = self._controls.camera_index if self._controls else 0
                if camera is None or wanted_index != active_index:
                    if camera is not None:
                        camera.close()
                    active_index = wanted_index
                    finch_logger.info("opening camera device %s", active_index)
                    try:
                        camera = open_camera(active_index)
                    except Exception as exc:
                        finch_logger.warning(
                            "could not open camera device %s: %s", active_index, exc
                        )
                        camera = None
                        self._stop.wait(1.0)
                        continue

                frame = camera.read()
                if frame is None:
                    finch_logger.warning("camera device %s returned no frame", active_index)
                    camera.close()
                    camera = None
                    self._stop.wait(1.0)
                    continue

                started = time.monotonic()
                boxes = detector.detect(frame)
                detect_ms = (time.monotonic() - started) * 1000

                self.publish_raw(frame)

                annotated = frame.copy()
                for box in boxes:
                    bb = box.bounding_box
                    cv2.rectangle(
                        annotated, (bb.x1, bb.y1), (bb.x2, bb.y2), _BGR_GREEN, 2
                    )
                self.publish_annotated(annotated)

                bus.publish("perf.detect_ms", round(detect_ms, 1))
                bus.publish("perf.fps", round(1000 / detect_ms, 1) if detect_ms else 0.0)
                bus.publish("detections", list(boxes))
        finally:
            if camera is not None:
                camera.close()

    def stop(self) -> None:
        self._stop.set()
