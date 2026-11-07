"""Unit and integration tests for Webhook Event Dispatcher and Metadata Packaging."""

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import pytest

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import (
    BehaviorPrediction,
    HumanPoseTrack,
    SOCFrameAnalysisResult,
)
from urbansoc.domain.webhook_models import (
    CameraLocationConfig,
    SubjectCropData,
    WebhookIncidentPayload,
)
from urbansoc.telemetry.webhook_dispatcher import (
    EventThrottler,
    WebhookDispatcher,
    crop_subject_image,
    encode_image_to_base64,
)


class MockWebhookHandler(BaseHTTPRequestHandler):
    """Local test HTTP server capturing incoming webhook POST requests."""

    received_requests: List[Dict[str, Any]] = []

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
            MockWebhookHandler.received_requests.append(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "success", "received": true}')
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP server console logs in pytest
        pass


@pytest.fixture
def mock_server():
    """Start an ephemeral local HTTP server for testing webhook POST calls."""
    MockWebhookHandler.received_requests = []
    server = HTTPServer(("127.0.0.1", 0), MockWebhookHandler)
    host, port = server.server_address
    server_url = f"http://{host}:{port}/api/v1/incidents"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield server_url

    server.shutdown()
    server.server_close()


def test_crop_subject_image_normal():
    """Test standard bounding box cropping with margin."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a colored rectangle in the target area
    frame[100:200, 150:250] = (0, 255, 0)
    bbox = BBox(x1=150, y1=100, x2=250, y2=200)

    crop = crop_subject_image(frame, bbox, margin=0.10)
    assert crop is not None
    assert crop.shape[0] > 0
    assert crop.shape[1] > 0
    # Cropped width should be around 100 + 2*10 = 120
    assert 110 <= crop.shape[1] <= 130
    assert 110 <= crop.shape[0] <= 130


def test_crop_subject_image_boundary_clamping():
    """Test cropping near frame borders does not throw IndexError."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # BBox touching top-left corner
    bbox = BBox(x1=5, y1=5, x2=50, y2=80)
    crop = crop_subject_image(frame, bbox, margin=0.20)
    assert crop is not None
    assert crop.shape[0] > 0
    assert crop.shape[1] > 0


def test_crop_subject_image_invalid():
    """Test invalid or empty frame handling."""
    assert crop_subject_image(None, BBox(0, 0, 10, 10)) is None
    empty_frame = np.array([])
    assert crop_subject_image(empty_frame, BBox(0, 0, 10, 10)) is None
    # Inverted bbox
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    assert crop_subject_image(frame, BBox(50, 50, 20, 20)) is None


def test_encode_image_to_base64():
    """Test encoding image to Base64 JPEG data URL and verifying decoding."""
    test_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    b64_url = encode_image_to_base64(test_img, quality=80)

    assert b64_url.startswith("data:image/jpeg;base64,")
    raw_b64 = b64_url.split(",", 1)[1]
    img_bytes = base64.b64decode(raw_b64)
    assert len(img_bytes) > 0

    # Decode back with OpenCV to verify image validity
    decoded = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape == (100, 100, 3)

    # Empty image check
    assert encode_image_to_base64(None) == ""


def test_event_throttler_cooldown_and_escalation():
    """Test EventThrottler enforces cooldown but permits threat escalations."""
    throttler = EventThrottler(default_cooldown=3.0)
    t0 = 1000.0

    # First event should pass
    assert throttler.should_dispatch(
        track_id=1,
        behavior="NORMAL",
        threat_level=ThreatLevel.LOW,
        now=t0,
    ) is True

    # Immediate same event within cooldown should be throttled
    assert throttler.should_dispatch(
        track_id=1,
        behavior="NORMAL",
        threat_level=ThreatLevel.LOW,
        now=t0 + 0.5,
    ) is False

    # Event with threat escalation (LOW -> CRITICAL) should bypass cooldown
    assert throttler.should_dispatch(
        track_id=1,
        behavior="WEAPON_THREAT",
        threat_level=ThreatLevel.CRITICAL,
        now=t0 + 0.8,
    ) is True

    # Now in cooldown for CRITICAL
    assert throttler.should_dispatch(
        track_id=1,
        behavior="WEAPON_THREAT",
        threat_level=ThreatLevel.CRITICAL,
        now=t0 + 1.5,
    ) is False

    # After cooldown period expires, should pass again
    assert throttler.should_dispatch(
        track_id=1,
        behavior="WEAPON_THREAT",
        threat_level=ThreatLevel.CRITICAL,
        now=t0 + 4.0,
    ) is True


def test_webhook_dispatcher_e2e(mock_server):
    """Integration test verifying complete JSON payload sent to external server."""
    cam_cfg = CameraLocationConfig(
        camera_id="CAM_TEST_01",
        name="Cổng An Ninh Số 1",
        zone_id="ZONE_TEST",
        address="123 Phố Đi Bộ, Quận 1",
        latitude=10.776889,
        longitude=106.700806,
    )

    dispatcher = WebhookDispatcher(
        server_url=mock_server,
        camera_config=cam_cfg,
        min_threat_level="ALL",
        cooldown_seconds=1.0,
        timeout=2.0,
    )

    # Create synthetic frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "TEST INCIDENT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # Create synthetic detection result with a WEAPON_THREAT and a HANDS_UP victim
    track1 = HumanPoseTrack(
        track_id=101,
        bbox=BBox(x1=100, y1=120, x2=220, y2=400),
        detection_conf=0.92,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.WEAPON_THREAT,
            confidence=0.95,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.96,
            reasoning="Tactical two-handed aiming posture detected.",
        ),
    )

    track2 = HumanPoseTrack(
        track_id=102,
        bbox=BBox(x1=300, y1=140, x2=410, y2=420),
        detection_conf=0.88,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.HANDS_UP,
            confidence=0.90,
            threat_level=ThreatLevel.HIGH,
            threat_score=0.78,
            reasoning="Hands held up above head in surrender.",
        ),
    )

    analysis = SOCFrameAnalysisResult(
        frame_index=42,
        timestamp="2026-11-07 14:35:00.123",
        human_count=2,
        humans=[track1, track2],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.96,
        critical_events=["WEAPON_THREAT detected on Track #101"],
    )

    # Dispatch event
    enqueued = dispatcher.dispatch_frame_event(
        frame=frame,
        annotated_frame=frame,
        analysis_result=analysis,
    )
    assert enqueued is True

    # Allow worker thread to perform HTTP POST
    time.sleep(0.5)

    # Check mock server received payload
    assert len(MockWebhookHandler.received_requests) >= 1
    received = MockWebhookHandler.received_requests[0]

    # 1. Event & Timestamps
    assert "event_id" in received and received["event_id"].startswith("EVT_")
    assert "timestamp" in received
    assert "timestamp_ms" in received

    # 2. Camera metadata
    cam_data = received["camera"]
    assert cam_data["camera_id"] == "CAM_TEST_01"
    assert cam_data["name"] == "Cổng An Ninh Số 1"
    assert cam_data["latitude"] == pytest.approx(10.776889)
    assert cam_data["longitude"] == pytest.approx(106.700806)
    assert cam_data["address"] == "123 Phố Đi Bộ, Quận 1"

    # 3. Detection metadata
    det = received["detection"]
    assert det["primary_action"] == "WEAPON_THREAT"
    assert det["threat_level"] == "CRITICAL"
    assert det["threat_score"] == pytest.approx(0.96, 0.01)
    assert det["is_urgent"] is True

    # 4. Weapon details
    weapon = det["weapon"]
    assert weapon["is_weapon_detected"] is True
    assert "TACTICAL_WEAPON_POSTURE" in weapon["weapon_types"]

    # 5. Subjects and Crop Images
    subjects = det["subjects"]
    assert len(subjects) == 2

    # Subject 1 (Suspect)
    s1 = next(s for s in subjects if s["track_id"] == 101)
    assert s1["role"] == "suspect"
    assert s1["behavior"] == "WEAPON_THREAT"
    assert s1["crop_image_base64"].startswith("data:image/jpeg;base64,")

    # Subject 2 (Victim)
    s2 = next(s for s in subjects if s["track_id"] == 102)
    assert s2["role"] == "victim"
    assert s2["behavior"] == "HANDS_UP"
    assert s2["crop_image_base64"].startswith("data:image/jpeg;base64,")

    # 6. Full Frame Image
    full_img = det["full_image"]
    assert full_img["format"] == "jpeg"
    assert full_img["width"] == 640
    assert full_img["height"] == 480
    assert full_img["image_base64"].startswith("data:image/jpeg;base64,")

    dispatcher.shutdown()


def test_webhook_dispatcher_offline_unreachable_server():
    """Verify system does not crash or raise exceptions when target server is down."""
    # Port 59998 is not listening
    unreachable_url = "http://127.0.0.1:59998/api/incidents"
    dispatcher = WebhookDispatcher(
        server_url=unreachable_url,
        timeout=0.2,
        max_retries=1,
    )

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    track = HumanPoseTrack(
        track_id=999,
        bbox=BBox(10, 10, 50, 50),
        detection_conf=0.9,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.FIGHTING,
            confidence=0.9,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.95,
            reasoning="Fighting",
        ),
    )
    analysis = SOCFrameAnalysisResult(
        frame_index=1,
        timestamp="2026-11-07 14:35:00.000",
        human_count=1,
        humans=[track],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.95,
    )

    # Must return True for enqueue, and worker thread must handle failure silently
    enqueued = dispatcher.dispatch_frame_event(frame, frame, analysis)
    assert enqueued is True

    time.sleep(0.6)
    assert dispatcher.failed_count >= 1
    assert dispatcher.last_error_message is not None

    dispatcher.shutdown()
