"""TelemetryStore is the producer side of the wire contract: worker threads write the
latest values and the HTTP handler serializes a snapshot on demand."""
import json

from robot_friend.audio.transcript import Language, Transcript
from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
from robot_friend.telemetry.store import TelemetryStore


def test_empty_store_serializes_to_a_valid_snapshot():
    snapshot = json.loads(TelemetryStore().to_json())
    assert snapshot["detections"] == []
    assert snapshot["transcript"] is None
    assert snapshot["perf"] == {"fps": 0.0, "detect_ms": 0.0}


def test_set_vision_is_reflected_in_the_snapshot():
    store = TelemetryStore()
    store.set_vision(
        [DetectedObject(DetectedObjectType.PERSON, BoundingBox(1, 2, 3, 4), 0.9)],
        fps=24.0,
        detect_ms=41.7,
    )
    snapshot = json.loads(store.to_json())
    assert snapshot["perf"] == {"fps": 24.0, "detect_ms": 41.7}
    assert snapshot["detections"] == [
        {"type": "PERSON", "box": [1, 2, 3, 4], "confidence": 0.9}
    ]
    assert snapshot["ts"] > 0


def test_set_transcript_is_reflected_in_the_snapshot():
    store = TelemetryStore()
    store.set_transcript(Transcript(text="hi", language=Language.ENGLISH))
    snapshot = json.loads(store.to_json())
    assert snapshot["transcript"]["text"] == "hi"
    assert snapshot["transcript"]["language"] == "en"
