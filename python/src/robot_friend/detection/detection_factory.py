from robot_friend.detection.detector import Detector
from robot_friend.utils.get_current_host import is_pi_host


class DetectionFactory:

    @staticmethod
    def get_detector() -> Detector:
        if is_pi_host():
            from robot_friend.detection.backends.hailo.HailoDetector import HailoDetector
            return HailoDetector()
        else:
            from robot_friend.detection.backends.ultralytics.YOLODetector import YoloDetector, YOLOModel
            return YoloDetector(YOLOModel.YOLO_V8N)