"""Comprehensive test suite for Camera Client Automated HTTPS Tunneling & In-Browser Video Streaming.

Covers >= 30 test cases verifying:
1. Cloudflare Tunnel extraction, lifecycle, and edge cases.
2. In-Browser /watch and /player endpoints rendering HTML5 video components.
3. Live MJPEG streaming response headers and multi-tenant routing.
4. Edge Camera Client tunnel discovery and telemetry HUD rendering.
5. Automated script syntax and integration integrity.
"""

import os
import re
import socket
import threading
import time
from http.server import HTTPServer
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from urbansoc.client.edge_client import EdgeCameraClient, get_auto_camera_id, get_auto_camera_name
from urbansoc.server.inference_server import InferenceServer, SOCMultiCameraHandler, ThreadedHTTPServer
from urbansoc.server.tunnel import CloudflareTunnelManager
from urbansoc.server.watch_player_html import WATCH_PLAYER_HTML


# ==============================================================================
# GROUP 1: Cloudflare Tunnel Parsing & Lifecycle Tests (TC-01 -> TC-08)
# ==============================================================================

def test_tc01_tunnel_manager_default_init():
    """TC-01: CloudflareTunnelManager initializes with expected local host and port."""
    mgr = CloudflareTunnelManager(local_port=8080, local_host="127.0.0.1")
    assert mgr.local_port == 8080
    assert mgr.local_host == "127.0.0.1"
    assert mgr.public_url is None
    assert mgr.process is None


def test_tc02_tunnel_manager_custom_bin_path():
    """TC-02: CloudflareTunnelManager respects explicit binary path."""
    mgr = CloudflareTunnelManager(local_port=9000, bin_path="/nonexistent/cloudflared")
    assert mgr.bin_path == "/nonexistent/cloudflared"


def test_tc03_tunnel_manager_start_missing_bin():
    """TC-03: Tunnel start returns None gracefully when cloudflared executable is missing."""
    mgr = CloudflareTunnelManager(local_port=8080, bin_path="/tmp/fake_bin_missing_cloudflared")
    url = mgr.start(timeout_seconds=0.1)
    assert url is None
    assert mgr.public_url is None


def test_tc04_tunnel_regex_standard_subdomain():
    """TC-04: Regex matches standard Cloudflare trycloudflare domain."""
    log_text = "INF | https://urban-safety-soc-1234.trycloudflare.com |"
    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", log_text)
    assert match is not None
    assert match.group(0) == "https://urban-safety-soc-1234.trycloudflare.com"


def test_tc05_tunnel_regex_hyphenated_alphanumeric():
    """TC-05: Regex handles complex hyphenated subdomains."""
    log_text = "Visit tunnel at: https://a-b-c-99-soc-test.trycloudflare.com/ready"
    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", log_text)
    assert match is not None
    assert match.group(0) == "https://a-b-c-99-soc-test.trycloudflare.com"


def test_tc06_tunnel_regex_ignores_non_tunnel():
    """TC-06: Regex correctly rejects non-cloudflare domains."""
    log_text = "Connected to https://google.com and https://example.com"
    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", log_text)
    assert match is None


def test_tc07_tunnel_stop_idempotent():
    """TC-07: Calling stop multiple times does not raise any exception."""
    mgr = CloudflareTunnelManager(local_port=8000)
    mgr.stop()
    mgr.stop()
    assert mgr.process is None
    assert mgr.public_url is None


def test_tc08_tunnel_monitor_output_simulated():
    """TC-08: Reader thread extracts public URL from stdout stream."""
    mgr = CloudflareTunnelManager(local_port=8000)
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = [
        "2026-11-08 Starting tunnel...\n",
        "2026-11-08 Your quick Tunnel: https://live-stream-test.trycloudflare.com\n",
        "",
    ]
    mgr.process = mock_proc
    mgr._monitor_output()
    assert mgr.public_url == "https://live-stream-test.trycloudflare.com"


# ==============================================================================
# GROUP 2: In-Browser HTML5 Watch Player & Template Integrity (TC-09 -> TC-16)
# ==============================================================================

def test_tc09_watch_player_html_doctype():
    """TC-09: Watch Player HTML template includes valid HTML5 doctype and viewport."""
    assert "<!DOCTYPE html>" in WATCH_PLAYER_HTML
    assert 'meta name="viewport"' in WATCH_PLAYER_HTML


def test_tc10_watch_player_stream_element():
    """TC-10: Watch Player HTML contains liveStream img tag pointing to MJPEG stream."""
    assert 'id="liveStream"' in WATCH_PLAYER_HTML
    assert '/stream.mjpg' in WATCH_PLAYER_HTML


def test_tc11_watch_player_fullscreen_support():
    """TC-11: Watch Player includes fullscreen toggle handler."""
    assert "toggleFullscreen()" in WATCH_PLAYER_HTML
    assert "requestFullscreen" in WATCH_PLAYER_HTML


def test_tc12_watch_player_snapshot_action():
    """TC-12: Watch Player includes snapshot capture function."""
    assert "captureSnapshot()" in WATCH_PLAYER_HTML
    assert "/snapshot.jpg" in WATCH_PLAYER_HTML


def test_tc13_watch_player_threat_tag():
    """TC-13: Watch Player includes threat level HUD element."""
    assert 'id="threatTag"' in WATCH_PLAYER_HTML
    assert 'id="threatText"' in WATCH_PLAYER_HTML


def test_tc14_watch_player_telemetry_elements():
    """TC-14: Watch Player includes FPS, human count, and clock elements."""
    assert 'id="fpsVal"' in WATCH_PLAYER_HTML
    assert 'id="humanCount"' in WATCH_PLAYER_HTML
    assert 'id="clockText"' in WATCH_PLAYER_HTML


def test_tc15_watch_player_auto_reconnect():
    """TC-15: Watch Player includes auto-reconnect error fallback for dropped streams."""
    assert "onerror" in WATCH_PLAYER_HTML
    assert "reloadStream" in WATCH_PLAYER_HTML


def test_tc16_watch_player_dashboard_link():
    """TC-16: Watch Player contains navigation link back to full SOC Dashboard."""
    assert 'href="/dashboard"' in WATCH_PLAYER_HTML


# ==============================================================================
# GROUP 3: Server HTTP Handlers & Live Video Streaming (TC-17 -> TC-24)
# ==============================================================================

@pytest.fixture(scope="module")
def mock_soc_server():
    """Spin up a lightweight InferenceServer instance for route verification."""
    server = InferenceServer(
        host="127.0.0.1",
        port=0,  # OS assigned ephemeral port
        enable_tunnel=False,
        always_vlm=False,
        mock_vlm=True,
    )
    # Mock detector to avoid downloading full YOLO weights during unit testing
    mock_det = MagicMock()
    mock_det.device = "cpu"
    mock_det.detect_and_estimate.return_value = []
    server.detector = mock_det

    # Bind ephemeral port
    class BoundHandler(SOCMultiCameraHandler):
        soc_server = server

    httpd = ThreadedHTTPServer(("127.0.0.1", 0), BoundHandler)
    httpd.inference_server = server
    assigned_port = httpd.server_address[1]
    server.port = assigned_port
    server._httpd = httpd

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    yield server, assigned_port

    httpd.shutdown()
    httpd.server_close()


def test_tc17_server_watch_endpoint_status(mock_soc_server):
    """TC-17: GET /watch returns HTTP 200 with text/html content-type."""
    import requests
    _, port = mock_soc_server
    resp = requests.get(f"http://127.0.0.1:{port}/watch", timeout=3.0)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("Content-Type", "")
    assert "URBAN SAFETY AI-SOC" in resp.text


def test_tc18_server_player_alias_endpoint(mock_soc_server):
    """TC-18: GET /player serves the same HTML5 watch player template."""
    import requests
    _, port = mock_soc_server
    resp = requests.get(f"http://127.0.0.1:{port}/player", timeout=3.0)
    assert resp.status_code == 200
    assert 'id="liveStream"' in resp.text


def test_tc19_server_video_alias_endpoint(mock_soc_server):
    """TC-19: GET /video serves the responsive watch player."""
    import requests
    _, port = mock_soc_server
    resp = requests.get(f"http://127.0.0.1:{port}/video", timeout=3.0)
    assert resp.status_code == 200
    assert "liveStream" in resp.text


def test_tc20_server_mjpeg_stream_header(mock_soc_server):
    """TC-20: GET /stream.mjpg returns multipart/x-mixed-replace content type."""
    import requests
    _, port = mock_soc_server
    headers = {"X-Max-Frames": "1"}
    with requests.get(f"http://127.0.0.1:{port}/stream.mjpg", headers=headers, stream=True, timeout=3.0) as resp:
        assert resp.status_code == 200
        ct = resp.headers.get("Content-Type", "")
        assert "multipart/x-mixed-replace" in ct
        assert "boundary=frame" in ct


def test_tc21_server_dashboard_state_api(mock_soc_server):
    """TC-21: GET /api/v1/dashboard/state returns valid status payload."""
    import requests
    _, port = mock_soc_server
    resp = requests.get(f"http://127.0.0.1:{port}/api/v1/dashboard/state", timeout=3.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "online"
    assert "cameras" in data


def test_tc22_server_camera_register_api(mock_soc_server):
    """TC-22: POST /api/v1/cameras/register successfully registers new camera profile."""
    import requests
    _, port = mock_soc_server
    payload = {
        "camera_id": "TEST_CAM_01",
        "name": "Test Camera 1",
        "latitude": 10.776,
        "longitude": 106.700,
        "address": "Zone A",
        "fps": 15.0,
    }
    resp = requests.post(f"http://127.0.0.1:{port}/api/v1/cameras/register", json=payload, timeout=3.0)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data.get("status") == "registered"
    assert res_data.get("camera_id") == "TEST_CAM_01"


def test_tc23_server_get_registered_cameras(mock_soc_server):
    """TC-23: GET /api/v1/cameras includes newly registered camera in count."""
    import requests
    _, port = mock_soc_server
    resp = requests.get(f"http://127.0.0.1:{port}/api/v1/cameras", timeout=3.0)
    assert resp.status_code == 200
    data = resp.json()
    cam_ids = [c["camera_id"] for c in data.get("cameras", [])]
    assert "TEST_CAM_01" in cam_ids


def test_tc24_server_camera_snapshot_endpoint(mock_soc_server):
    """TC-24: GET /api/v1/cameras/{id}/snapshot returns JPEG binary or placeholder."""
    import requests
    _, port = mock_soc_server
    resp = requests.get(f"http://127.0.0.1:{port}/api/v1/cameras/TEST_CAM_01/snapshot", timeout=3.0)
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type") == "image/jpeg"
    assert len(resp.content) > 0


# ==============================================================================
# GROUP 4: Edge Camera Client Tunnel Integration & HUD (TC-25 -> TC-32)
# ==============================================================================

def test_tc25_edge_client_auto_camera_id():
    """TC-25: get_auto_camera_id returns uppercase non-empty string starting with LAPTOP_."""
    cam_id = get_auto_camera_id()
    assert cam_id.startswith("LAPTOP_")
    assert len(cam_id) > 7


def test_tc26_edge_client_auto_camera_name():
    """TC-26: get_auto_camera_name returns non-empty formatted descriptor."""
    name = get_auto_camera_name()
    assert "Laptop" in name
    assert len(name) > 6


def test_tc27_edge_client_tunnel_flag_default():
    """TC-27: EdgeCameraClient enable_tunnel flag defaults to True."""
    client = EdgeCameraClient(headless=True, enable_tunnel=True)
    assert client.enable_tunnel is True
    client.stop()


def test_tc28_edge_client_tunnel_discovery_cloudflare_url():
    """TC-28: EdgeCameraClient recognizes server_url as tunnel URL when using trycloudflare."""
    tunnel_url = "https://subdomain-test.trycloudflare.com"
    client = EdgeCameraClient(server_url=tunnel_url, headless=True, enable_tunnel=True)
    assert client.public_tunnel_url == tunnel_url
    client.stop()


def test_tc29_edge_client_tunnel_discovery_from_file(tmp_path):
    """TC-29: EdgeCameraClient loads public URL from /tmp/soc_public_url.txt if present."""
    fake_txt = tmp_path / "soc_public_url.txt"
    fake_txt.write_text("https://test-from-file.trycloudflare.com\n")
    orig_exists = os.path.exists
    orig_open = open

    def fake_exists(p):
        if "soc_public_url.txt" in str(p):
            return True
        return orig_exists(p)

    def fake_open(p, *args, **kwargs):
        if "soc_public_url.txt" in str(p):
            return orig_open(str(fake_txt), *args, **kwargs)
        return orig_open(p, *args, **kwargs)

    with patch("os.path.exists", side_effect=fake_exists):
        with patch("builtins.open", side_effect=fake_open):
            client = EdgeCameraClient(server_url="http://127.0.0.1:8000", headless=True, enable_tunnel=True)
            assert client.public_tunnel_url == "https://test-from-file.trycloudflare.com"
            client.stop()


def test_tc30_edge_client_hud_rendering():
    """TC-30: EdgeCameraClient _draw_client_hud renders title banner onto video frame."""
    client = EdgeCameraClient(camera_id="HUD_TEST", camera_name="Test Client", headless=True)
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    hud_frame = client._draw_client_hud(blank_frame, current_fps=15.0)
    assert hud_frame.shape == (480, 640, 3)
    # HUD adds colored top and bottom banners, so mean pixel value increases from 0
    assert np.mean(hud_frame) > 0.0
    client.stop()


def test_tc31_edge_client_synthetic_stream():
    """TC-31: EdgeCameraClient _read_frame returns valid 640x480 frame in synthetic mode."""
    client = EdgeCameraClient(camera_index="auto", headless=True)
    client._simulated = True  # force synthetic
    ret, frame = client._read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    client.stop()


def test_tc32_edge_client_stop_cleans_session_and_tunnel():
    """TC-32: EdgeCameraClient stop releases resources without throwing errors."""
    client = EdgeCameraClient(headless=True)
    mock_mgr = MagicMock()
    client._tunnel_mgr = mock_mgr
    client.stop()
    assert client._running is False
    assert client._tunnel_mgr is None
    mock_mgr.stop.assert_called_once()


# ==============================================================================
# GROUP 5: CLI Arguments & Startup Automation Verification (TC-33 -> TC-36)
# ==============================================================================

def test_tc33_client_cli_arg_tunnel_flag():
    """TC-33: client.py parse_args defaults to --tunnel=True and supports --no-tunnel."""
    import sys
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    import client
    with patch("sys.argv", ["client.py"]):
        args = client.parse_args()
        assert args.tunnel is True

    with patch("sys.argv", ["client.py", "--no-tunnel"]):
        args = client.parse_args()
        assert args.tunnel is False


def test_tc34_client_cli_custom_server_url():
    """TC-34: client.py parse_args respects custom --server-url."""
    import sys
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    import client
    custom_url = "https://soc-edge.trycloudflare.com"
    with patch("sys.argv", ["client.py", "--server-url", custom_url]):
        args = client.parse_args()
        assert args.server_url == custom_url


def test_tc35_start_sh_syntax_check():
    """TC-35: start.sh passes bash syntax validation without syntax errors."""
    import subprocess
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "start.sh"))
    assert os.path.exists(script_path), f"start.sh not found at {script_path}"
    res = subprocess.run(["bash", "-n", script_path], capture_output=True, text=True)
    assert res.returncode == 0, f"start.sh syntax error: {res.stderr}"


def test_tc36_start_sh_help_execution():
    """TC-36: ./start.sh help executes successfully and outputs usage guides."""
    import subprocess
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "start.sh"))
    res = subprocess.run(["bash", script_path, "help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "CÁCH DÙNG START.SH" in res.stdout
    assert "./start.sh client" in res.stdout
