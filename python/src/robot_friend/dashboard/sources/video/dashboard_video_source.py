from abc import ABC, abstractmethod

import numpy as np

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.dashboard.sources.video.dashboard_video_streams import VideoStreams


class DashboardVideoSource(DashboardDataSource, ABC):
    """Base contract for dashboard video producers.

    Implementations decide where frames come from; this class standardizes how they
    publish raw/annotated frames and metadata into the dashboard.
    """

    channel = "video"

    def __init__(
        self,
        streams: VideoStreams,
        *,
        raw_stream: str = "raw",
        annotated_stream: str = "annotated",
    ) -> None:
        self._streams = streams
        self._raw_stream = raw_stream
        self._annotated_stream = annotated_stream

    @abstractmethod
    def start(self, bus: Bus) -> None:
        ...

    def stop(self) -> None:
        """Stop background production when the implementation supports it."""

    def publish_raw(self, frame: np.ndarray) -> None:
        self.publish_frame(self._raw_stream, frame)

    def publish_annotated(self, frame: np.ndarray) -> None:
        self.publish_frame(self._annotated_stream, frame)

    def publish_frame(self, stream: str, frame: np.ndarray) -> None:
        self._streams.publish(stream, frame)

    def publish_jpeg(self, stream: str, data: bytes) -> None:
        self._streams.publish_jpeg(stream, data)
