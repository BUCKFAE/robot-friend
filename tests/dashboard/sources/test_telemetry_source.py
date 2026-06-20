"""apply_telemetry is the dashboard side of the wire contract: it must fan a decoded
snapshot onto the same Bus channels the panels read, and tolerate an empty robot."""
from robot_friend.audio.transcript import Transcript
from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.dataclass import DETECTIONS_CHANNEL, TRANSCRIPT_CHANNEL
from robot_friend.dashboard.sources.telemetry_source import (
    PERF_DETECT_MS_CHANNEL,
    PERF_FPS_CHANNEL,
    apply_telemetry,
)
from robot_friend.image.detection import DetectedObject


def test_apply_telemetry_publishes_every_channel():
    bus = Bus()
    apply_telemetry(
        bus,
        {
            "perf": {"fps": 24.0, "detect_ms": 41.7},
            "detections": [{"type": "PERSON", "box": [1, 2, 3, 4], "confidence": 0.9}],
            "transcript": {
                "text": "hi",
                "language": "en",
                "language_probability": 0.8,
                "keywords": [],
            },
        },
    )
    assert bus.latest(PERF_FPS_CHANNEL) == 24.0
    assert bus.latest(PERF_DETECT_MS_CHANNEL) == 41.7
    detections = bus.latest(DETECTIONS_CHANNEL)
    assert len(detections) == 1 and isinstance(detections[0], DetectedObject)
    assert isinstance(bus.latest(TRANSCRIPT_CHANNEL), Transcript)


def test_apply_telemetry_tolerates_an_idle_robot():
    bus = Bus()
    apply_telemetry(
        bus,
        {"ts": 0.0, "perf": {"fps": 0.0, "detect_ms": 0.0}, "detections": [], "transcript": None},
    )
    assert bus.latest(DETECTIONS_CHANNEL) == []
    assert bus.latest(TRANSCRIPT_CHANNEL) is None  # nothing to publish
