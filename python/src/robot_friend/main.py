import sys

import cv2

from robot_friend.detection.backends.ultralytics.YOLODetector import YoloDetector, YOLOModel
from robot_friend.resource_handler import get_model_dir


def main() -> None:
    model_dir = get_model_dir()
    print(model_dir)

    detector = YoloDetector(YOLOModel.YOLO_V8N)

    # Use camera with index 0
    cap = cv2.VideoCapture(index=0)

    if not cap.isOpened():
        sys.exit("cannot open webcam")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        boxes = detector.detect(frame)
        if not boxes:
            continue

        for b in boxes:
            cv2.rectangle(frame, (b.bounding_box.x1, b.bounding_box.y1), (b.bounding_box.x2, b.bounding_box.y2), (0, 255, 0), 2)
        cv2.imshow("presence", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
