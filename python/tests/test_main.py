from robot_friend.person.person_recognizer import YOLOModel


def test_yolo_name():
    assert YOLOModel.YOLO_V8N.value == 'yolov8n.pt'
