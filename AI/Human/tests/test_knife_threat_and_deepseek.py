"""Unit and integration tests for Sharp Object / Knife Detection and DeepSeek VLM Multimodal Image Delivery."""

import base64
import json
import time
from typing import List

import cv2
import numpy as np

from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import check_knife_threat, evaluate_single_track_behavior
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_EYE,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_EYE,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO
from urbansoc.domain.synthetic import create_synthetic_pose
from urbansoc.domain.webhook_models import (
    CameraLocationConfig,
    SubjectCropData,
    WebhookIncidentPayload,
)
from urbansoc.telemetry.webhook_dispatcher import crop_hand_region, encode_image_and_hash


def test_knife_threat_ready_guard_stance():
    """Verify that a tactical knife guard stance (cocked arm + forward guard) is detected as KNIFE_THREAT."""
    pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="knife_threat")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])

    pred = check_knife_threat(pose, state, history=[], norm_speed=0.2)
    assert pred is not None, "Knife threat should be detected from synthetic knife_threat pose"
    assert pred.primary_behavior == BehaviorType.KNIFE_THREAT
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert pred.threat_score >= 0.93
    assert "knife" in pred.reasoning.lower() or "sharp object" in pred.reasoning.lower()


def test_knife_threat_forward_stabbing_thrust():
    """Verify that rapid forward wrist thrust at mid-torso height is detected as KNIFE_THREAT."""
    bbox = BBox.from_xyxy(100, 100, 180, 300)
    # Stabbing right arm extended forward at chest height
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=140.0, y=120.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=160.0, y=150.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_ELBOW, name="right_elbow", x=190.0, y=165.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=230.0, y=170.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=120.0, y=150.0, confidence=0.95),
        KeypointCOCO(id=LEFT_ELBOW, name="left_elbow", x=110.0, y=180.0, confidence=0.95),
        KeypointCOCO(id=LEFT_WRIST, name="left_wrist", x=110.0, y=210.0, confidence=0.95),
    ]
    pose = HumanPoseTrack(track_id=1, bbox=bbox, detection_conf=0.95, keypoints=kpts)
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    # Simulate high velocity thrust
    state.wrist_velocity = 820.0

    pred = check_knife_threat(pose, state, history=[], norm_speed=0.4)
    assert pred is not None
    assert pred.primary_behavior == BehaviorType.KNIFE_THREAT
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert "stabbing thrust" in pred.reasoning.lower()


def test_crop_hand_region_focused_extraction():
    """Verify crop_hand_region extracts a valid non-empty hand sub-image around active wrist."""
    # Create synthetic frame with drawn circle at wrist
    frame = np.full((480, 640, 3), 50, dtype=np.uint8)
    wrist_x, wrist_y = 320, 240
    cv2.circle(frame, (wrist_x, wrist_y), 15, (0, 0, 255), -1)  # Red marker at wrist

    kpts = [
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=260.0, y=200.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_ELBOW, name="right_elbow", x=290.0, y=220.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=float(wrist_x), y=float(wrist_y), confidence=0.95),
    ]
    pose = HumanPoseTrack(track_id=1, bbox=BBox.from_xyxy(200, 150, 400, 450), detection_conf=0.95, keypoints=kpts)

    hand_crop = crop_hand_region(frame, pose, crop_size=100)
    assert hand_crop is not None
    assert hand_crop.shape[0] > 0 and hand_crop.shape[1] > 0
    assert hand_crop.shape[0] <= 100 and hand_crop.shape[1] <= 100


def test_deepseek_multimodal_payload_schema():
    """Verify that WebhookIncidentPayload produces top-level image fields and DeepSeek-compatible message format."""
    dummy_img = np.full((100, 100, 3), 120, dtype=np.uint8)
    full_b64, full_hash, full_size = encode_image_and_hash(dummy_img, timestamp_ms=1000)
    hand_b64, hand_hash, hand_size = encode_image_and_hash(dummy_img[20:80, 20:80], timestamp_ms=1000)

    payload = WebhookIncidentPayload(
        event_id="EVT_TEST_DEEPSEEK_001",
        timestamp="2026-11-07T17:35:00+07:00",
        timestamp_ms=1794047700000,
        camera=CameraLocationConfig(camera_id="LAPTOP_01", name="Laptop Gate"),
        primary_action="KNIFE_THREAT",
        threat_level="CRITICAL",
        threat_score=0.96,
        is_urgent=True,
        reasoning="Rapid stabbing forward thrust detected",
        weapon={"is_weapon_detected": True, "weapon_type": "SHARP_OBJECT_KNIFE"},
        subjects=[],
        full_image={"format": "jpeg", "width": 100, "height": 100, "image_base64": full_b64, "sha256_hash": full_hash, "image_size_bytes": full_size},
        hand_crop_image_base64=hand_b64,
        hand_crop_image_sha256=hand_hash,
    )

    data = payload.to_dict()

    # 1. Direct top-level image keys for DeepSeek
    assert "image" in data
    assert data["image"].startswith("data:image/jpeg;base64,")
    assert "image_base64" in data
    assert "hand_crop_base64" in data
    assert data["hand_crop_base64"].startswith("data:image/jpeg;base64,")
    assert "image_url" in data
    assert data["image_url"] == "/api/v1/incidents/EVT_TEST_DEEPSEEK_001/image.jpg"
    assert "ai_prompt" in data
    assert "KNIFE_THREAT" in data["ai_prompt"]

    # 2. OpenAI / DeepSeek multimodal message structure
    assert "deepseek_message" in data
    msg = data["deepseek_message"]
    assert msg["role"] == "user"
    assert isinstance(msg["content"], list)
    assert len(msg["content"]) >= 2  # Text prompt + image_url(s)

    types = [item["type"] for item in msg["content"]]
    assert "text" in types
    assert "image_url" in types

    # 3. Backward compatibility
    assert "detection" in data
    assert data["detection"]["primary_action"] == "KNIFE_THREAT"
    assert "full_image" in data["detection"]


def test_inference_server_serves_deepseek_images(tmp_path):
    """Verify that InferenceServer saves incident images and serves them via HTTP GET for DeepSeek."""
    import urllib.request
    from urbansoc.server.inference_server import InferenceServer

    server = InferenceServer(
        host="127.0.0.1",
        port=8099,
        output_dir=str(tmp_path),
        webhook_url=None,
    )
    server.start(blocking=False)
    time.sleep(0.3)

    try:
        # 1. Post simulated incident payload with full_frame and hand_crop
        dummy_img = np.full((120, 160, 3), 75, dtype=np.uint8)
        cv2.putText(dummy_img, "TEST", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        full_b64, full_hash, _ = encode_image_and_hash(dummy_img, timestamp_ms=1000)
        hand_b64, hand_hash, _ = encode_image_and_hash(dummy_img[30:90, 30:90], timestamp_ms=1000)

        event_id = "EVT_DEEPSEEK_INTEG_TEST"
        payload = {
            "event_id": event_id,
            "timestamp_ms": 1000,
            "camera": {"camera_id": "TEST_CAM"},
            "hand_crop_base64": hand_b64,
            "detection": {
                "full_image": {
                    "image_base64": full_b64,
                    "sha256_hash": full_hash,
                }
            }
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8099/api/v1/incidents",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200

        # 2. GET /api/v1/incidents/{event_id}/image.jpg
        img_url = f"http://127.0.0.1:8099/api/v1/incidents/{event_id}/image.jpg"
        with urllib.request.urlopen(img_url, timeout=2.0) as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "image/jpeg"
            data = resp.read()
            assert len(data) > 100

        # 3. GET /api/v1/incidents/{event_id}/hand_crop.jpg
        hand_url = f"http://127.0.0.1:8099/api/v1/incidents/{event_id}/hand_crop.jpg"
        with urllib.request.urlopen(hand_url, timeout=2.0) as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "image/jpeg"
            data = resp.read()
            assert len(data) > 100

    finally:
        server.stop()
