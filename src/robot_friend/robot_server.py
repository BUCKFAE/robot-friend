"""Dependency-light HTTP server for a headless robot.

Serves any number of named MJPEG video streams plus a small registry of JSON endpoints
from a single stdlib :class:`~http.server.ThreadingHTTPServer` — no FastAPI/web stack, so
the realtime detection process stays lean and free of dashboard concerns. The dashboard
*attaches* as a client: it proxies the MJPEG into its own transport, polls the JSON
endpoints (telemetry, logs, devices), and POSTs control commands. The server depends on
nothing it serves — register only the endpoints a given process wants, and it works the
same whether or not anything is attached.

Built-in route:
    ``GET /video/<stream>``  multipart MJPEG of the latest frames published on ``<stream>``
Registered routes (via :meth:`on_get` / :meth:`on_post`):
    ``GET <path>``   handler(query_params) -> JSON bytes
    ``POST <path>``  handler(parsed_json_body) -> optional JSON bytes

This generalizes the old single-stream ``MJPEGServer``.
"""
from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np

from robot_friend.utils.jpeg import encode_jpeg

_BOUNDARY = b"frame"
_VIDEO_PREFIX = "/video/"

#: A GET handler maps flattened query params to a JSON response body.
GetHandler = Callable[[dict[str, str]], bytes]
#: A POST handler maps the parsed JSON body to an optional JSON response body.
PostHandler = Callable[[dict], "bytes | None"]


class RobotServer:
    """Serves named MJPEG streams + registered JSON endpoints from one stdlib server."""

    def __init__(self, port: int, *, host: str = "0.0.0.0") -> None:
        self._cond = threading.Condition()
        self._jpeg: dict[str, bytes] = {}
        self._seq: dict[str, int] = {}
        self._get_routes: dict[str, GetHandler] = {}
        self._post_routes: dict[str, PostHandler] = {}
        self._httpd = ThreadingHTTPServer((host, port), self._make_handler())
        threading.Thread(
            target=self._httpd.serve_forever, daemon=True, name="robot-server"
        ).start()

    @property
    def port(self) -> int:
        """The bound port (resolves the real port when constructed with ``port=0``)."""
        return self._httpd.server_address[1]

    def on_get(self, path: str, handler: GetHandler) -> None:
        """Register a JSON GET endpoint; ``handler(query)`` returns the JSON body bytes."""
        self._get_routes[path] = handler

    def on_post(self, path: str, handler: PostHandler) -> None:
        """Register a JSON POST endpoint; ``handler(body)`` returns optional JSON bytes."""
        self._post_routes[path] = handler

    def publish(self, stream: str, frame: np.ndarray) -> None:
        """Encode a BGR frame and publish it as the latest on ``stream``."""
        data = encode_jpeg(frame)
        if data:
            self.publish_jpeg(stream, data)

    def publish_jpeg(self, stream: str, data: bytes) -> None:
        """Publish an already-encoded JPEG as the latest on ``stream``."""
        with self._cond:
            self._jpeg[stream] = data
            self._seq[stream] = self._seq.get(stream, 0) + 1
            self._cond.notify_all()

    def shutdown(self) -> None:
        """Stop serving (the worker threads are daemons, so this is optional)."""
        self._httpd.shutdown()

    def _wait_for_next(
        self, stream: str, last_seq: int, timeout: float = 5.0
    ) -> tuple[bytes | None, int]:
        with self._cond:
            self._cond.wait_for(
                lambda: self._seq.get(stream, 0) != last_seq, timeout=timeout
            )
            return self._jpeg.get(stream), self._seq.get(stream, 0)

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 (http.server API)
                parsed = urlparse(self.path)
                handler = server._get_routes.get(parsed.path)
                if handler is not None:
                    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                    self._send_json(handler(query))
                elif parsed.path.startswith(_VIDEO_PREFIX):
                    self._serve_mjpeg(parsed.path[len(_VIDEO_PREFIX):])
                else:
                    self.send_error(404)

            def do_POST(self) -> None:  # noqa: N802 (http.server API)
                handler = server._post_routes.get(urlparse(self.path).path)
                if handler is None:
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    self.send_error(400)
                    return
                result = handler(body)
                self._send_json(result if result is not None else b"{}")

            def _send_json(self, body: bytes) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.end_headers()
                self.wfile.write(body)

            def _serve_mjpeg(self, stream: str) -> None:
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    f"multipart/x-mixed-replace; boundary={_BOUNDARY.decode()}",
                )
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.end_headers()
                last = -1
                try:
                    while True:
                        data, seq = server._wait_for_next(stream, last)
                        if data is None or seq == last:
                            continue
                        last = seq
                        self.wfile.write(b"--" + _BOUNDARY + b"\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
                        self.wfile.write(data)
                        self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, format, *args) -> None:  # noqa: A002  silence per-request logging
                pass

        return Handler
