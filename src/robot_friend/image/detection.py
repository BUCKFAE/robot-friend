from dataclasses import dataclass
from enum import Enum

@dataclass
class BoundingBox:
    """Axis-aligned box in image pixel coordinates.

    Coordinates follow the OpenCV/NumPy image convention: the origin is the
    top-left corner of the frame, +x grows rightward and +y grows *downward*.
    Values are absolute pixels in the source frame's resolution (not
    normalized), so ``x2 >= x1`` and ``y2 >= y1`` always hold.

    Note: this is the image frame, distinct from the robot's aiming frame
    (see ``robot_friend.utils.coordinates.coordinate.Coordinate``, which is
    center-origin and y-up). Use ``bounding_box_to_coordinate`` to convert;
    do not mix the two.

    Attributes:
        x1: Left edge, in pixels from the left of the frame.
        y1: Top edge, in pixels from the top of the frame.
        x2: Right edge, in pixels from the left of the frame.
        y2: Bottom edge, in pixels from the top of the frame.
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
    SPOON = DetectedObjectTypeConfig('spoon', 42)
    CHAIR = DetectedObjectTypeConfig('chair', 56)
    PHONE = DetectedObjectTypeConfig('cell_phone', 67)

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
