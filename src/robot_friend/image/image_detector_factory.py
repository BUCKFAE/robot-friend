from robot_friend.image.image_detector import ImageDetector
from robot_friend.utils.get_current_host import is_pi_host


class ImageDetectorFactory:

    @staticmethod
    def get_image_detector() -> ImageDetector:
        if is_pi_host():
            from robot_friend.image.backends.hailo.hailo_detector import HailoImageDetector
            return HailoImageDetector()
        else:
            from robot_friend.image.backends.ultralytics.yolo_detector import YoloImageDetector, YOLOModel
            return YoloImageDetector(YOLOModel.YOLO_V8N)