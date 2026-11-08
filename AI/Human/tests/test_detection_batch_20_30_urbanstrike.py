"""Unit and integration tests for Batching 20-30 Detect Requests, AI Multimodal Analysis,
and Single POST Request Dispatch to the Urban Strike endpoint on Port 7777 Tunneling.
"""

import base64
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import pytest
import requests

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import (
    BehaviorPrediction,
    HumanPoseTrack,
    KeypointCOCO,
    SOCFrameAnalysisResult,
)
from urbansoc.domain.synthetic import create_synthetic_pose
from urbansoc.server.camera_context import CameraContext, CameraDetectionBatch
from urbansoc.server.inference_server import InferenceServer
from urbansoc.server.tunnel import CloudflareTunnelManager
from urbansoc.telemetry.webhook_dispatcher import WebhookDispatcher


class MockUrbanStrikeServer(BaseHTTPRequestHandler):
    """Local mock receiver capturing POST requests directed at Urban Strike endpoint."""

    received_requests: List[Dict[str, Any]] = []

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            MockUrbanStrikeServer.received_requests.append(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "incident_recorded", "success": true}')
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        pass


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def make_dummy_analysis(
    frame_idx: int = 1,
    action: str = "WEAPON_THREAT",
    threat_level: ThreatLevel = ThreatLevel.CRITICAL,
    threat_score: float = 0.98,
) -> SOCFrameAnalysisResult:
    pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="two_handed_aim", step=frame_idx)
    pose.behavior = BehaviorPrediction(
        primary_behavior=BehaviorType(action),
        confidence=0.95,
        threat_level=threat_level,
        threat_score=threat_score,
        reasoning=f"Tactical stance for {action}",
    )
    return SOCFrameAnalysisResult(
        frame_index=frame_idx,
        timestamp="2026-11-08 05:30:00.000",
        human_count=1,
        humans=[pose],
        highest_threat_level=threat_level,
        highest_threat_score=threat_score,
    )


# ------------------------------------------------------------------------------
# Test 1 & 2: Batch Size Clamping (20 to 30)
# ------------------------------------------------------------------------------
def test_batch_size_clamped_between_20_and_30() -> None:
    # Lower bound clamp: 5 -> clamped to 20
    b_low = CameraDetectionBatch(batch_size=5)
    assert b_low.batch_size == 20

    # Upper bound clamp: 50 -> clamped to 30
    b_high = CameraDetectionBatch(batch_size=50)
    assert b_high.batch_size == 30

    # Valid within range: 25 -> stays 25
    b_mid = CameraDetectionBatch(batch_size=25)
    assert b_mid.batch_size == 25


def test_camera_context_respects_batch_size_and_env(tmp_path: Any) -> None:
    # Default without env: clamped to 25
    os.environ["SOC_DETECTION_BATCH_SIZE"] = "28"
    try:
        ctx = CameraContext(camera_id="CAM_TEST_ENV", output_dir=str(tmp_path))
        assert ctx.batch_size == 28
        assert ctx.detection_batch.batch_size == 28
    finally:
        os.environ.pop("SOC_DETECTION_BATCH_SIZE", None)


# ------------------------------------------------------------------------------
# Test 3 & 4: Accumulation under 20-30 detects and flushing at exact batch size
# ------------------------------------------------------------------------------
def test_detection_batch_accumulation_and_flush() -> None:
    batch = CameraDetectionBatch(batch_size=20)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Ingest 19 events (1 below batch threshold)
    for i in range(1, 20):
        analysis = make_dummy_analysis(frame_idx=i, action="NORMAL", threat_level=ThreatLevel.LOW, threat_score=0.1)
        ready = batch.add_event(
            analysis=analysis,
            frame_bgr=frame,
            display_frame=frame,
            primary_action="NORMAL",
            humans_summary=[{"track_id": 1}],
            timestamp=float(i),
        )
        assert ready is False
        assert len(batch.events) == i

    # Ingest 20th event (reaching threshold)
    analysis_20 = make_dummy_analysis(frame_idx=20, action="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, threat_score=0.98)
    ready_20 = batch.add_event(
        analysis=analysis_20,
        frame_bgr=frame,
        display_frame=frame,
        primary_action="WEAPON_THREAT",
        humans_summary=[{"track_id": 1}],
        timestamp=20.0,
    )
    assert ready_20 is True
    assert len(batch.events) == 20

    # Flush batch report
    summary = batch.flush()
    assert summary["event_count"] == 20
    assert summary["first_frame_index"] == 1
    assert summary["last_frame_index"] == 20
    assert summary["dominant_action"] == "NORMAL"
    assert summary["highest_threat"] == "CRITICAL"
    assert summary["highest_threat_score"] == 0.98
    assert summary["keyframe_bgr"] is not None
    # Buffer should now be cleared for next cycle
    assert len(batch.events) == 0


# ------------------------------------------------------------------------------
# Test 5 & 6: Keyframe Selection Priority
# ------------------------------------------------------------------------------
def test_keyframe_selection_picks_highest_threat_frame() -> None:
    batch = CameraDetectionBatch(batch_size=25)
    dummy_frame = np.zeros((50, 50, 3), dtype=np.uint8)
    special_keyframe = np.full((50, 50, 3), 255, dtype=np.uint8)

    for i in range(1, 26):
        if i == 14:
            # Frame 14 has the highest threat
            analysis = make_dummy_analysis(frame_idx=i, action="FIGHTING", threat_level=ThreatLevel.CRITICAL, threat_score=0.99)
            batch.add_event(analysis, special_keyframe, special_keyframe, "FIGHTING", [], float(i))
        else:
            analysis = make_dummy_analysis(frame_idx=i, action="NORMAL", threat_level=ThreatLevel.LOW, threat_score=0.1)
            batch.add_event(analysis, dummy_frame, dummy_frame, "NORMAL", [], float(i))

    summary = batch.flush()
    assert summary["highest_threat_score"] == 0.99
    # The flushed keyframe must be the highest threat frame
    assert np.array_equal(summary["keyframe_bgr"], special_keyframe)


# ------------------------------------------------------------------------------
# Test 7: Multi-Camera Batch Isolation
# ------------------------------------------------------------------------------
def test_multi_camera_batch_isolation(tmp_path: Any) -> None:
    from urbansoc.server.camera_context import CameraContextManager

    mgr = CameraContextManager(output_dir=str(tmp_path))
    ctx_a = mgr.get_or_create("CAM_ALPHA", batch_size=20)
    ctx_b = mgr.get_or_create("CAM_BETA", batch_size=25)

    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    # Ingest 15 events into CAM_ALPHA
    for i in range(15):
        analysis = make_dummy_analysis(frame_idx=i)
        ctx_a.detection_batch.add_event(analysis, frame, frame, "NORMAL", [], float(i))

    # Ingest 5 events into CAM_BETA
    for j in range(5):
        analysis = make_dummy_analysis(frame_idx=j)
        ctx_b.detection_batch.add_event(analysis, frame, frame, "NORMAL", [], float(j))

    assert len(ctx_a.detection_batch.events) == 15
    assert len(ctx_b.detection_batch.events) == 5
    assert ctx_a.detection_batch.batch_size == 20
    assert ctx_b.detection_batch.batch_size == 25


# ------------------------------------------------------------------------------
# Test 8, 9 & 10: End-to-End Server Ingestion: 20-30 Detects -> AI Analysis -> Single POST to Urban Strike
# ------------------------------------------------------------------------------
def test_e2e_server_batches_25_detects_and_posts_once_to_urbanstrike(tmp_path: Any) -> None:
    urbanstrike_port = get_free_port()
    ai_server_port = get_free_port()

    output_dir = str(tmp_path / "soc_batch_out")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Start Mock Urban Strike Endpoint
    MockUrbanStrikeServer.received_requests = []
    mock_httpd = HTTPServer(("127.0.0.1", urbanstrike_port), MockUrbanStrikeServer)
    mock_thread = threading.Thread(target=mock_httpd.serve_forever, daemon=True)
    mock_thread.start()

    urbanstrike_url = f"http://127.0.0.1:{urbanstrike_port}/api/incidents"

    # 2. Start Central AI Server configured with batch_size=20 and webhook to Urban Strike
    server = InferenceServer(
        host="127.0.0.1",
        port=ai_server_port,
        output_dir=output_dir,
        enable_tunnel=False,
        webhook_url=urbanstrike_url,
        always_vlm=False,
        mock_vlm=True,
        enable_batching=True,
        batch_size=20,
    )
    server.start(blocking=False)
    time.sleep(0.4)

    try:
        # Prepare test image
        dummy_frame = np.full((120, 160, 3), 80, dtype=np.uint8)
        cv2.rectangle(dummy_frame, (30, 20), (130, 100), (0, 0, 255), 2)
        _, enc = cv2.imencode(".jpg", dummy_frame)
        jpeg_bytes = enc.tobytes()

        # Ingest 19 frames: must buffer and accumulate, ZERO webhook requests
        for step in range(1, 20):
            headers = {
                "Content-Type": "image/jpeg",
                "X-Camera-ID": "LAPTOP_STRIKE_CAM",
                "X-Timestamp-Ms": str(int(time.time() * 1000) + step * 40),
                "X-Test-Action": "WEAPON_THREAT",
                "X-Batch-AI": "true",
            }
            resp = requests.post(
                f"http://127.0.0.1:{ai_server_port}/api/v1/ingest/frame",
                data=jpeg_bytes,
                headers=headers,
                timeout=5.0,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "processed"
            assert data["batch_status"] == "accumulating"
            assert data["accumulated_events"] == step
            assert data["ai_analyzed"] is False

        # Verify Urban Strike received 0 requests during accumulation
        time.sleep(0.2)
        assert len(MockUrbanStrikeServer.received_requests) == 0

        # Ingest 20th frame: triggers batch flush, sends to AI, and posts to Urban Strike 1 time
        headers_20 = {
            "Content-Type": "image/jpeg",
            "X-Camera-ID": "LAPTOP_STRIKE_CAM",
            "X-Timestamp-Ms": str(int(time.time() * 1000) + 20 * 40),
            "X-Test-Action": "WEAPON_THREAT",
            "X-Batch-AI": "true",
        }
        resp_20 = requests.post(
            f"http://127.0.0.1:{ai_server_port}/api/v1/ingest/frame",
            data=jpeg_bytes,
            headers=headers_20,
            timeout=5.0,
        )
        assert resp_20.status_code == 200
        data_20 = resp_20.json()
        assert data_20["status"] == "processed"
        assert data_20["batch_status"] == "ai_analyzed"
        assert data_20["ai_analyzed"] is True
        assert data_20["event_batch_count"] == 20

        # Allow background dispatcher thread to deliver POST request
        time.sleep(0.6)

        # EXACTLY ONE POST request should have been received by Urban Strike
        assert len(MockUrbanStrikeServer.received_requests) == 1
        incident = MockUrbanStrikeServer.received_requests[0]

        assert incident["camera_id"] == "LAPTOP_STRIKE_CAM"
        assert incident["primary_action"] == "WEAPON_THREAT"
        assert incident["threat_level"] in ("HIGH", "CRITICAL")
        assert incident["ai_verified"] is True
        assert "batch_summary" in incident
        assert incident["batch_summary"]["event_count"] == 20
        assert incident["batch_summary"]["dominant_action"] == "WEAPON_THREAT"
        assert "image_base64" in incident or "image" in incident

    finally:
        server.stop()
        mock_httpd.shutdown()


# ------------------------------------------------------------------------------
# Test 11: Tunnel Configuration & Default Port 7777
# ------------------------------------------------------------------------------
def test_tunnel_manager_default_port_7777() -> None:
    tunnel = CloudflareTunnelManager()
    assert tunnel.local_port == 7777

    custom_tunnel = CloudflareTunnelManager(local_port=7777, local_host="127.0.0.1")
    assert custom_tunnel.local_port == 7777
    assert custom_tunnel.local_host == "127.0.0.1"


def test_inference_server_default_port_7777() -> None:
    srv = InferenceServer(enable_tunnel=False)
    assert srv.port == 7777
    assert srv.batch_size == 25
    assert srv.enable_batching is True
