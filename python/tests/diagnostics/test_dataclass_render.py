"""Browser-free unit tests for the dataclass → renderable adapter (the testable core
of Phase 4). Exercises the repo's real data objects, including the tricky
enum-whose-value-is-a-dataclass types."""
import json

import numpy as np

from robot_friend.dashboard.sources.dataclass import to_json, to_renderable, to_table
from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
from robot_friend.speech.keywords.keyword import DetectedSpeechKeyword, SpeechKeyword
from robot_friend.speech.transcript import Language, Transcript


def test_plain_dataclass():
    assert to_renderable(BoundingBox(1, 2, 3, 4)) == {"x1": 1, "y1": 2, "x2": 3, "y2": 4}


def test_scalar_enum_shows_name_and_value():
    assert to_renderable(Language.GERMAN) == "GERMAN (de)"


def test_dataclass_valued_enums_expand():
    assert to_renderable(DetectedObjectType.PERSON) == {"PERSON": {"name": "person", "coco_class_id": 0}}
    assert to_renderable(SpeechKeyword.YES) == {"YES": {"aliases_en": ["yes"], "aliases_de": ["ja"]}}


def test_nested_dataclass_with_enum_field():
    obj = DetectedObject(DetectedObjectType.PERSON, BoundingBox(1, 2, 3, 4), 0.97)
    assert to_renderable(obj) == {
        "detected_object_type": {"PERSON": {"name": "person", "coco_class_id": 0}},
        "bounding_box": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
        "confidence": 0.97,
    }


def test_detected_speech_keyword():
    d = DetectedSpeechKeyword(SpeechKeyword.YES, "yes")
    assert to_renderable(d) == {
        "keyword": {"YES": {"aliases_en": ["yes"], "aliases_de": ["ja"]}},
        "matched_alias": "yes",
    }


def test_transcript_custom_renderer_uses_raw_fields():
    t = Transcript(text="hey finch",
                   keywords=[DetectedSpeechKeyword(SpeechKeyword.YES, "yes")],
                   language=Language.ENGLISH, language_probability=0.881)
    r = to_renderable(t)
    assert r["text"] == "hey finch"
    assert r["language"] == "ENGLISH (en)"
    assert r["language_probability"] == 0.881
    assert r["keywords"][0]["matched_alias"] == "yes"


def test_transcript_with_none_fields():
    r = to_renderable(Transcript(text=None))
    assert r["text"] is None
    assert r["language"] is None
    assert r["keywords"] == []


def test_list_of_dataclasses():
    out = to_renderable([DetectedObject(DetectedObjectType.PERSON, BoundingBox(0, 0, 1, 1), 0.5)])
    assert isinstance(out, list) and out[0]["confidence"] == 0.5


def test_numpy_scalars_and_arrays_become_native():
    assert to_renderable(np.float32(0.5)) == 0.5
    assert to_renderable(np.int64(7)) == 7
    assert to_renderable(np.array([1, 2, 3])) == [1, 2, 3]


def test_to_json_round_trips():
    parsed = json.loads(to_json(Transcript(text="hi", language=Language.ENGLISH)))
    assert parsed["text"] == "hi" and parsed["language"] == "ENGLISH (en)"


def test_to_table_compacts_cells():
    columns, rows = to_table([DetectedObject(DetectedObjectType.PERSON, BoundingBox(1, 2, 3, 4), 0.9)])
    assert columns == ["detected_object_type", "bounding_box", "confidence"]
    # single-key enum dict -> just the member name (keeps the column narrow)
    assert rows[0]["detected_object_type"] == "PERSON"
    # other nested values -> compact JSON (no spaces)
    assert rows[0]["bounding_box"] == '{"x1":1,"y1":2,"x2":3,"y2":4}'
    assert rows[0]["confidence"] == 0.9
