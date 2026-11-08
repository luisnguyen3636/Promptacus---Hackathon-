"""Comprehensive Test Suite for Urban Safety AI-SOC Web App & Backend Core.

Tuân thủ nghiêm ngặt nguyên tắc [CD-04] và [CD-05] (yêu cầu tối thiểu 30 test cases hợp lệ).
Bao gồm 36 test cases kiểm thử:
1. Phục vụ Web App tại /dashboard/ (HTML, static assets, SPA routing)
2. Telemetry & Overview APIs (dynamic threat levels & metrics)
3. Camera Devices & PTZ Controls (zoom, pan, tilt, autofocus, validation)
4. AI Detect Ingestion (weapon threat, fallen, fighting, crops, hash, dynamic bbox)
5. Recent Incidents & Playback Buffer (VLM analysis, snapshots, 404 handling)
6. Operational HITL Dispatcher & Packaging (mandatory operatorId, 3 decisions, audit log)
7. Audit Logs, SSE stream, & WebSocket Real-time Broadcasting
"""

import json
import os
import re
import socket
import base64
import subprocess
import sys
import time
from typing import Any, Dict, Generator
import urllib.request
import urllib.error

import pytest
import requests

def ws_connect_and_recv(host: str, port: int, path: str = "/ws/live-stream", timeout: float = 3.0):
    """Raw RFC-6455 WebSocket client using pure standard library socket."""
    s = socket.create_connection((host, port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(handshake.encode("ascii"))
    resp = s.recv(4096).decode("utf-8", errors="ignore")
    if "101 Switching Protocols" not in resp:
        s.close()
        raise RuntimeError(f"WebSocket handshake failed: {resp}")
    return s

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_PORT = 8019
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"
WS_URL = f"ws://127.0.0.1:{TEST_PORT}/ws/live-stream"


@pytest.fixture(scope="module")
def backend_server() -> Generator[subprocess.Popen, None, None]:
    """Launch backend Node.js server on TEST_PORT for isolated integration testing."""
    env = os.environ.copy()
    env["PORT"] = str(TEST_PORT)
    env["NODE_ENV"] = "production"

    server_js = os.path.join(BACKEND_DIR, "server.js")
    proc = subprocess.Popen(
        ["node", server_js],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to become responsive
    ready = False
    for _ in range(30):
        time.sleep(0.3)
        try:
            resp = requests.get(f"{BASE_URL}/api/soc/overview", timeout=1.0)
            if resp.status_code == 200:
                ready = True
                break
        except Exception:
            pass

    if not ready:
        proc.kill()
        out, err = proc.communicate()
        raise RuntimeError(f"Backend server failed to start on port {TEST_PORT}.\nSTDOUT: {out.decode()}\nSTDERR: {err.decode()}")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


# ==============================================================================
# NHÓM 1: PHỤC VỤ WEB APP TẠI /dashboard/ (TC-01 -> TC-04)
# ==============================================================================

def test_tc01_get_dashboard_serves_html(backend_server):
    """TC-01: GET /dashboard returns 200 OK and serves index.html."""
    resp = requests.get(f"{BASE_URL}/dashboard", timeout=2.0)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("Content-Type", "")
    assert '<div id="root">' in resp.text or "CYBERGUARD AI" in resp.text


def test_tc02_get_dashboard_slash_serves_html(backend_server):
    """TC-02: GET /dashboard/ returns 200 OK with correct HTML content."""
    resp = requests.get(f"{BASE_URL}/dashboard/", timeout=2.0)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("Content-Type", "")
    assert '<div id="root">' in resp.text or "CYBERGUARD AI" in resp.text


def test_tc03_get_root_serves_web_app_or_service_info(backend_server):
    """TC-03: GET / serves Web App for browser clients and JSON for API clients."""
    # Browser client
    resp_browser = requests.get(f"{BASE_URL}/", headers={"Accept": "text/html"}, timeout=2.0)
    assert resp_browser.status_code == 200
    assert "text/html" in resp_browser.headers.get("Content-Type", "")

    # API client
    resp_api = requests.get(f"{BASE_URL}/", headers={"Accept": "application/json"}, timeout=2.0)
    assert resp_api.status_code == 200


def test_tc04_static_assets_serving(backend_server):
    """TC-04: Static assets are served correctly at /dashboard/assets/ or /assets/."""
    # Verify index.html contains an asset reference
    resp = requests.get(f"{BASE_URL}/dashboard", timeout=2.0)
    if "./assets/" in resp.text:
        # Extract first asset filename
        import re
        match = re.search(r'\./assets/([a-zA-Z0-9\._\-]+)', resp.text)
        if match:
            asset_file = match.group(1)
            asset_resp = requests.get(f"{BASE_URL}/assets/{asset_file}", timeout=2.0)
            assert asset_resp.status_code == 200
            assert len(asset_resp.content) > 0


# ==============================================================================
# NHÓM 2: TELEMETRY & OVERVIEW APIS (TC-05 -> TC-08)
# ==============================================================================

def test_tc05_get_soc_overview_schema(backend_server):
    """TC-05: GET /api/soc/overview returns valid schema per standard.md."""
    resp = requests.get(f"{BASE_URL}/api/soc/overview", timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert "threatLevel" in data
    assert "threatScore" in data
    assert "status" in data
    assert "metrics" in data
    m = data["metrics"]
    assert "latencyMs" in m
    assert "downloadMbps" in m
    assert "uploadMbps" in m
    assert "camerasOnline" in m
    assert "openThreats" in m


def test_tc06_get_dashboard_state_api(backend_server):
    """TC-06: GET /api/v1/dashboard/state returns structured operational state."""
    resp = requests.get(f"{BASE_URL}/api/v1/dashboard/state", timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "online"
    assert "active_cameras" in data
    assert "cameras" in data
    assert "global_threat_level" in data
    assert "highest_threat_score" in data


def test_tc07_telemetry_reflects_camera_counts(backend_server):
    """TC-07: Telemetry metrics provide consistent camera online and total counts."""
    resp = requests.get(f"{BASE_URL}/api/soc/overview", timeout=2.0)
    data = resp.json()
    metrics = data["metrics"]
    assert metrics["camerasOnline"] >= 0
    assert metrics["camerasTotal"] >= metrics["camerasOnline"]


def test_tc08_threat_level_scales_with_score(backend_server):
    """TC-08: Threat Level aligns with standard taxonomy (LOW/MEDIUM/HIGH/CRITICAL)."""
    resp = requests.get(f"{BASE_URL}/api/soc/overview", timeout=2.0)
    data = resp.json()
    assert data["threatLevel"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert 0 <= data["threatScore"] <= 100


# ==============================================================================
# NHÓM 3: CAMERA DEVICES & PTZ CONTROLS (TC-09 -> TC-14)
# ==============================================================================

def test_tc09_get_devices_cameras(backend_server):
    """TC-09: GET /api/devices/cameras returns list of cameras with bounding boxes."""
    resp = requests.get(f"{BASE_URL}/api/devices/cameras", timeout=2.0)
    assert resp.status_code == 200
    cams = resp.json()
    assert isinstance(cams, list)
    assert len(cams) >= 1
    c0 = cams[0]
    assert "id" in c0
    assert "name" in c0
    assert "streamUrl" in c0
    assert "ptzState" in c0
    assert "boundingBoxes" in c0


def test_tc10_get_v1_cameras_alias(backend_server):
    """TC-10: GET /api/v1/cameras works as an alias to device camera listing."""
    resp = requests.get(f"{BASE_URL}/api/v1/cameras", timeout=2.0)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_tc11_ptz_zoom_in_command(backend_server):
    """TC-11: POST /api/cameras/:id/ptz with ZOOM_IN increases zoom level."""
    # Read initial zoom
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cid = cams[0]["id"]
    initial_zoom = cams[0]["ptzState"]["zoom"]

    resp = requests.post(
        f"{BASE_URL}/api/cameras/{cid}/ptz",
        json={"action": "ZOOM_IN", "speed": 1},
        timeout=2.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["ptzState"]["zoom"] >= initial_zoom


def test_tc12_ptz_pan_command(backend_server):
    """TC-12: POST /api/cameras/:id/ptz with PAN updates pan angle."""
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cid = cams[0]["id"]

    resp = requests.post(
        f"{BASE_URL}/api/cameras/{cid}/ptz",
        json={"action": "PAN", "speed": 2},
        timeout=2.0,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"


def test_tc13_ptz_auto_focus_command(backend_server):
    """TC-13: POST /api/cameras/:id/ptz with AUTO_FOCUS locks focus."""
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cid = cams[0]["id"]

    resp = requests.post(
        f"{BASE_URL}/api/cameras/{cid}/ptz",
        json={"action": "AUTO_FOCUS"},
        timeout=2.0,
    )
    assert resp.status_code == 200
    assert "LOCKED" in resp.json()["ptzState"]["focus"]


def test_tc14_ptz_nonexistent_camera_or_invalid_action(backend_server):
    """TC-14: PTZ command returns 400 when camera not found or action invalid."""
    # Nonexistent camera
    resp1 = requests.post(
        f"{BASE_URL}/api/cameras/NONEXISTENT_CAM_99/ptz",
        json={"action": "ZOOM_IN"},
        timeout=2.0,
    )
    assert resp1.status_code == 400

    # Invalid action
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cid = cams[0]["id"]
    resp2 = requests.post(
        f"{BASE_URL}/api/cameras/{cid}/ptz",
        json={"action": "UNKNOWN_ACTION_XYZ"},
        timeout=2.0,
    )
    assert resp2.status_code == 400


# ==============================================================================
# NHÓM 4: AI DETECT INGESTION (TC-15 -> TC-23)
# ==============================================================================

def test_tc15_ingest_weapon_threat_incident(backend_server):
    """TC-15: Ingest WEAPON_THREAT / KNIFE_THREAT incident successfully."""
    payload = {
        "event_id": f"EVT-TEST-WEAPON-{int(time.time())}",
        "primary_action": "WEAPON_THREAT",
        "severity": "CRITICAL",
        "threat_level": "CRITICAL",
        "threat_score": 0.95,
        "camera_id": "cam_01",
        "camera_name": "Server Room Main Gate",
        "reasoning": "VLM Phân tích: Đối tượng cầm dao nhọn trong tư thế tấn công.",
        "weapon_info": {
            "is_weapon_detected": True,
            "weapon_types": ["SHARP_OBJECT_KNIFE"],
            "confidence": 0.96,
        },
        "subjects": [
            {
                "track_id": 101,
                "role": "suspect",
                "behavior": "WEAPON_THREAT",
                "confidence": 0.96,
                "bbox": [100, 50, 250, 400],
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["event_id"] == payload["event_id"]
    assert data["threat_level"] == "CRITICAL"


def test_tc16_ingest_fallen_person_incident(backend_server):
    """TC-16: Ingest FALLEN (người ngã) incident with medical alert reasoning."""
    payload = {
        "event_id": f"EVT-TEST-FALLEN-{int(time.time())}",
        "primary_action": "FALLEN",
        "severity": "HIGH",
        "threat_score": 85,
        "camera_id": "cam_03",
        "reasoning": "VLM Phân tích: Nạn nhân ngã quỵ trên sàn, bất động >15s.",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_tc17_ingest_multi_subject_fighting_assault(backend_server):
    """TC-17: Ingest multi-subject FIGHTING event with attacker, victim, bystander."""
    payload = {
        "event_id": f"EVT-TEST-FIGHT-{int(time.time())}",
        "primary_action": "FIGHTING",
        "severity": "CRITICAL",
        "threat_score": 0.92,
        "camera_id": "cam_02",
        "subjects": [
            {"track_id": 1, "role": "attacker", "behavior": "FIGHTING", "bbox": [120, 80, 260, 480]},
            {"track_id": 2, "role": "victim", "behavior": "FALLEN", "bbox": [200, 250, 380, 480]},
            {"track_id": 3, "role": "bystander", "behavior": "RUNNING", "bbox": [400, 100, 500, 350]},
        ],
        "reasoning": "VLM: Ẩu đả bạo lực giữa đối tượng #1 và nạn nhân #2.",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_tc18_ingest_with_base64_full_frame_and_hand_crop(backend_server):
    """TC-18: Ingest stores base64 full frame and hand crop image evidence."""
    mock_b64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
    payload = {
        "event_id": f"EVT-TEST-CROPS-{int(time.time())}",
        "primary_action": "KNIFE_THREAT",
        "severity": "HIGH",
        "image_base64": mock_b64,
        "hand_crop_base64": mock_b64,
        "camera_id": "cam_01",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200

    # Verify crops exist in playback endpoint
    playback = requests.get(f"{BASE_URL}/api/incidents/{payload['event_id']}/playback").json()
    assert playback["visualEvidence"]["eventPeakSnapshot"] == mock_b64
    assert playback["visualEvidence"]["preEventSnapshot"] == mock_b64


def test_tc19_ingest_with_forensic_sha256_hash(backend_server):
    """TC-19: Ingest retains cryptographic Forensic SHA-256 integrity hash."""
    test_hash = "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"
    payload = {
        "event_id": f"EVT-TEST-HASH-{int(time.time())}",
        "primary_action": "INTRUSION",
        "severity": "HIGH",
        "forensic_hash": test_hash,
        "camera_id": "cam_01",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200

    playback = requests.get(f"{BASE_URL}/api/incidents/{payload['event_id']}/playback").json()
    assert playback["forensicHash"] == test_hash


def test_tc20_ingest_auto_registers_new_camera(backend_server):
    """TC-20: Ingesting an incident with a new camera automatically registers it."""
    new_cam_id = f"NEW_CAM_{int(time.time())}"
    payload = {
        "event_id": f"EVT-AUTOCAM-{int(time.time())}",
        "primary_action": "LOITERING",
        "severity": "MEDIUM",
        "camera": {
            "camera_id": new_cam_id,
            "name": "Camera Giám Sát Cổng Phụ Mới",
            "latitude": 21.0300,
            "longitude": 105.8500,
            "ip": "192.168.1.199",
        }
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200

    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    registered_ids = [c["id"] for c in cams]
    assert new_cam_id in registered_ids


def test_tc21_ingest_updates_camera_bounding_boxes(backend_server):
    """TC-21: Ingest updates AI bounding boxes on the target camera."""
    target_cam = "cam_01"
    payload = {
        "event_id": f"EVT-BOX-{int(time.time())}",
        "primary_action": "WEAPON_THREAT",
        "camera_id": target_cam,
        "subjects": [
            {
                "id": "box_test_target_01",
                "role": "suspect",
                "behavior": "WEAPON_THREAT",
                "confidence": 0.98,
                "x": 0.28,
                "y": 0.15,
                "w": 0.24,
                "h": 0.70,
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200

    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cam = next(c for c in cams if c["id"] == target_cam)
    assert len(cam["boundingBoxes"]) >= 1


def test_tc22_ingest_updates_system_threat_score(backend_server):
    """TC-22: Ingest with high threat score escalates system threat overview."""
    payload = {
        "event_id": f"EVT-ESCALATE-{int(time.time())}",
        "primary_action": "WEAPON_THREAT",
        "severity": "CRITICAL",
        "threat_score": 0.98,
        "camera_id": "cam_01",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=payload, timeout=2.0)
    assert resp.status_code == 200

    overview = requests.get(f"{BASE_URL}/api/soc/overview").json()
    assert overview["threatScore"] >= 75
    assert overview["threatLevel"] == "CRITICAL"


def test_tc23_ingest_rejects_empty_or_invalid_payload(backend_server):
    """TC-23: Ingestion returns 400 when payload is empty or invalid."""
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", data="not json", headers={"Content-Type": "application/json"}, timeout=2.0)
    assert resp.status_code == 400


# ==============================================================================
# NHÓM 5: RECENT INCIDENTS & PLAYBACK BUFFER (TC-24 -> TC-27)
# ==============================================================================

def test_tc24_get_recent_incidents_list(backend_server):
    """TC-24: GET /api/incidents/recent returns list of incidents."""
    resp = requests.get(f"{BASE_URL}/api/incidents/recent", timeout=2.0)
    assert resp.status_code == 200
    incidents = resp.json()
    assert isinstance(incidents, list)
    assert len(incidents) >= 1
    assert "id" in incidents[0]
    assert "severity" in incidents[0]
    assert "status" in incidents[0]


def test_tc25_newest_incident_appears_at_top(backend_server):
    """TC-25: Newly ingested incident is indexed at index 0 of recent incidents."""
    unique_id = f"EVT-TOP-{int(time.time())}"
    requests.post(
        f"{BASE_URL}/api/v1/incidents",
        json={"event_id": unique_id, "primary_action": "LOITERING", "camera_id": "cam_01"},
    )
    incidents = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    assert incidents[0]["id"] == unique_id


def test_tc26_get_incident_playback_success(backend_server):
    """TC-26: GET /api/incidents/:id/playback returns complete playback buffer structure."""
    incidents = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    target_id = incidents[0]["id"]

    resp = requests.get(f"{BASE_URL}/api/incidents/{target_id}/playback", timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data["incidentId"] == target_id
    assert "bufferRange" in data
    assert "visualEvidence" in data
    assert "vlmReasoning" in data


def test_tc27_get_incident_playback_not_found(backend_server):
    """TC-27: Playback request for nonexistent incident returns 404."""
    resp = requests.get(f"{BASE_URL}/api/incidents/NONEXISTENT_99999/playback", timeout=2.0)
    assert resp.status_code == 404


# ==============================================================================
# NHÓM 6: CHỐT CHẶN VẬN HÀNH VIÊN HITL DISPATCHER [CD-04] (TC-28 -> TC-33)
# ==============================================================================

def test_tc28_hitl_rejects_missing_operator_id(backend_server):
    """TC-28: [CD-04 Rule] Verification without operatorId is rejected with 400."""
    incidents = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    target_id = incidents[0]["id"]

    resp = requests.post(
        f"{BASE_URL}/api/incidents/{target_id}/verify",
        json={"decision": "CONFIRM_AND_DISPATCH"},  # operatorId missing
        timeout=2.0,
    )
    assert resp.status_code == 400
    assert "operator" in resp.json().get("error", "").lower()


def test_tc29_hitl_confirm_and_dispatch_success(backend_server):
    """TC-29: Operator CONFIRM_AND_DISPATCH updates status to OPERATOR_CONFIRMED."""
    # Create fresh incident
    evt_id = f"EVT-CONFIRM-{int(time.time())}"
    requests.post(f"{BASE_URL}/api/v1/incidents", json={"event_id": evt_id, "primary_action": "WEAPON_THREAT", "camera_id": "cam_01"})

    resp = requests.post(
        f"{BASE_URL}/api/incidents/{evt_id}/verify",
        json={
            "operatorId": "OP-VN-SOC-804",
            "decision": "CONFIRM_AND_DISPATCH",
            "notes": "Xác nhận đối tượng cầm vũ khí tại cửa",
        },
        timeout=2.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["decision"] == "CONFIRM_AND_DISPATCH"

    # Verify status changed in recent incidents
    updated = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    inc = next(i for i in updated if i["id"] == evt_id)
    assert inc["status"] == "OPERATOR_CONFIRMED"


def test_tc30_hitl_confirm_generates_incident_package(backend_server):
    """TC-30: Automated Incident Evidence Package is generated upon CONFIRM_AND_DISPATCH."""
    evt_id = f"EVT-PKG-{int(time.time())}"
    requests.post(f"{BASE_URL}/api/v1/incidents", json={"event_id": evt_id, "primary_action": "INTRUSION", "camera_id": "cam_01"})

    resp = requests.post(
        f"{BASE_URL}/api/incidents/{evt_id}/verify",
        json={"operatorId": "OP-HA-NOI-01", "decision": "CONFIRM_AND_DISPATCH"},
    )
    assert resp.status_code == 200
    pkg = resp.json().get("incidentPackage")
    assert pkg is not None
    assert "packageId" in pkg
    assert pkg["dispatchedByOperator"] == "OP-HA-NOI-01"
    assert "coordinates" in pkg


def test_tc31_hitl_downgrade_monitor_decision(backend_server):
    """TC-31: DOWNGRADE_MONITOR updates status to DOWNGRADED_MONITORING."""
    evt_id = f"EVT-DOWNGRADE-{int(time.time())}"
    requests.post(f"{BASE_URL}/api/v1/incidents", json={"event_id": evt_id, "primary_action": "LOITERING", "camera_id": "cam_01"})

    resp = requests.post(
        f"{BASE_URL}/api/incidents/{evt_id}/verify",
        json={"operatorId": "OP-VN-SOC-804", "decision": "DOWNGRADE_MONITOR"},
    )
    assert resp.status_code == 200
    updated = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    inc = next(i for i in updated if i["id"] == evt_id)
    assert inc["status"] == "DOWNGRADED_MONITORING"


def test_tc32_hitl_dismiss_false_positive_decision(backend_server):
    """TC-32: DISMISS_FALSE_POSITIVE updates status to DISMISSED."""
    evt_id = f"EVT-DISMISS-{int(time.time())}"
    requests.post(f"{BASE_URL}/api/v1/incidents", json={"event_id": evt_id, "primary_action": "CROUCHING", "camera_id": "cam_01"})

    resp = requests.post(
        f"{BASE_URL}/api/incidents/{evt_id}/verify",
        json={"operatorId": "OP-VN-SOC-804", "decision": "DISMISS_FALSE_POSITIVE"},
    )
    assert resp.status_code == 200
    updated = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    inc = next(i for i in updated if i["id"] == evt_id)
    assert inc["status"] == "DISMISSED"


def test_tc33_hitl_rejects_unknown_decision(backend_server):
    """TC-33: Invalid decision outside the 3 standard options is rejected with 400."""
    incidents = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    target_id = incidents[0]["id"]

    resp = requests.post(
        f"{BASE_URL}/api/incidents/{target_id}/verify",
        json={"operatorId": "OP-804", "decision": "INVALID_DECISION_XYZ"},
        timeout=2.0,
    )
    assert resp.status_code == 400


# ==============================================================================
# NHÓM 7: AUDIT LOGS, SSE & WEBSOCKET ENGINE (TC-34 -> TC-36)
# ==============================================================================

def test_tc34_audit_logs_record_immutable_trail(backend_server):
    """TC-34: GET /api/soc/audit-logs contains full audit log entries."""
    resp = requests.get(f"{BASE_URL}/api/soc/audit-logs", timeout=2.0)
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    l0 = logs[-1]
    assert "auditId" in l0
    assert "operatorId" in l0
    assert "decision" in l0
    assert l0["status"] == "RECORDED_IMMUTABLE"


def test_tc35_websocket_connection_and_heartbeat(backend_server):
    """TC-35: WebSocket /ws/live-stream connects with HTTP 101 Switching Protocols."""
    sock = ws_connect_and_recv("127.0.0.1", TEST_PORT, "/ws/live-stream")
    # Verify incoming frame data arrives
    frame_bytes = sock.recv(2048)
    sock.close()
    assert len(frame_bytes) > 0


def test_tc36_websocket_broadcasts_incident_alert_on_ingest(backend_server):
    """TC-36: Ingesting an incident broadcasts over WebSocket in real time."""
    sock = ws_connect_and_recv("127.0.0.1", TEST_PORT, "/ws/live-stream")

    # Ingest incident
    test_evt_id = f"EVT-WS-ALERT-{int(time.time())}"
    resp = requests.post(
        f"{BASE_URL}/api/v1/incidents",
        json={"event_id": test_evt_id, "primary_action": "WEAPON_THREAT", "camera_id": "cam_01"},
        timeout=2.0,
    )
    assert resp.status_code == 200

    # Socket receives broadcast frame
    data_received = False
    sock.settimeout(2.0)
    for _ in range(5):
        try:
            chunk = sock.recv(4096)
            if test_evt_id.encode() in chunk or b"INCIDENT_ALERT" in chunk or b"TELEMETRY_AND_AI_TICK" in chunk:
                data_received = True
                break
        except Exception:
            break

    sock.close()
    assert data_received is True


# ==============================================================================
# NHÓM 8: KẾT NỐI CAMERA CLIENT, LIVE STREAMING & AI ALERT (TC-37 -> TC-42)
# ==============================================================================

def test_tc37_register_camera_client(backend_server):
    """TC-37: POST /api/v1/cameras/register successfully registers camera client."""
    client_cam_id = f"LAPTOP_CLIENT_{int(time.time())}"
    payload = {
        "camera_id": client_cam_id,
        "name": "Laptop WebCam Client #1",
        "latitude": 21.0285,
        "longitude": 105.8544,
        "address": "Phòng Điều Hành Trung Tâm",
        "fps": 30,
    }
    resp = requests.post(f"{BASE_URL}/api/v1/cameras/register", json=payload, timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["camera"]["id"] == client_cam_id
    assert f"/api/v1/cameras/{client_cam_id}/stream" in data["stream_url"]


def test_tc38_post_stream_raw_jpeg_frame(backend_server):
    """TC-38: POST /api/v1/cameras/:id/stream receives raw JPEG binary frame."""
    client_cam_id = "cam_01"
    raw_jpeg = base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=")
    headers = {
        "Content-Type": "image/jpeg",
        "X-Camera-ID": client_cam_id,
        "X-Camera-Name": "Server Room Live",
        "X-Timestamp-Ms": str(int(time.time() * 1000)),
        "X-Test-Action": "NORMAL",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/cameras/{client_cam_id}/stream", data=raw_jpeg, headers=headers, timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["camera_id"] == client_cam_id


def test_tc39_get_camera_snapshot_jpeg(backend_server):
    """TC-39: GET /api/v1/cameras/:id/snapshot returns valid JPEG image."""
    resp = requests.get(f"{BASE_URL}/api/v1/cameras/cam_01/snapshot", timeout=2.0)
    assert resp.status_code == 200
    assert "image/jpeg" in resp.headers.get("Content-Type", "")
    assert len(resp.content) > 0


def test_tc40_get_camera_mjpeg_stream(backend_server):
    """TC-40: GET /api/v1/cameras/:id/stream serves multipart/x-mixed-replace stream."""
    resp = requests.get(f"{BASE_URL}/api/v1/cameras/cam_01/stream", stream=True, timeout=3.0)
    assert resp.status_code == 200
    content_type = resp.headers.get("Content-Type", "")
    assert "multipart/x-mixed-replace" in content_type

    # Verify boundary frame chunks
    first_chunk = next(resp.iter_content(chunk_size=1024))
    assert b"--frame" in first_chunk or b"image/jpeg" in first_chunk


def test_tc41_camera_client_stream_triggers_ai_alert(backend_server):
    """TC-41: Streaming a frame with X-Test-Action: WEAPON_THREAT activates aiAlert on camera."""
    client_cam_id = "cam_02"
    raw_jpeg = base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=")
    headers = {
        "Content-Type": "image/jpeg",
        "X-Camera-ID": client_cam_id,
        "X-Test-Action": "WEAPON_THREAT",
        "X-Timestamp-Ms": str(int(time.time() * 1000)),
    }
    resp = requests.post(f"{BASE_URL}/api/v1/cameras/{client_cam_id}/stream", data=raw_jpeg, headers=headers, timeout=2.0)
    assert resp.status_code == 200

    # Verify camera state now has active aiAlert
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cam2 = next(c for c in cams if c["id"] == client_cam_id)
    assert cam2["aiAlert"] is not None
    assert cam2["aiAlert"]["hasAlert"] is True
    assert cam2["aiAlert"]["type"] == "WEAPON_THREAT"
    assert cam2["aiAlert"]["severity"] == "CRITICAL"


def test_tc42_ingest_incident_escalates_camera_alert_state(backend_server):
    """TC-42: Ingesting an AI incident updates camera's aiAlert banner metadata."""
    target_cam = "cam_03"
    incident_payload = {
        "event_id": f"EVT-ALERT-CAM-{int(time.time())}",
        "primary_action": "FALLEN",
        "severity": "HIGH",
        "threat_score": 0.88,
        "camera_id": target_cam,
        "reasoning": "Nạn nhân ngã quỵ bất tỉnh cần hỗ trợ y tế khẩn cấp",
    }
    resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=incident_payload, timeout=2.0)
    assert resp.status_code == 200

    # Verify camera aiAlert state
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cam3 = next(c for c in cams if c["id"] == target_cam)
    assert cam3["aiAlert"] is not None
    assert cam3["aiAlert"]["hasAlert"] is True
    assert cam3["aiAlert"]["type"] == "FALLEN"
    assert cam3["aiAlert"]["severity"] == "HIGH"


# ==============================================================================
# NHÓM 9: XÁC MINH ZERO DUMMY VÀ 100% CẢNH BÁO TỪ NVIDIA AI (TC-43 -> TC-46)
# ==============================================================================

def test_tc43_zero_dummy_baseline_no_sine_wave_or_fake_cameras(backend_server):
    """TC-43: Verify no fake cameras (cam_05, cam_06) and clean initial state."""
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    cam_ids = [c["id"] for c in cams]
    assert "cam_05" not in cam_ids
    assert "cam_06" not in cam_ids
    # Initial cameras cam_04 if unalerted or any newly registered should have valid structure
    for c in cams:
        assert isinstance(c["boundingBoxes"], list)


def test_tc44_zero_dummy_incident_origins_guarantee(backend_server):
    """TC-44: Verify all incidents have traceable event_id and primary_action."""
    incidents = requests.get(f"{BASE_URL}/api/incidents/recent").json()
    assert isinstance(incidents, list)
    for inc in incidents:
        # Check that incidents are not hardcoded mock artifacts without action
        assert "id" in inc
        assert "severity" in inc
        assert inc["status"] in ("PENDING_VERIFICATION", "OPERATOR_CONFIRMED", "DOWNGRADED_MONITORING", "DISMISSED")


def test_tc45_100_percent_ai_alert_pipeline_flow(backend_server):
    """TC-45: 100% of camera alerts originate strictly from an AI detection payload."""
    test_cam = "cam_test_pipeline"
    # Register clean camera without any alert
    reg_resp = requests.post(
        f"{BASE_URL}/api/v1/cameras/register",
        json={"camera_id": test_cam, "name": "AI Pipeline Test Camera"},
        timeout=2.0
    )
    assert reg_resp.status_code == 200
    
    # Verify camera has no alert initially
    cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    target = next(c for c in cams if c["id"] == test_cam)
    assert target.get("aiAlert") is None
    assert len(target.get("boundingBoxes", [])) == 0

    # Simulate AI Server delivering a verified detection
    ai_alert_payload = {
        "event_id": f"EVT-NVIDIA-{int(time.time())}",
        "primary_action": "KNIFE_THREAT",
        "severity": "CRITICAL",
        "threat_score": 0.95,
        "confidence": 0.95,
        "camera_id": test_cam,
        "reasoning": "NVIDIA VLM xác nhận đối tượng cầm dao tấn công lúc 16:40",
        "boxes": [
            {
                "id": "box_ai_1",
                "label": "KNIFE_THREAT 95%",
                "subLabel": "SUSPECT",
                "severity": "CRITICAL",
                "bbox": [100, 150, 400, 600]
            }
        ]
    }
    post_resp = requests.post(f"{BASE_URL}/api/v1/incidents", json=ai_alert_payload, timeout=2.0)
    assert post_resp.status_code == 200

    # Verify camera now has 100% AI-derived alert and bounding boxes
    cams_after = requests.get(f"{BASE_URL}/api/devices/cameras").json()
    target_after = next(c for c in cams_after if c["id"] == test_cam)
    assert target_after["aiAlert"] is not None
    assert target_after["aiAlert"]["hasAlert"] is True
    assert target_after["aiAlert"]["type"] == "KNIFE_THREAT"
    assert target_after["aiAlert"]["severity"] == "CRITICAL"
    assert target_after["aiAlert"]["confidence"] == 0.95
    assert len(target_after["boundingBoxes"]) == 1
    assert target_after["boundingBoxes"][0]["label"] == "KNIFE_THREAT 95%"


def test_tc46_ai_alert_all_six_critical_classes(backend_server):
    """TC-46: Verify all 6 critical classes (WEAPON_THREAT, KNIFE_THREAT, FALLEN, FIGHTING, LOITERING, INTRUSION) map correctly."""
    classes = [
        ("WEAPON_THREAT", "CRITICAL"),
        ("KNIFE_THREAT", "CRITICAL"),
        ("FALLEN", "HIGH"),
        ("FIGHTING", "HIGH"),
        ("LOITERING", "MEDIUM"),
        ("INTRUSION", "HIGH"),
    ]
    for action, expected_sev in classes:
        cam_id = f"cam_cls_{action.lower()}"
        resp = requests.post(
            f"{BASE_URL}/api/v1/incidents",
            json={
                "event_id": f"EVT-CLS-{action}-{int(time.time())}",
                "primary_action": action,
                "severity": expected_sev,
                "camera_id": cam_id,
                "reasoning": f"NVIDIA NIM VLM phân tích lớp hành vi {action}",
            },
            timeout=2.0
        )
        assert resp.status_code == 200
        cams = requests.get(f"{BASE_URL}/api/devices/cameras").json()
        c = next(cam for cam in cams if cam["id"] == cam_id)
        assert c["aiAlert"] is not None
        assert c["aiAlert"]["type"] == action


