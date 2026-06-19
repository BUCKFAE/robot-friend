import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np


class MJPEGServer:
    """Serves the most recent published frame as an MJPEG stream on /.

    Viewable with a browser or ffplay; used to watch the annotated camera
    view of a headless robot over the network.
    """

    def __init__(self, port: int):
        self._jpeg: bytes | None = None
        self._cond = threading.Condition()
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()
                try:
                    while True:
                        with server._cond:
                            server._cond.wait()
                            data = server._jpeg
                        if data is None:
                            continue
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(data)}\r\n\r\n'.encode())
                        self.wfile.write(data)
                        self.wfile.write(b'\r\n')
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self._httpd = ThreadingHTTPServer(('0.0.0.0', port), Handler)
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def publish(self, frame: np.ndarray) -> None:
        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return
        with self._cond:
            self._jpeg = jpeg.tobytes()
            self._cond.notify_all()
