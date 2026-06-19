"""Dashboard video transport and sources."""
from robot_friend.dashboard.sources.demo.demo_video_source import (
    SCENARIOS,
    DemoVideoSource,
)
from robot_friend.dashboard.sources.video.camera_video_source import CameraVideoSource
from robot_friend.dashboard.sources.video.dashboard_video_source import DashboardVideoSource
from robot_friend.dashboard.sources.video.dashboard_video_streams import VideoStreams
from robot_friend.resource_handler import get_dashboard_static_file

VIDEO_STREAM_HTML = get_dashboard_static_file("video-stream.html").read_text()

FakeVideoSource = DemoVideoSource
VideoSource = CameraVideoSource

__all__ = [
    "CameraVideoSource",
    "DashboardVideoSource",
    "DemoVideoSource",
    "FakeVideoSource",
    "SCENARIOS",
    "VIDEO_STREAM_HTML",
    "VideoSource",
    "VideoStreams",
]
