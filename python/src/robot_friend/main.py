import argparse
from robot_friend.mjpeg import MJPEGServer

import cv2

from robot_friend.camera import open_camera
from robot_friend.image.detection_factory import DetectionFactory
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host


def main() -> None:
    parser = argparse.ArgumentParser(description='robot-friend person detection')
    parser.add_argument('--port', type=int, metavar='PORT', default=8081,
                        help="Port to serve the annotated camera view as MJPEG on")

    args = parser.parse_args()

    detector = DetectionFactory.get_detector()

    # The Pi is headless: serve the annotated view as MJPEG rather than opening a
    # local OpenCV/Qt window, which aborts the process when there is no display.
    headless = is_pi_host()
    server: MJPEGServer | None = None
    if headless:
        server = MJPEGServer(args.port)
        finch_logger.info("serving annotated view on http://0.0.0.0:%s/", args.port)

    with open_camera() as camera:
        finch_logger.info(
            "Running: %s + %s", type(detector).__name__, type(camera).__name__
        )
        try:
            while True:
                frame = camera.read()
                if frame is None:
                    break
                boxes = detector.detect(frame)

                for b in boxes:
                    cv2.rectangle(frame, (b.bounding_box.x1, b.bounding_box.y1),
                                  (b.bounding_box.x2, b.bounding_box.y2), (0, 255, 0), 2)

                if server:
                    server.publish(frame)

                if not headless:
                    cv2.imshow('presence', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        except KeyboardInterrupt:
            pass

    if not headless:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
