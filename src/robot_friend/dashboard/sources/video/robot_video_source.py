"""Dashboard video source that proxies the robot's MJPEG streams.

The robot (``robot_friend.main``) serves raw + annotated MJPEG on its
:class:`~robot_friend.robot_server.RobotServer`; this source reads those streams and
republishes each JPEG into the dashboard's own :class:`VideoStreams` transport. That
keeps the existing ``VideoPanel`` / WebSocket pipeline unchanged and means the browser
only ever talks to the dashboard (single origin). Each stream runs on its own daemon
thread that reconnects when the robot restarts.
"""
from __future__ import annotations

import threading
import urllib.error
import urllib.request

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.video.dashboard_video_source import DashboardVideoSource
from robot_friend.dashboard.sources.video.dashboard_video_streams import VideoStreams
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.mjpeg import iter_mjpeg_frames

_RECONNECT_DELAY = 1.0


class RobotVideoSource(DashboardVideoSource):
    """Proxy the robot's named MJPEG streams into the dashboard's video transport."""

    def __init__(
        self,
        streams: VideoStreams,
        base_url: str,
        *,
        raw_stream: str = "raw",
        annotated_stream: str = "annotated",
    ) -> None:
        super().__init__(streams, raw_stream=raw_stream, annotated_stream=annotated_stream)
        self._base_url = base_url.rstrip("/")
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self, bus: Bus) -> None:
        for stream in (self._raw_stream, self._annotated_stream):
            thread = threading.Thread(
                target=self._proxy, args=(stream,), daemon=True, name=f"robot-video-{stream}"
            )
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop.set()

    def _proxy(self, stream: str) -> None:
        url = f"{self._base_url}/video/{stream}"
        unreachable = False
        while not self._stop.is_set():
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    unreachable = False
                    for jpeg in iter_mjpeg_frames(response):
                        if self._stop.is_set():
                            break
                        self.publish_jpeg(stream, jpeg)
            except (urllib.error.URLError, OSError) as exc:
                if not unreachable:
                    finch_logger.info("robot video unreachable at %s (%s); retrying", url, exc)
                    unreachable = True
            self._stop.wait(_RECONNECT_DELAY)
