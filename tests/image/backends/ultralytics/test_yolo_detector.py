from robot_friend.image.backends.ultralytics.yolo_detector import YOLOModel


def test_yolo_name():
    assert YOLOModel.YOLO_V8N.value == 'yolov8n.pt'
