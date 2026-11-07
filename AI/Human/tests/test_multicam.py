"""Unit and Integration tests for Multi-Laptop Client-Server AI-SOC Architecture."""

import base64
import hashlib
import json
import socket
import threading
import time
from typing import Tuple

import cv2
import numpy as np
import pytest
import requests

from urbansoc.client.edge_client import EdgeCameraClient
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import COCO_KEYPOINT_NAMES
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO
from urbansoc.domain.webhook_models import CameraLocationConfig
from urbansoc.server.camera_context import CameraContext, CameraContextManager
from urbansoc.server.inference_server import InferenceServer
from urbansoc.telemetry.webhook_dispatcher import compute_forensic_sha256, encode_image_and_hash


def get_free_port() -> int:
    """Find a random available TCP port for isolated integration testing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_camera_context_isolation(tmp_path: pytest.TempPathFactory) -> None:
    """Verify that CameraContextManager maintains 100% isolation between multiple cameras (AGENTS.md CD-02)."""
    manager = CameraContextManager(output_dir=str(tmp_path))

    ctx1 = manager.get_or_create("LAPTOP_01", config=CameraLocationConfig(camera_id="LAPTOP_01", name="Laptop A"))
    ctx2 = manager.get_or_create("LAPTOP_02", config=CameraLocationConfig(camera_id="LAPTOP_02", name="Laptop B"))

    assert ctx1.camera_id == "LAPTOP_01"
    assert ctx2.camera_id == "LAPTOP_02"
    assert ctx1 is not ctx2
    assert ctx1.behavior_engine is not ctx2.behavior_engine
    assert ctx1.throttler is not ctx2.throttler

    # Process empty detections on both
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)

    analysis1, disp1 = ctx1.process_detections(frame1, None, None, None, t_infer=10.0, timestamp=time.time())
    analysis2, disp2 = ctx2.process_detections(frame2, None, None, None, t_infer=12.0, timestamp=time.time())

    assert analysis1.human_count == 0
    assert analysis2.human_count == 0
    assert ctx1.frame_count == 1
    assert ctx2.frame_count == 1

    status1 = ctx1.get_status_dict()
    status2 = ctx2.get_status_dict()

    assert status1["camera_id"] == "LAPTOP_01"
    assert status1["name"] == "Laptop A"
    assert status2["camera_id"] == "LAPTOP_02"
    assert status2["name"] == "Laptop B"


def test_edge_camera_client_simulated_read() -> None:
    """Verify that EdgeCameraClient safely generates synthetic frames without hardware webcam."""
    client = EdgeCameraClient(
        server_url="http://127.0.0.1:9999",
        camera_id="TEST_CAM",
        camera_name="Test Client",
        camera_index=999,  # Non-existent webcam index forces synthetic fallback
        fps=10.0,
        resolution=(320, 240),
        headless=True,
    )

    ret, frame = client._read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (240, 320, 3)

    client.stop()


def test_inference_server_e2e_integration(tmp_path: pytest.TempPathFactory) -> None:
    """Full End-to-End integration test for the intermediate InferenceServer."""
    test_port = get_free_port()
    output_dir = str(tmp_path)

    # Initialize and start InferenceServer non-blocking
    server = InferenceServer(
        host="127.0.0.1",
        port=test_port,
        output_dir=output_dir,
    )
    server.start(blocking=False)
    time.sleep(0.4)  # Allow thread to bind port

    base_url = f"http://127.0.0.1:{test_port}"

    try:
        # 1. Test GET / (Dashboard UI)
        resp_dashboard = requests.get(f"{base_url}/", timeout=2.0)
        assert resp_dashboard.status_code == 200
        assert "URBAN SAFETY AI-SOC" in resp_dashboard.text

        # 2. Test GET /api/v1/cameras (Empty initial state)
        resp_cams = requests.get(f"{base_url}/api/v1/cameras", timeout=2.0)
        assert resp_cams.status_code == 200
        data_cams = resp_cams.json()
        assert data_cams["status"] == "success"
        assert isinstance(data_cams["cameras"], list)

        # 3. Test POST /api/v1/cameras/register
        reg_payload = {
            "camera_id": "LAPTOP_TEST_01",
            "name": "Laptop Alpha",
            "latitude": 10.776889,
            "longitude": 106.700806,
            "address": "Phòng Điều Hành A",
            "fps": 15.0,
        }
        resp_reg = requests.post(f"{base_url}/api/v1/cameras/register", json=reg_payload, timeout=2.0)
        assert resp_reg.status_code == 200
        reg_data = resp_reg.json()
        assert reg_data["status"] == "registered"
        assert reg_data["camera_id"] == "LAPTOP_TEST_01"

        # 4. Test POST /api/v1/ingest/frame with raw binary JPEG
        test_frame = np.full((240, 320, 3), 100, dtype=np.uint8)
        cv2.putText(test_frame, "TEST FRAME", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        _, jpeg_encoded = cv2.imencode(".jpg", test_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        jpeg_bytes = jpeg_encoded.tobytes()

        headers = {
            "Content-Type": "image/jpeg",
            "X-Camera-ID": "LAPTOP_TEST_01",
            "X-Camera-Name": "Laptop Alpha",
            "X-Timestamp-Ms": str(int(time.time() * 1000)),
        }
        resp_ingest = requests.post(f"{base_url}/api/v1/ingest/frame", data=jpeg_bytes, headers=headers, timeout=3.0)
        assert resp_ingest.status_code == 200
        ingest_data = resp_ingest.json()
        assert ingest_data["status"] == "processed"
        assert ingest_data["camera_id"] == "LAPTOP_TEST_01"
        assert ingest_data["frame_index"] >= 1

        # 5. Test GET /api/v1/cameras/<camera_id>/snapshot
        resp_snap = requests.get(f"{base_url}/api/v1/cameras/LAPTOP_TEST_01/snapshot", timeout=2.0)
        assert resp_snap.status_code == 200
        assert resp_snap.headers["Content-Type"] == "image/jpeg"
        assert len(resp_snap.content) > 100

        # 6. Test GET /api/v1/cameras after stream
        resp_cams_after = requests.get(f"{base_url}/api/v1/cameras", timeout=2.0)
        assert resp_cams_after.status_code == 200
        cams_list = resp_cams_after.json()["cameras"]
        assert len(cams_list) >= 1
        cam_info = next(c for c in cams_list if c["camera_id"] == "LAPTOP_TEST_01")
        assert cam_info["name"] == "Laptop Alpha"
        assert cam_info["status"] == "ONLINE"
        assert cam_info["total_frames"] >= 1

        # 7. Test Incident Webhook reception with forensic SHA-256
        ts_ms = int(time.time() * 1000)
        sample_img = np.full((100, 100, 3), 50, dtype=np.uint8)
        _, enc_sample = cv2.imencode(".jpg", sample_img)
        sample_raw = enc_sample.tobytes()
        expected_hash = compute_forensic_sha256(sample_raw, ts_ms)
        sample_b64 = "data:image/jpeg;base64," + base64.b64encode(sample_raw).decode("utf-8")

        incident_payload = {
            "event_id": "EVT_TEST_001",
            "timestamp": "2026-11-07T15:00:00",
            "timestamp_ms": ts_ms,
            "camera": {"camera_id": "LAPTOP_TEST_01"},
            "detection": {
                "full_image": {
                    "image_base64": sample_b64,
                    "sha256_hash": expected_hash,
                }
            },
        }
        resp_incident = requests.post(f"{base_url}/api/v1/incidents", json=incident_payload, timeout=2.0)
        assert resp_incident.status_code == 200
        inc_data = resp_incident.json()
        assert inc_data["status"] == "success"
        assert inc_data["forensic_hash_valid"] is True

        # 8. Test EdgeCameraClient streaming directly into InferenceServer
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="LAPTOP_CLIENT_E2E",
            camera_name="Laptop Automated Streamer",
            camera_index=999,  # synthetic
            fps=20.0,
            resolution=(320, 240),
            headless=True,
        )
        client.stream_loop(max_frames=3)
        assert client.frame_count >= 3

        # Verify LAPTOP_CLIENT_E2E is now registered and has received frames
        resp_cams_final = requests.get(f"{base_url}/api/v1/cameras", timeout=2.0)
        cams_final = resp_cams_final.json()["cameras"]
        e2e_cam = next((c for c in cams_final if c["camera_id"] == "LAPTOP_CLIENT_E2E"), None)
        assert e2e_cam is not None
        assert e2e_cam["total_frames"] >= 3

    finally:
        server.stop()


def test_independent_camera_throttling(tmp_path: pytest.TempPathFactory) -> None:
    """Verify that event throttling on Camera 1 does not suppress alerts on Camera 2 (AGENTS.md CD-02, CD-05)."""
    manager = CameraContextManager(output_dir=str(tmp_path))
    ctx1 = manager.get_or_create("CAM_01")
    ctx2 = manager.get_or_create("CAM_02")

    now = time.time()
    # Trigger event on CAM_01
    assert ctx1.throttler.should_dispatch(1, "WEAPON_THREAT", ThreatLevel.HIGH, now, 5.0) is True
    # Immediate second event on CAM_01 is throttled
    assert ctx1.throttler.should_dispatch(1, "WEAPON_THREAT", ThreatLevel.HIGH, now + 0.1, 5.0) is False

    # Event on CAM_02 with SAME track_id is NOT throttled because CAM_02 has its own isolated throttler!
    assert ctx2.throttler.should_dispatch(1, "WEAPON_THREAT", ThreatLevel.HIGH, now + 0.1, 5.0) is True


def test_multicam_concurrent_action_detection(tmp_path: pytest.TempPathFactory) -> None:
    """Verify that multiple cameras independently detect distinct dangerous human actions in parallel."""
    test_port = get_free_port()
    server = InferenceServer(host="127.0.0.1", port=test_port, output_dir=str(tmp_path))
    server.start(blocking=False)
    time.sleep(0.4)

    base_url = f"http://127.0.0.1:{test_port}"

    try:
        # Camera A streams WEAPON_THREAT
        client_a = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_WEAPON",
            camera_name="Cam Weapon Stance",
            camera_index=991,
            fps=25.0,
            headless=True,
            test_action="WEAPON_THREAT",
        )
        client_a.stream_loop(max_frames=10)

        # Camera B streams FALLEN
        client_b = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_FALLEN",
            camera_name="Cam Fallen Subject",
            camera_index=992,
            fps=25.0,
            headless=True,
            test_action="FALLEN",
        )
        client_b.stream_loop(max_frames=10)

        # Camera C streams HANDS_UP
        client_c = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_HANDS_UP",
            camera_name="Cam Hands Up",
            camera_index=993,
            fps=25.0,
            headless=True,
            test_action="HANDS_UP",
        )
        client_c.stream_loop(max_frames=10)

        resp = requests.get(f"{base_url}/api/v1/cameras", timeout=2.0)
        cams = resp.json().get("cameras", [])

        cam_weapon = next(c for c in cams if c["camera_id"] == "CAM_WEAPON")
        cam_fallen = next(c for c in cams if c["camera_id"] == "CAM_FALLEN")
        cam_hands = next(c for c in cams if c["camera_id"] == "CAM_HANDS_UP")

        assert cam_weapon["primary_action"] == "WEAPON_THREAT"
        assert cam_weapon["highest_threat"] == "CRITICAL"

        assert cam_fallen["primary_action"] == "FALLEN"
        assert cam_fallen["highest_threat"] == "CRITICAL"

        assert cam_hands["primary_action"] == "HANDS_UP"
        assert cam_hands["highest_threat"] == "HIGH"
    finally:
        server.stop()


