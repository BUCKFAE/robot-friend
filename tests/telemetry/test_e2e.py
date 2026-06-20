"""End-to-end: vision telemetry must flow from the robot's server to the dashboard bus
over a real socket — the core of the telemetry-attach architecture. Import-light (no web
stack), so it runs in the default suite."""
import time

from robot_friend.audio.transcript import Language, Transcript
from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.sources.dataclass import DETECTIONS_CHANNEL, TRANSCRIPT_CHANNEL
from robot_friend.dashboard.sources.telemetry_source import (
    PERF_FPS_CHANNEL,
    TelemetrySource,
)
from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
from robot_friend.robot_server import RobotServer
from robot_friend.telemetry.store import TelemetryStore


def test_vision_and_speech_telemetry_flow_from_robot_to_bus():
    store = TelemetryStore()
    store.set_vision(
        [DetectedObject(DetectedObjectType.PERSON, BoundingBox(1, 2, 3, 4), 0.9)],
        fps=24.0,
        detect_ms=41.7,
    )
    store.set_transcript(Transcript(text="hey finch", language=Language.ENGLISH))
    server = RobotServer(0)
    server.on_get("/telemetry.json", lambda _query: store.to_json())
    bus = Bus()
    source = TelemetrySource(f"http://127.0.0.1:{server.port}", interval=0.02)
    source.start(bus)
    try:
        deadline = time.monotonic() + 3.0
        while bus.latest(DETECTIONS_CHANNEL) is None and time.monotonic() < deadline:
            time.sleep(0.02)
        detections = bus.latest(DETECTIONS_CHANNEL)
        assert detections is not None and len(detections) == 1
        assert detections[0].detected_object_type is DetectedObjectType.PERSON
        assert bus.latest(PERF_FPS_CHANNEL) == 24.0
        # detections and transcript arrive in the same snapshot/poll.
        transcript = bus.latest(TRANSCRIPT_CHANNEL)
        assert transcript is not None and transcript.text == "hey finch"
    finally:
        source.stop()
        server.shutdown()
