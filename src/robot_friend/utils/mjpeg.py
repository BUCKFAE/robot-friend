"""Dependency-light MJPEG (multipart/x-mixed-replace) parsing.

Lives in ``utils`` (no web-stack imports) so the parser can be unit-tested and reused
without pulling in the dashboard's FastAPI transport.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import IO


def iter_mjpeg_frames(reader: IO[bytes]) -> Iterator[bytes]:
    """Yield JPEG payloads from a ``multipart/x-mixed-replace`` MJPEG stream.

    Parses each part's headers and uses ``Content-Length`` to read the exact JPEG body.
    ``reader`` is any blocking byte stream with ``readline()`` / ``read(n)`` (an
    ``http.client`` response, or a ``BytesIO`` in tests). Returns when the stream closes.
    """
    while True:
        content_length: int | None = None
        while True:
            line = reader.readline()
            if not line:
                return  # stream closed
            stripped = line.strip()
            if stripped.lower().startswith(b"content-length:"):
                content_length = int(stripped.split(b":", 1)[1].decode().strip())
            elif not stripped and content_length is not None:
                break  # blank line ends the part headers
        data = reader.read(content_length)
        if len(data) < content_length:
            return  # truncated / closed mid-frame
        yield data
