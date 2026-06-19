"""Generic dataclass → renderable adapter (dashboard feature #6, "DTO viz").

The repo's data objects are plain ``@dataclass`` instances, but they nest in ways
``dataclasses.asdict`` mishandles: fields hold **enums whose ``.value`` is itself a
dataclass** (``DetectedObjectType`` → ``DetectedObjectTypeConfig``, ``SpeechKeyword``
→ ``SpeechKeywordConfig``), scalar enums (``Language`` = ``'de'``), nested dataclasses
and optional ``None`` fields. :func:`to_renderable` walks the object into a JSON-safe
tree handling all of those, with a per-type **custom-renderer registry** (so e.g.
``Transcript`` can surface its own ``as_log_line()``). :func:`to_table` flattens a list
of such objects into ``(columns, rows)`` for a table.

This module is import-light (only the pure-Python dataclass/enum definitions), so it
loads without the ``yolo``/``audio`` backend extras.
"""
from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from enum import Enum
from typing import Any

import numpy as np

#: Exact-type custom renderers, consulted before generic handling.
_RENDERERS: dict[type, Callable[[Any], Any]] = {}


def register_renderer(target: type) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
    """Register a custom ``obj -> renderable`` function for an exact type."""
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        _RENDERERS[target] = func
        return func
    return decorator


def to_renderable(obj: Any, *, _depth: int = 0, _max_depth: int = 12) -> Any:
    """Convert ``obj`` into a JSON-safe tree of dicts/lists/primitives for display."""
    renderer = _RENDERERS.get(type(obj))
    if renderer is not None:
        return renderer(obj)

    if obj is None:
        return obj
    if isinstance(obj, np.generic):  # numpy scalar -> native python (covers np.float64 etc.)
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (str, bool, int, float)):
        return obj
    if _depth >= _max_depth:
        return repr(obj)

    if isinstance(obj, Enum):
        value = obj.value
        # Config-style enums carry a dataclass/collection value worth expanding.
        if dataclasses.is_dataclass(value) or isinstance(value, (list, tuple, set, dict, Enum)):
            return {obj.name: to_renderable(value, _depth=_depth + 1, _max_depth=_max_depth)}
        return f"{obj.name} ({value})"

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_renderable(getattr(obj, f.name), _depth=_depth + 1, _max_depth=_max_depth)
                for f in dataclasses.fields(obj)}

    if isinstance(obj, (list, tuple, set)):
        return [to_renderable(x, _depth=_depth + 1, _max_depth=_max_depth) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_renderable(v, _depth=_depth + 1, _max_depth=_max_depth) for k, v in obj.items()}

    return repr(obj)


def to_json(obj: Any) -> str:
    """Pretty JSON for the dataclass panel."""
    return json.dumps(to_renderable(obj), indent=2, ensure_ascii=False)


def _cell(value: Any) -> Any:
    """Render one table cell compactly so nested values don't blow out column width."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Enums render as {NAME: {...}}; in a table just show the member name.
    if isinstance(value, dict) and len(value) == 1:
        (key, inner), = value.items()
        if isinstance(inner, (dict, list)):
            return key
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def to_table(items: list[Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Flatten a list of objects into ``(columns, rows)`` with compact cells, so any
    dataclass list renders in a table without runaway column widths."""
    rows: list[dict[str, Any]] = []
    for item in items:
        rendered = to_renderable(item)
        if not isinstance(rendered, dict):
            rendered = {"value": rendered}
        rows.append({key: _cell(value) for key, value in rendered.items()})
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns, rows


# --- custom renderer: respect Transcript.as_log_line() -----------------------------
# Imported here (not in the core path) so the registry is populated on import. These
# are pure-Python dataclasses, so this stays free of the heavy backend deps.
from robot_friend.audio.transcript import Transcript  # noqa: E402


@register_renderer(Transcript)
def _render_transcript(transcript: Transcript) -> dict[str, Any]:
    return {
        "text": transcript.text,
        "language": to_renderable(transcript.language),
        "language_probability": round(transcript.language_probability, 4),
        "keywords": [to_renderable(k) for k in (transcript.keywords or [])],
    }


# --- demo source -------------------------------------------------------------------
from robot_friend.dashboard.bus import Bus  # noqa: E402
from robot_friend.dashboard.sources.data_source import DashboardDataSource  # noqa: E402

#: Bus channels the dataclass / table panels read (and the demo source feeds).
TRANSCRIPT_CHANNEL = "audio.transcript"
DETECTIONS_CHANNEL = "detections"


def _sample_transcript(scenario: str) -> Transcript:
    from robot_friend.audio.keywords.keyword import DetectedSpeechKeyword, SpeechKeyword
    from robot_friend.audio.transcript import Language
    if scenario == "stress_text":
        return Transcript(
            text="ja genau " * 10 + "— äöü ß 你好 こんにちは 🤖",
            keywords=[DetectedSpeechKeyword(SpeechKeyword.YES, "ja"),
                      DetectedSpeechKeyword(SpeechKeyword.NO, "nein")],
            language=Language.GERMAN, language_probability=0.8123)
    return Transcript(text="hey finch",
                      keywords=[DetectedSpeechKeyword(SpeechKeyword.YES, "yes")],
                      language=Language.ENGLISH, language_probability=0.88)


def _sample_detections(scenario: str) -> list[Any]:
    from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
    count = 12 if scenario == "dense" else (5 if scenario == "stress_text" else 2)
    return [DetectedObject(DetectedObjectType.PERSON,
                           BoundingBox(10 + i * 7, 20 + i * 5, 130 + i * 7, 250 + i * 5),
                           round(0.99 - i * 0.05, 2)) for i in range(count)]


class FakeDataclassSource(DashboardDataSource):
    """Demo source: publish a sample ``Transcript`` and a list of ``DetectedObject``s
    so the dataclass + table panels have deterministic content. The ``empty`` scenario
    publishes nothing, so those panels show their placeholders."""

    channel = TRANSCRIPT_CHANNEL

    def __init__(self, scenario: str = "nominal") -> None:
        self._scenario = scenario

    def start(self, bus: Bus) -> None:
        if self._scenario == "empty":
            return
        bus.publish(TRANSCRIPT_CHANNEL, _sample_transcript(self._scenario))
        bus.publish(DETECTIONS_CHANNEL, _sample_detections(self._scenario))
