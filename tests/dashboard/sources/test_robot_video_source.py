"""The MJPEG proxy parser must split a multipart stream back into exact JPEG payloads."""
import io

from robot_friend.utils.mjpeg import iter_mjpeg_frames


def _part(payload: bytes) -> bytes:
    return (
        b"--frame\r\nContent-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload + b"\r\n"
    )


def test_iter_mjpeg_frames_parses_payloads():
    stream = io.BytesIO(_part(b"JPEG-ONE") + _part(b"second-frame"))
    assert list(iter_mjpeg_frames(stream)) == [b"JPEG-ONE", b"second-frame"]


def test_iter_mjpeg_frames_stops_at_a_truncated_frame():
    stream = io.BytesIO(
        _part(b"whole")
        + b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: 99\r\n\r\nshort"
    )
    assert list(iter_mjpeg_frames(stream)) == [b"whole"]
