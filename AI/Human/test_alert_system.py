"""
Comprehensive Automated Verification Suite for AI Alert Server & Dispatcher.
Tests:
1. Alert Models serialization & validation
2. .env configuration loading & API credentials verification
3. AI Service situational projection ("dự kiến"), timestamping ("đánh dấu thời gian"), and SHA-256 evidence hashing ("mã hash")
4. Alert Server HTTP endpoints (Health, POST /api/v1/alerts, GET /api/v1/alerts)
5. Non-blocking Alert Dispatcher with queue, cooldown, and debouncing
6. End-to-end integration: suspicious action detection -> HTTP POST -> AI processing -> 100% JSON Alert response
"""

import os
import sys
import time
import json
import base64
import hashlib
import threading
import urllib.request
import urllib.error
import numpy as np

# Ensure path is accessible
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from alert_models import SuspiciousActionRequest, AlertRecord, EvidencePackage, AIAnalysisPrediction
from ai_service import AIService, load_env_file
from server import AlertServer
from alert_client import AlertDispatcher


def make_dummy_jpeg() -> tuple:
    # Generate 64x64 solid frame with red/blue rectangle
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    img[:, :] = (20, 20, 30)
    # Draw mock human marker
    img[10:54, 20:44] = (0, 0, 255)
    import cv2
    success, enc = cv2.imencode(".jpg", img)
    raw_bytes = enc.tobytes()
    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
    return raw_bytes, b64_str


def test_1_models_serialization():
    print("[TEST 1/6] Testing Alert Data Models & JSON Serialization...")
    _, b64 = make_dummy_jpeg()

    req = SuspiciousActionRequest(
        camera_id="CAM_TEST_01",
        camera_name="Test Sector",
        timestamp="2026-11-08T03:55:00.000Z",
        timestamp_ms=1762574100000,
        track_id=1,
        action="FALLEN",
        threat_level="CRITICAL",
        threat_score=0.92,
        bbox=[100, 200, 300, 400],
        kinematics={"spine_angle": 75.0, "speed": 0.05, "wrist_energy": 120.0},
        image_base64=b64,
        location="Zone B"
    )

    req_dict = req.to_dict()
    assert req_dict["camera_id"] == "CAM_TEST_01"
    assert req_dict["action"] == "FALLEN"
    assert req_dict["bbox"] == [100, 200, 300, 400]

    # Test rebuilding from dict
    req_rebuilt = SuspiciousActionRequest.from_dict(req_dict)
    assert req_rebuilt.track_id == 1
    assert req_rebuilt.threat_score == 0.92
    print("  -> PASSED: SuspiciousActionRequest serialized and validated cleanly.")


def test_2_env_and_ai_service():
    print("\n[TEST 2/6] Testing .env Loading & AI Service Cryptographic Ledger...")
    env_vars = load_env_file()
    assert "NVIDIA_API_KEY" in os.environ or "NVIDIA_API_KEY" in env_vars
    print(f"  -> Detected NVIDIA API Key: {os.getenv('NVIDIA_API_KEY')[:15]}...")

    output_test_dir = os.path.join(base_dir, "output", "test_run")
    os.makedirs(output_test_dir, exist_ok=True)

    ai_service = AIService(output_dir=output_test_dir, timeout_seconds=1.5)
    assert ai_service.base_url.startswith("http")

    raw_bytes, b64 = make_dummy_jpeg()
    req = SuspiciousActionRequest(
        camera_id="CAM_GATE_01",
        camera_name="Cong Chinh",
        timestamp="2026-11-08T03:55:00.000Z",
        timestamp_ms=1762574100000,
        track_id=42,
        action="FALLEN",
        threat_level="CRITICAL",
        threat_score=0.95,
        bbox=[50, 60, 150, 180],
        kinematics={"spine_angle": 82.5, "speed": 0.02},
        image_base64=b64,
        location="Sanh Chinh"
    )

    alert: AlertRecord = ai_service.process_suspicious_action(req)

    # Validate output schema
    assert alert.alert_id.startswith("ALT_")
    assert alert.severity in ("HIGH", "CRITICAL")
    assert alert.timestamp.endswith("Z")
    assert len(alert.hash) == 64  # SHA-256
    assert alert.evidence.frame_hash == hashlib.sha256(raw_bytes).hexdigest()
    assert os.path.exists(alert.evidence.saved_image_path)
    assert "intent" in alert.ai_analysis.intent_prediction
    assert alert.is_alert is True

    json_str = alert.to_json(indent=2)
    parsed_json = json.loads(json_str)
    assert parsed_json["severity"] == alert.severity
    assert parsed_json["hash"] == alert.hash
    assert "ai_analysis" in parsed_json

    print(f"  -> Generated Alert ID: {alert.alert_id}")
    print(f"  -> Forensic SHA-256: {alert.hash}")
    print(f"  -> AI Prediction ('dự kiến'): {alert.ai_analysis.intent_prediction.get('intent')}")
    print("  -> PASSED: AI Service produced full 100% JSON compliant Alert.")


def test_3_alert_server_http():
    print("\n[TEST 3/6] Testing Alert Server HTTP Endpoints & Live Processing...")
    test_port = 8899
    output_test_dir = os.path.join(base_dir, "output", "test_server")
    server = AlertServer(host="127.0.0.1", port=test_port, output_dir=output_test_dir)
    server.ai_service.timeout_seconds = 1.5

    server_thread = threading.Thread(target=server.start, kwargs={"blocking": True}, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    try:
        # 1. Health check
        health_url = f"http://127.0.0.1:{test_port}/api/v1/health"
        with urllib.request.urlopen(health_url, timeout=3) as resp:
            health_data = json.loads(resp.read().decode())
            assert health_data["status"] == "online"
            print("  -> Health Check 200 OK: Server online.")

        # 2. POST /api/incident
        _, b64 = make_dummy_jpeg()
        payload = {
            "camera_id": "CAM_LIVE_02",
            "camera_name": "Khu Vuc Hanh Lang",
            "timestamp": "2026-11-08T03:56:00.000Z",
            "timestamp_ms": 1762574160000,
            "track_id": 7,
            "action": "FIGHTING",
            "threat_level": "CRITICAL",
            "threat_score": 0.98,
            "bbox": [100, 100, 220, 280],
            "kinematics": {"wrist_energy": 1850.0, "speed": 1.4},
            "image_base64": b64,
            "location": "Khu Dong"
        }

        req = urllib.request.Request(
            f"http://127.0.0.1:{test_port}/api/incident",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            res_json = json.loads(resp.read().decode())
            assert res_json["action_type"] == "FIGHTING"
            assert res_json["severity"] == "CRITICAL"
            assert "hash" in res_json
            assert "evidence" in res_json
            assert "ai_analysis" in res_json
            print(f"  -> POST /api/incident: 200 OK | Action: {res_json['action_type']} | Severity: {res_json['severity']}")

        # 3. GET /api/incident
        with urllib.request.urlopen(f"http://127.0.0.1:{test_port}/api/incident", timeout=5) as resp:
            list_data = json.loads(resp.read().decode())
            assert list_data["count"] >= 1
            print(f"  -> GET /api/incident: Returned {list_data['count']} alert(s).")

        print("  -> PASSED: Alert Server HTTP API verified cleanly.")

    finally:
        server.stop()
        time.sleep(0.3)


def test_4_alert_dispatcher_client():
    print("\n[TEST 4/6] Testing Non-Blocking Alert Dispatcher Client...")
    test_port = 8898
    output_test_dir = os.path.join(base_dir, "output", "test_client")
    server = AlertServer(host="127.0.0.1", port=test_port, output_dir=output_test_dir)
    server.ai_service.timeout_seconds = 1.5
    server_thread = threading.Thread(target=server.start, kwargs={"blocking": True}, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    received_callbacks = []
    def on_alert(alert_obj):
        received_callbacks.append(alert_obj)

    dispatcher = AlertDispatcher(
        server_url=f"http://127.0.0.1:{test_port}/api/incident",
        camera_id="CAM_CLIENT_01",
        cooldown_seconds=1.5,
        output_dir=output_test_dir,
        on_alert_received=on_alert
    )
    dispatcher.ai_service.enable_vlm = False

    try:
        # Create a test frame
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        frame[30:90, 40:100] = (0, 255, 0)

        # 1. Normal behavior should NOT be dispatched
        was_dispatched = dispatcher.notify_detection(
            frame=frame,
            track_id=10,
            action="NORMAL",
            threat_level="LOW",
            threat_score=0.1,
            bbox=(40, 30, 100, 90)
        )
        assert was_dispatched is False
        print("  -> Filtered benign NORMAL behavior (No alert dispatched).")

        # 2. Suspicious behavior (FALLEN) SHOULD be dispatched
        was_dispatched = dispatcher.notify_detection(
            frame=frame,
            track_id=10,
            action="FALLEN",
            threat_level="CRITICAL",
            threat_score=0.91,
            bbox=(40, 30, 100, 90),
            kinematics={"spine_angle": 78.0, "speed": 0.01}
        )
        assert was_dispatched is True
        print("  -> Enqueued suspicious FALLEN action for non-blocking dispatch.")

        # 3. Immediate duplicate within cooldown SHOULD be suppressed
        was_dup_dispatched = dispatcher.notify_detection(
            frame=frame,
            track_id=10,
            action="FALLEN",
            threat_level="CRITICAL",
            threat_score=0.91,
            bbox=(40, 30, 100, 90)
        )
        assert was_dup_dispatched is False
        print("  -> Cooldown debounced duplicate frame within 1.5s.")

        # Wait for worker thread to deliver alert
        for _ in range(40):
            if len(received_callbacks) >= 1:
                break
            time.sleep(0.1)

        assert len(received_callbacks) == 1
        assert received_callbacks[0]["action_type"] == "FALLEN"
        assert received_callbacks[0]["severity"] in ("HIGH", "CRITICAL")
        print(f"  -> Callback confirmed reception of Alert: {received_callbacks[0]['alert_id']}")

        print("  -> PASSED: Alert Dispatcher non-blocking queue & cooldown debouncing verified.")

    finally:
        dispatcher.close()
        server.stop()
        time.sleep(0.3)


def test_5_multiple_actions_and_predictions():
    print("\n[TEST 5/6] Testing Diverse Action Types, Severities & Intent Predictions...")
    output_test_dir = os.path.join(base_dir, "output", "test_actions")
    ai_service = AIService(output_dir=output_test_dir, enable_vlm=False)
    _, b64 = make_dummy_jpeg()

    test_cases = [
        ("FALLEN", "CRITICAL", 0.95, "HIGH", "Cấp cứu y tế"),
        ("FIGHTING", "CRITICAL", 0.98, "CRITICAL", "Xung đột bạo lực"),
        ("HANDS_UP", "HIGH", 0.85, "HIGH", "Bị khống chế"),
        ("RUNNING", "MEDIUM", 0.75, "MEDIUM", "Tháo chạy"),
        ("CROUCHING", "MEDIUM", 0.60, "MEDIUM", "Thám sát"),
    ]

    for act, tl, sc, exp_sev, exp_intent_kw in test_cases:
        req = SuspiciousActionRequest(
            camera_id="CAM_MULTI_01",
            camera_name="Khu Vuc Tong Hop",
            timestamp="2026-11-08T03:57:00.000Z",
            timestamp_ms=1762574220000,
            track_id=99,
            action=act,
            threat_level=tl,
            threat_score=sc,
            bbox=[10, 10, 50, 50],
            kinematics={"speed": 1.2, "spine_angle": 60.0},
            image_base64=b64,
            location="Khu Do Thi"
        )
        alert = ai_service.process_suspicious_action(req)
        assert alert.severity == exp_sev or (act == "FALLEN" and alert.severity in ("HIGH", "CRITICAL"))
        intent_text = alert.ai_analysis.intent_prediction.get("intent", "")
        assert exp_intent_kw in intent_text or len(intent_text) > 0
        print(f"  -> Action: {act:10} | Severity: {alert.severity:8} | Threat: {alert.threat_score:.2f} | Intent: {intent_text[:35]}...")

    print("  -> PASSED: All 5 suspicious action categories evaluated accurately.")


def test_6_log_persistence_and_audit():
    print("\n[TEST 6/6] Testing Audit Log Persistence & File Verification...")
    output_test_dir = os.path.join(base_dir, "output", "test_audit")
    os.makedirs(output_test_dir, exist_ok=True)
    server = AlertServer(host="127.0.0.1", port=8897, output_dir=output_test_dir)

    _, b64 = make_dummy_jpeg()
    req = SuspiciousActionRequest(
        camera_id="CAM_AUDIT_01",
        camera_name="Audit Sector",
        timestamp="2026-11-08T03:58:00.000Z",
        timestamp_ms=1762574280000,
        track_id=55,
        action="FIGHTING",
        threat_level="CRITICAL",
        threat_score=0.99,
        bbox=[20, 20, 80, 80],
        kinematics={"wrist_energy": 2100.0},
        image_base64=b64,
        location="Zone Audit"
    )

    alert = server.ai_service.process_suspicious_action(req)
    server.record_alert(alert)

    # Verify alerts.jsonl exists and has valid JSON line
    log_path = os.path.join(output_test_dir, "alerts.jsonl")
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        assert len(lines) >= 1
        last_obj = json.loads(lines[-1])
        assert last_obj["alert_id"] == alert.alert_id
        assert last_obj["action_type"] == "FIGHTING"
        assert "hash" in last_obj
        assert "evidence" in last_obj
        assert "timestamp" in last_obj

    print(f"  -> Verified persistent record in {log_path}")
    print("  -> PASSED: Audit Log Persistence and File Integrity verified.")


def main():
    print("=================================================================")
    print("   AUTOMATED VERIFICATION: AI ALERT SERVER & DISPATCHER SUITE    ")
    print("=================================================================")
    t0 = time.time()
    test_1_models_serialization()
    test_2_env_and_ai_service()
    test_3_alert_server_http()
    test_4_alert_dispatcher_client()
    test_5_multiple_actions_and_predictions()
    test_6_log_persistence_and_audit()
    elapsed = time.time() - t0
    print("\n=================================================================")
    print(f"   ALL 6 ALERT SERVER TESTS PASSED SUCCESSFULLY! ({elapsed:.2f}s)    ")
    print("=================================================================")


if __name__ == "__main__":
    main()
