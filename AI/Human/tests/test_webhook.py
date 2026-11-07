"""Unit and integration tests for Webhook Event Dispatcher, Anti-Noise Filtering, and Forensic SHA-256."""

import base64
import hashlib
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
from urbansoc.domain.keypoints import COCO_KEYPOINT_NAMES
from urbansoc.domain.schemas import (
    BehaviorPrediction,
    HumanPoseTrack,
    KeypointCOCO,
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
    compute_forensic_sha256,
    crop_subject_image,
    encode_image_and_hash,
    extract_subject_kinematics,
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
    frame[100:200, 150:250] = (0, 255, 0)
    bbox = BBox(x1=150, y1=100, x2=250, y2=200)

    crop = crop_subject_image(frame, bbox, margin=0.10)
    assert crop is not None
    assert crop.shape[0] > 0
    assert crop.shape[1] > 0
    assert 110 <= crop.shape[1] <= 130
    assert 110 <= crop.shape[0] <= 130


def test_crop_subject_image_boundary_clamping():
    """Test cropping near frame borders does not throw IndexError."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
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
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    assert crop_subject_image(frame, BBox(50, 50, 20, 20)) is None


def test_compute_forensic_sha256():
    """Test forensic SHA-256 calculation combining image bytes and millisecond timestamp."""
    raw_bytes = b"TEST_IMAGE_BYTES_XYZ"
    timestamp_ms = 1794038100123

    computed_hash = compute_forensic_sha256(raw_bytes, timestamp_ms)
    assert len(computed_hash) == 64  # SHA-256 hex digest length

    # Verify recalculation matches exactly
    hasher = hashlib.sha256()
    hasher.update(raw_bytes)
    hasher.update(str(timestamp_ms).encode("utf-8"))
    assert computed_hash == hasher.hexdigest()

    # Tampered bytes must produce different hash
    tampered_hash = compute_forensic_sha256(b"TAMPERED_BYTES", timestamp_ms)
    assert tampered_hash != computed_hash

    # Different timestamp must produce different hash
    different_time_hash = compute_forensic_sha256(raw_bytes, timestamp_ms + 1)
    assert different_time_hash != computed_hash


def test_encode_image_and_hash():
    """Test encoding image to Base64, computing SHA-256, and decoding image."""
    test_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    timestamp_ms = 1794038100000
    b64_url, sha_hash, size_bytes = encode_image_and_hash(test_img, timestamp_ms, quality=80)

    assert b64_url.startswith("data:image/jpeg;base64,")
    assert len(sha_hash) == 64
    assert size_bytes > 0

    raw_b64 = b64_url.split(",", 1)[1]
    img_bytes = base64.b64decode(raw_b64)
    assert len(img_bytes) == size_bytes

    # Recalculate hash on extracted bytes to verify consistency
    verify_hash = compute_forensic_sha256(img_bytes, timestamp_ms)
    assert verify_hash == sha_hash

    # Decode back with OpenCV to verify image validity
    decoded = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape == (100, 100, 3)

    # Empty image check
    empty_url, empty_hash, empty_sz = encode_image_and_hash(None, timestamp_ms)
    assert empty_url == ""
    assert empty_hash == ""
    assert empty_sz == 0


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


def test_anti_noise_filtering_rejects_low_conf_and_small_boxes(mock_server):
    """Verify that noisy detections (low confidence or tiny bbox) are filtered out."""
    dispatcher = WebhookDispatcher(
        server_url=mock_server,
        min_detection_conf=0.35,
        min_bbox_area=1200,
        filter_noise=True,
    )

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Noisy track with very low detection confidence (0.20 < 0.35)
    noise_track_low_conf = HumanPoseTrack(
        track_id=901,
        bbox=BBox(x1=100, y1=100, x2=200, y2=300),  # good area
        detection_conf=0.20,  # below 0.35 threshold
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.FIGHTING,
            confidence=0.95,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.95,
            reasoning="Low confidence glitch",
        ),
    )

    # 2. Noisy track with tiny bbox area (width=10, height=20, area=200 < 1200)
    noise_track_tiny_box = HumanPoseTrack(
        track_id=902,
        bbox=BBox(x1=50, y1=50, x2=60, y2=70),
        detection_conf=0.90,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.WEAPON_THREAT,
            confidence=0.95,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.96,
            reasoning="Tiny distant blur",
        ),
    )

    noisy_analysis = SOCFrameAnalysisResult(
        frame_index=1,
        timestamp="2026-11-07 14:55:00.000",
        human_count=2,
        humans=[noise_track_low_conf, noise_track_tiny_box],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.96,
    )

    # Dispatched should be False because all candidates were filtered as noise
    enqueued = dispatcher.dispatch_frame_event(frame, frame, noisy_analysis)
    assert enqueued is False
    assert dispatcher.filtered_noise_count >= 2

    dispatcher.shutdown()


def test_webhook_dispatcher_e2e_with_forensic_hash_and_all_telemetry(mock_server):
    """Integration test verifying complete JSON payload with 17 keypoints, kinematics, and SHA-256."""
    cam_cfg = CameraLocationConfig(
        camera_id="CAM_FORENSIC_01",
        name="Cổng An Ninh Số 1",
        zone_id="ZONE_ALPHA",
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
        min_detection_conf=0.35,
        min_bbox_area=1200,
        filter_noise=True,
    )

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "CRIME EVIDENCE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # Create synthetic 17 COCO keypoints for suspect
    suspect_keypoints = [
        KeypointCOCO(id=i, name=COCO_KEYPOINT_NAMES[i], x=150.0 + i * 2, y=200.0 + i * 5, confidence=0.90)
        for i in range(17)
    ]

    suspect_track = HumanPoseTrack(
        track_id=101,
        bbox=BBox(x1=100, y1=120, x2=220, y2=400),
        detection_conf=0.92,
        keypoints=suspect_keypoints,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.WEAPON_THREAT,
            confidence=0.95,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.96,
            reasoning="Tactical two-handed aiming posture detected.",
        ),
        dwell_time_seconds=3.75,
    )

    analysis = SOCFrameAnalysisResult(
        frame_index=10,
        timestamp="2026-11-07 14:55:00.123",
        human_count=1,
        humans=[suspect_track],
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

    time.sleep(0.5)

    assert len(MockWebhookHandler.received_requests) >= 1
    received = MockWebhookHandler.received_requests[0]

    # 1. Event, Timestamps, and Audit
    assert "event_id" in received and received["event_id"].startswith("EVT_")
    timestamp_ms = received["timestamp_ms"]
    assert timestamp_ms > 0

    audit = received["audit"]
    assert "SHA-256" in audit["hash_algorithm"]
    assert audit["anti_noise_filtering"]["enabled"] is True

    # 2. Full Frame Image and Forensic SHA-256 Verification
    full_img = received["detection"]["full_image"]
    assert full_img["format"] == "jpeg"
    assert full_img["width"] == 640
    assert full_img["height"] == 480
    assert "sha256_hash" in full_img
    full_sha = full_img["sha256_hash"]
    assert len(full_sha) == 64

    # Verify SHA-256 on full frame bytes
    full_raw_bytes = base64.b64decode(full_img["image_base64"].split(",", 1)[1])
    computed_full_sha = compute_forensic_sha256(full_raw_bytes, timestamp_ms)
    assert computed_full_sha == full_sha, "Full image cryptographic hash mismatch!"

    # 3. Comprehensive Subject Telemetry
    subjects = received["detection"]["subjects"]
    assert len(subjects) == 1
    s1 = subjects[0]

    assert s1["track_id"] == 101
    assert s1["role"] == "suspect"
    assert s1["behavior"] == "WEAPON_THREAT"
    assert s1["threat_level"] == "CRITICAL"
    assert s1["threat_score"] == pytest.approx(0.96, 0.01)

    # BBox geometry
    geom = s1["bbox_geometry"]
    assert geom["width"] == 120
    assert geom["height"] == 280
    assert geom["area"] == 120 * 280
    assert s1["dwell_time_seconds"] == pytest.approx(3.75, 0.01)

    # Kinematics
    kine = s1["kinematics"]
    assert "spine_angle" in kine
    assert "left_elbow_angle" in kine
    assert "right_elbow_angle" in kine
    assert "left_arm_extension" in kine
    assert "wrist_distance" in kine

    # All 17 Keypoints
    kps = s1["keypoints"]
    assert len(kps) == 17
    assert kps[0]["name"] == "nose"
    assert "x" in kps[0] and "y" in kps[0] and "confidence" in kps[0]

    # Crop Image and Forensic SHA-256 Verification
    crop_b64 = s1["crop_image_base64"]
    crop_sha = s1["crop_image_sha256"]
    assert len(crop_sha) == 64

    crop_raw_bytes = base64.b64decode(crop_b64.split(",", 1)[1])
    computed_crop_sha = compute_forensic_sha256(crop_raw_bytes, timestamp_ms)
    assert computed_crop_sha == crop_sha, "Subject crop cryptographic hash mismatch!"

    dispatcher.shutdown()


def test_webhook_dispatcher_offline_unreachable_server():
    """Verify system does not crash or raise exceptions when target server is down."""
    unreachable_url = "http://127.0.0.1:59998/api/incidents"
    dispatcher = WebhookDispatcher(
        server_url=unreachable_url,
        timeout=0.2,
        max_retries=1,
    )

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    track = HumanPoseTrack(
        track_id=999,
        bbox=BBox(10, 10, 100, 150),
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
        timestamp="2026-11-07 14:55:00.000",
        human_count=1,
        humans=[track],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.95,
    )

    enqueued = dispatcher.dispatch_frame_event(frame, frame, analysis)
    assert enqueued is True

    time.sleep(0.6)
    assert dispatcher.failed_count >= 1
    assert dispatcher.last_error_message is not None

    dispatcher.shutdown()


def test_webhook_ai_verification_suppresses_false_positive():
    """Verify that when AI multimodal falsification rejects action as false positive, NO POST is sent."""
    dispatcher = WebhookDispatcher(server_url="http://127.0.0.1:59999/api/incidents")
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    track = HumanPoseTrack(
        track_id=1,
        bbox=BBox(10, 10, 100, 150),
        detection_conf=0.9,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.WEAPON_THREAT,
            confidence=0.9,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.95,
            reasoning="Suspected weapon",
        ),
    )
    analysis = SOCFrameAnalysisResult(
        frame_index=1,
        timestamp="2026-11-08 04:00:00.000",
        human_count=1,
        humans=[track],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.95,
    )

    # AI Multimodal analysis indicates false positive (e.g. umbrella/phone suppressed by Gate 3/5)
    mock_suppressed_vlm = {
        "false_positive_suppressed": True,
        "suppression_explanation": "Đối tượng cầm ô dù che mưa, không phải hung khí nguy hiểm.",
        "severity": "low",
        "primary_action": "NORMAL",
        "threat_score": 0.05,
        "anti_false_positive_audit": {
            "false_positive_suppressed": True,
            "suppression_reason": "Gate 3 rejected weapon morphology; holding umbrella.",
        },
    }

    enqueued = dispatcher.dispatch_frame_event(
        frame=frame,
        annotated_frame=frame,
        analysis_result=analysis,
        vlm_result=mock_suppressed_vlm,
    )
    # MUST BE BLOCKED: NO POST REQUEST ENQUEUED OR SENT
    assert enqueued is False
    assert dispatcher.queue.empty() is True

    dispatcher.shutdown()


def test_webhook_ai_verification_confirms_threat_and_includes_crops():
    """Verify that when AI confirms the action on the image, POST request is enqueued with subject crops."""
    dispatcher = WebhookDispatcher(server_url="http://127.0.0.1:59999/api/incidents")
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    track = HumanPoseTrack(
        track_id=2,
        bbox=BBox(20, 20, 120, 180),
        detection_conf=0.95,
        behavior=BehaviorPrediction(
            primary_behavior=BehaviorType.WEAPON_THREAT,
            confidence=0.95,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.95,
            reasoning="Tactical 2-handed firearm posture",
        ),
    )
    analysis = SOCFrameAnalysisResult(
        frame_index=2,
        timestamp="2026-11-08 04:00:01.000",
        human_count=1,
        humans=[track],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.95,
    )

    # AI Multimodal analysis verifies action is genuine threat
    mock_verified_vlm = {
        "false_positive_suppressed": False,
        "severity": "critical",
        "action_type": "WEAPON_THREAT",
        "primary_action": "WEAPON_THREAT",
        "threat_score": 0.95,
        "confidence": 0.96,
        "reasoning": "Detected action: WEAPON_THREAT. Subject aiming posture with 2-handed forward grip. Falsification passed.",
        "anti_false_positive_audit": {
            "false_positive_suppressed": False,
            "gate_5_adversarial_benign_hypothesis": {
                "benign_hypothesis_probability": 0.08,
                "escalation_permitted": True,
            },
        },
    }

    enqueued = dispatcher.dispatch_frame_event(
        frame=frame,
        annotated_frame=frame,
        analysis_result=analysis,
        vlm_result=mock_verified_vlm,
    )
    assert enqueued is True
    assert dispatcher.queue.empty() is False

    payload = dispatcher.queue.get_nowait()
    assert payload["action_confirmed"] is True
    assert payload["ai_verified"] is True
    assert payload["primary_action"] == "WEAPON_THREAT"
    assert payload["threat_level"] == "CRITICAL"
    assert "subject_crop_base64" in payload
    assert "image_base64" in payload
    assert "hand_crop_base64" in payload
    assert "forensic_hash" in payload
    assert payload["reasoning"] == mock_verified_vlm["reasoning"]
    assert payload["detection"]["action_confirmed"] is True
    assert payload["audit"]["verification_status"] == "AUTO_DISPATCHED_TO_AI_MODEL"

    dispatcher.shutdown()
