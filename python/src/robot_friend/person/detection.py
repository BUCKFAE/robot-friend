from dataclasses import dataclass
from enum import Enum


class DetectedObjectType(Enum):
    PERSON = 'person'

@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

@dataclass
class DetectedObject:
    detected_object_type: DetectedObjectType
    bounding_box: BoundingBox
    confidence: float


