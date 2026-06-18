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
    SPOON = DetectedObjectTypeConfig('spoon', 44)
    PHONE = DetectedObjectTypeConfig('cell_phone', 69)

    @classmethod
    def from_coco_class_id(cls, class_id: int) -> 'DetectedObjectType':
        for object_type in DetectedObjectType:
            if object_type.value.coco_class_id == class_id:
                return object_type
        raise ValueError(f'Did not find object type with coco class {class_id}')

@dataclass
class DetectedObject:
    detected_object_type: DetectedObjectType
    bounding_box: BoundingBox
    confidence: float
