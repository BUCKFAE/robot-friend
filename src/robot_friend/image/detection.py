from dataclasses import dataclass
from enum import Enum

@dataclass
class BoundingBox:
    """Axis-aligned box in pixel coordinates.

    Attributes:
        x1: Left edge.
        y1: Top edge.
        x2: Right edge.
        y2: Bottom edge.
    """
    x1: int
    y1: int
    x2: int
    y2: int

@dataclass
class DetectedObjectTypeConfig:
    name: str
    coco_class_id: int

class DetectedObjectType(Enum):
    """The object classes we recognize, each mapped to its COCO class id."""
    PERSON = DetectedObjectTypeConfig('person', 0)
    SPOON = DetectedObjectTypeConfig('spoon', 44)
    PHONE = DetectedObjectTypeConfig('cell_phone', 69)

    @classmethod
    def from_coco_class_id(cls, class_id: int) -> 'DetectedObjectType':
        """Maps a raw COCO class id to its detected object type.

        Args:
            class_id: The COCO class id reported by the detector.

        Returns:
            The matching object type.

        Raises:
            ValueError: If no object type maps to the given class id.
        """
        for object_type in DetectedObjectType:
            if object_type.value.coco_class_id == class_id:
                return object_type
        raise ValueError(f'Did not find object type with coco class {class_id}')

@dataclass
class DetectedObject:
    """A single object found in a frame.

    Attributes:
        detected_object_type: What was detected.
        bounding_box: Where it sits in the frame.
        confidence: The detector's confidence score in [0, 1].
    """
    detected_object_type: DetectedObjectType
    bounding_box: BoundingBox
    confidence: float
