"""Unit and integration tests for HTTP MJPEG real-time camera streaming endpoint."""

import socket
import time
import urllib.request
import cv2
import numpy as np
import pytest

from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO
from urbansoc.server.inference_server import InferenceServer


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def mock_server(tmp_path):
    port = _find_free_port()
    server = InferenceServer(
        host="127.0.0.1",
        port=port,
        output_dir=str(tmp_path),
        model_weights="yolo/yolo11n-pose.pt",
    )
    server.start(blocking=False)
    time.sleep(0.3)

    # Ingest a sample test frame for LAPTOP_01
    ctx = server.context_manager.get_or_create("LAPTOP_01")
    test_img = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(test_img, "TEST FRAME", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    with ctx._lock:
        ctx.latest_frame = test_img
        ctx.latest_display_frame = test_img.copy()
        ctx.frame_count = 1

    yield server, port
    server.stop()


def test_mjpeg_stream_headers_and_frame_chunks(mock_server):
    """Verify HTTP MJPEG endpoint returns multipart/x-mixed-replace with valid JPEG frames."""
    server, port = mock_server
    url = f"http://127.0.0.1:{port}/api/v1/cameras/LAPTOP_01/stream"

    req = urllib.request.Request(url, headers={"X-Max-Frames": "2"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type")
        assert content_type is not None
        assert "multipart/x-mixed-replace" in content_type
        assert "boundary=frame" in content_type

        # Read the entire 2-frame stream
        data = resp.read()
        assert b"--frame\r\n" in data
        assert b"Content-Type: image/jpeg\r\n" in data
        # JPEG start of image marker
        assert b"\xff\xd8" in data


def test_mjpeg_direct_short_url_stream(mock_server):
    """Verify direct short url /stream.mjpg streams active camera."""
    server, port = mock_server
    url = f"http://127.0.0.1:{port}/stream.mjpg"

    req = urllib.request.Request(url, headers={"X-Max-Frames": "1"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type")
        assert "multipart/x-mixed-replace" in content_type
        data = resp.read()
        assert b"\xff\xd8" in data


def test_mjpeg_stream_graceful_disconnect(mock_server):
    """Verify sudden client disconnect does not raise unhandled exception in server."""
    server, port = mock_server

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))
    req = b"GET /api/v1/cameras/LAPTOP_01/stream HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
    s.sendall(req)

    # Read initial bytes then abruptly close socket
    initial_bytes = s.recv(512)
    assert b"200 OK" in initial_bytes
    s.close()

    time.sleep(0.2)
    # Server should still be healthy and responding to new requests
    status_url = f"http://127.0.0.1:{port}/api/v1/cameras"
    with urllib.request.urlopen(status_url, timeout=2.0) as resp:
        assert resp.status == 200
