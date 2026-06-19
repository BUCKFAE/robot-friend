"""HTTP transport for dashboard video streams.

Each named stream stores its latest JPEG plus a monotonic sequence number. Producers
publish frames from ordinary threads; FastAPI routes expose binary JPEG WebSockets
for browser panels, MJPEG for simple external viewers, and a single-frame snapshot
endpoint for tooling.
"""
from __future__ import annotations

import asyncio
import functools
import threading

import cv2
import numpy as np
from fastapi import Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

_BOUNDARY = "frame"
_JPEG_QUALITY = 80


class VideoStreams:
    """Latest-JPEG-per-named-stream, served through a FastAPI app."""

    URL_PREFIX = "/dashboard/video"

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._jpeg: dict[str, bytes] = {}
        self._seq: dict[str, int] = {}

    def publish(self, stream: str, frame: np.ndarray) -> None:
        """Encode a BGR uint8 frame to JPEG and publish it on ``stream``."""
        data = encode_jpeg(frame)
        if data:
            self.publish_jpeg(stream, data)

    def publish_jpeg(self, stream: str, data: bytes) -> None:
        """Publish an already-encoded JPEG on ``stream``."""
        with self._cond:
            self._jpeg[stream] = data
            self._seq[stream] = self._seq.get(stream, 0) + 1
            self._cond.notify_all()

    def get(self, stream: str) -> tuple[bytes | None, int]:
        """Return ``(latest_jpeg, sequence)`` for ``stream``."""
        with self._cond:
            return self._jpeg.get(stream), self._seq.get(stream, 0)

    def wait_for_next(
        self, stream: str, last_seq: int, timeout: float = 5.0
    ) -> tuple[bytes | None, int]:
        """Block until ``stream`` has a frame newer than ``last_seq`` or times out."""
        with self._cond:
            self._cond.wait_for(
                lambda: self._seq.get(stream, 0) != last_seq,
                timeout=timeout,
            )
            return self._jpeg.get(stream), self._seq.get(stream, 0)

    def url(self, stream: str) -> str:
        """Return the MJPEG endpoint for ``stream``."""
        return f"{self.URL_PREFIX}/{stream}"

    def snapshot_url(self, stream: str) -> str:
        """Return the single-frame JPEG endpoint for ``stream``."""
        return f"{self.URL_PREFIX}/{stream}/snapshot"

    def websocket_url(self, stream: str) -> str:
        """Return the browser WebSocket endpoint for ``stream``."""
        return f"{self.URL_PREFIX}/{stream}/ws"

    def mount(self, app) -> None:
        """Register MJPEG and snapshot routes on ``app``."""
        streams = self

        @app.get(self.URL_PREFIX + "/{stream}")
        async def video_feed(stream: str):
            async def frames():
                last = -1
                try:
                    while True:
                        data, seq = await asyncio.to_thread(
                            streams.wait_for_next, stream, last
                        )
                        if data is not None and seq != last:
                            last = seq
                            yield (
                                b"--" + _BOUNDARY.encode() + b"\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n"
                                + data + b"\r\n"
                            )
                except asyncio.CancelledError:
                    return

            return StreamingResponse(
                frames(),
                media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}",
                headers={
                    "Cache-Control": "no-store, max-age=0",
                    "Pragma": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        @app.websocket(self.URL_PREFIX + "/{stream}/ws")
        async def video_socket(websocket: WebSocket, stream: str):
            await websocket.accept()
            last = -1
            try:
                while True:
                    data, seq = await asyncio.to_thread(
                        streams.wait_for_next, stream, last
                    )
                    if data is not None and seq != last:
                        last = seq
                        await websocket.send_bytes(data)
            except (asyncio.CancelledError, WebSocketDisconnect):
                return

        @app.get(self.URL_PREFIX + "/{stream}/snapshot")
        async def video_snapshot(stream: str):
            data, seq = streams.get(stream)
            return Response(
                content=data if data is not None else placeholder_jpeg(),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-store, max-age=0",
                    "Pragma": "no-cache",
                    "X-Frame-Seq": str(seq),
                },
            )


def encode_jpeg(frame: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
    return buf.tobytes() if ok else b""


@functools.lru_cache(maxsize=1)
def placeholder_jpeg() -> bytes:
    frame = np.zeros((360, 480, 3), dtype=np.uint8)
    frame[:] = (27, 17, 17)
    cv2.putText(
        frame,
        "no signal",
        (150, 195),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (200, 173, 166),
        2,
        cv2.LINE_AA,
    )
    return encode_jpeg(frame)
