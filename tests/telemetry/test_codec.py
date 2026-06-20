"""The telemetry wire codec must round-trip the domain dataclasses through JSON so the
dashboard rebuilds the exact objects its panels expect."""
import json

from robot_friend.audio.keywords.keyword import DetectedSpeechKeyword, SpeechKeyword
from robot_friend.audio.transcript import Language, Transcript
from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
from robot_friend.telemetry.codec import (
    detection_from_wire,
    detection_to_wire,
    transcript_from_wire,
    transcript_to_wire,
)


def _through_json(value: dict) -> dict:
    """Force the value across the real JSON boundary, not just the dict transform."""
    return json.loads(json.dumps(value))


def test_detection_round_trips():
    detection = DetectedObject(
        DetectedObjectType.PERSON, BoundingBox(10, 20, 130, 250), 0.97
    )
    assert detection_from_wire(_through_json(detection_to_wire(detection))) == detection


def test_transcript_round_trips():
    transcript = Transcript(
        text="hey finch",
        keywords=[DetectedSpeechKeyword(SpeechKeyword.YES, "ja")],
        language=Language.GERMAN,
        language_probability=0.81,
    )
    assert transcript_from_wire(_through_json(transcript_to_wire(transcript))) == transcript


def test_transcript_without_language_or_keywords():
    back = transcript_from_wire(_through_json(transcript_to_wire(Transcript(text=None))))
    assert back.text is None
    assert back.language is None
    assert back.keywords == []
