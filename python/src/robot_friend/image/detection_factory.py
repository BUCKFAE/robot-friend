from robot_friend.image.detector import ImageDetector
from robot_friend.utils.get_current_host import is_pi_host


class DetectionFactory:

    @staticmethod
    def get_detector() -> ImageDetector:
        if is_pi_host():
            from robot_friend.image.backends.hailo.HailoDetector import HailoImageDetector
            return HailoImageDetector()
        else:
            from robot_friend.image.backends.ultralytics.YOLODetector import YoloImageDetector, YOLOModel
            return YoloImageDetector(YOLOModel.YOLO_V8N)