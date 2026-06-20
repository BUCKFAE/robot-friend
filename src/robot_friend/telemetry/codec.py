"""JSON wire format for robot telemetry, shared by the producer and the dashboard.

The repo's domain objects (:class:`DetectedObject`, :class:`Transcript`) are plain
dataclasses with nested enums. The dashboard's ``to_renderable`` is built for *display*
and is lossy for round-trips (enums collapse to ``{NAME: {...}}``), so this module
defines explicit, typed (de)serializers instead: the producer encodes its latest
telemetry to JSON, and the dashboard decodes it back into the *same* dataclasses, so
panels receive identical objects whether the data is live or demo.

Import-light (only the pure-Python dataclass/enum definitions) so ``robot_friend.main``
can serialize telemetry without importing the dashboard or its web-stack deps.
"""
from __future__ import annotations

from typing import Any

from robot_friend.audio.keywords.keyword import DetectedSpeechKeyword, SpeechKeyword
from robot_friend.audio.transcript import Language, Transcript
from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType


def detection_to_wire(detection: DetectedObject) -> dict[str, Any]:
    """Encode a :class:`DetectedObject` as a JSON-safe dict."""
    box = detection.bounding_box
    return {
        "type": detection.detected_object_type.name,
        "box": [box.x1, box.y1, box.x2, box.y2],
        "confidence": detection.confidence,
    }


def detection_from_wire(data: dict[str, Any]) -> DetectedObject:
    """Rebuild a :class:`DetectedObject` from :func:`detection_to_wire` output."""
    x1, y1, x2, y2 = data["box"]
    return DetectedObject(
        DetectedObjectType[data["type"]],
        BoundingBox(int(x1), int(y1), int(x2), int(y2)),
        float(data["confidence"]),
    )


def _keyword_to_wire(keyword: DetectedSpeechKeyword) -> dict[str, str]:
    return {"keyword": keyword.keyword.name, "matched_alias": keyword.matched_alias}


def _keyword_from_wire(data: dict[str, str]) -> DetectedSpeechKeyword:
    return DetectedSpeechKeyword(SpeechKeyword[data["keyword"]], data["matched_alias"])


def transcript_to_wire(transcript: Transcript) -> dict[str, Any]:
    """Encode a :class:`Transcript` as a JSON-safe dict."""
    return {
        "text": transcript.text,
        "language": transcript.language.value if transcript.language else None,
        "language_probability": transcript.language_probability,
        "keywords": [_keyword_to_wire(k) for k in (transcript.keywords or [])],
    }


def transcript_from_wire(data: dict[str, Any]) -> Transcript:
    """Rebuild a :class:`Transcript` from :func:`transcript_to_wire` output."""
    language = Language.from_code(data["language"]) if data.get("language") else None
    return Transcript(
        text=data.get("text"),
        keywords=[_keyword_from_wire(k) for k in data.get("keywords") or []],
        language=language,
        language_probability=data.get("language_probability", 0.0),
    )
