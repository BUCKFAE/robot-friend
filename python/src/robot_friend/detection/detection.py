from dataclasses import dataclass
from enum import Enum

@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

@dataclass
class DetectedObjectTypeConfig:
    name: str
    coco_class_id: int

class DetectedObjectType(Enum):
    """
    Enum for everything we can detect
    """
    PERSON = DetectedObjectTypeConfig('person', 0)

@dataclass
class DetectedObject:
    detected_object_type: DetectedObjectType
    bounding_box: BoundingBox
    confidence: float
