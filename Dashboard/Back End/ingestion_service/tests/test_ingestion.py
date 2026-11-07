import json
import os
import shutil
import tempfile
import threading
import time
import pytest
from werkzeug.serving import make_server

from ..app import create_app
from ..config import IngestionConfig
from .mock_target_server import create_mock_target_app, received_requests


SAMPLE_FULL_INPUT = {
  "schema_version": "1.0.0",
  "session": {
    "authenticated": False,
    "user": None
  },

  "config": {
    "brand": { "name": "CYBERGUARD", "product": "AI · SOC", "version": "2.1" },
    "site": { "site_id": "SITE-HQ-01", "name": "Headquarters" },
    "display": { "timezone": "UTC", "refresh_interval_ms": 1000 },

    "navigation": {
      "sections": [
        {
          "section_id": "operations",
          "title": "OPERATIONS",
          "items": [
            { "id": "soc_dashboard", "label": "SOC Dashboard", "icon": "chart-bar", "route": "/dashboard", "badge_key": None },
            { "id": "live_video_wall", "label": "Live Video Wall", "icon": "video", "route": "/video-wall", "badge_key": None },
            { "id": "threat_intelligence", "label": "Threat Intelligence", "icon": "alert-triangle", "route": "/threat-intel", "badge_key": "threat_intelligence" },
            { "id": "incident_feed", "label": "Incident Feed", "icon": "activity", "route": "/incidents", "badge_key": "incident_feed" },
            { "id": "ai_analyzer", "label": "AI Analyzer", "icon": "cpu", "route": "/ai-analyzer", "badge_key": None },
            { "id": "device_manager", "label": "Device Manager", "icon": "server", "route": "/devices", "badge_key": None }
          ]
        }
      ],
      "footer_items": [
        { "id": "settings", "label": "Settings", "icon": "settings", "route": "/settings" }
      ]
    },

    "enums": {
      "severity": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
      "incident_status": ["OPEN", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"],
      "open_statuses": ["OPEN", "ACKNOWLEDGED", "INVESTIGATING"],
      "event_type": ["PHYSICAL_INTRUSION", "EQUIPMENT_TAMPER", "PERIMETER_BREACH", "CAMERA_OFFLINE", "ACCESS_DENIED"],
      "camera_status": ["LIVE", "DEGRADED", "OFFLINE", "CONNECTING"],
      "offline_reason": ["NO_SIGNAL", "POWER_LOSS", "AUTH_FAILED", "UNKNOWN"],
      "object_class": ["person", "vehicle", "equipment_tamper", "animal", "unknown"],
      "zone": ["SERVER_ROOM", "GATE", "PARKING", "LOBBY", "WAREHOUSE"],
      "health_status": ["NOMINAL", "WARNING", "CRITICAL"],
      "poe_state": ["ACTIVE", "FAULT", "OFF"],
      "system_state": ["ACTIVE", "DEGRADED", "DOWN"],
      "engine_status": ["ONLINE", "DEGRADED", "OFFLINE"],
      "stream_mode": ["LIVE", "PAUSED", "DISCONNECTED"]
    },

    "severity_palette": {
      "CRITICAL": "#CF1322",
      "HIGH": "#FF4D4F",
      "MEDIUM": "#FA8C16",
      "LOW": "#FADB14",
      "INFO": "#1890FF"
    },

    "thresholds": {
      "stream_latency_ms": { "warning": 100, "critical": 250 },
      "nvr_storage_used_percent": { "warning": 85, "critical": 95 },
      "poe_load_percent": { "warning": 80, "critical": 95 }
    },

    "threat_score": {
      "max_score": 100,
      "gauge_segments_total": 15,
      "bands": [
        { "min": 0, "max": 24, "level": "LOW", "risk_label": "SAFE" },
        { "min": 25, "max": 49, "level": "MEDIUM", "risk_label": "CAUTION" },
        { "min": 50, "max": 74, "level": "HIGH", "risk_label": "AT RISK" },
        { "min": 75, "max": 100, "level": "CRITICAL", "risk_label": "DANGER" }
      ]
    },

    "camera_matrix": {
      "title": "LIVE CAMERA MATRIX",
      "supported_layouts": ["1x1", "2x2", "3x3", "4x4"],
      "default_layout": "2x2",
      "toolbar_actions": ["settings", "layout", "fullscreen", "more"],
      "tile_controls": ["zoom_in", "zoom_out", "ptz", "fit"],
      "bounding_box_format": {
        "coordinate_system": "normalized",
        "origin": "top_left",
        "range": [0, 1]
      }
    },

    "cameras": [
      {
        "camera_id": "CAM-SRV-01", "location_name": "Server Room", "zone": "SERVER_ROOM",
        "ip_address": "192.168.16.120", "codec": "H.265", "resolution": "1920x1080",
        "webrtc_endpoint": "/api/v2/streams/CAM-SRV-01/webrtc",
        "ptz": { "supported": True, "presets": ["Rack_Corridor_A", "Rack_Corridor_B"] }
      },
      {
        "camera_id": "CAM-GATE-01", "location_name": "Main Gate", "zone": "GATE",
        "ip_address": "192.168.16.130", "codec": "H.265", "resolution": "1920x1080",
        "webrtc_endpoint": "/api/v2/streams/CAM-GATE-01/webrtc",
        "ptz": { "supported": True, "presets": ["Gate_Overview", "Gate_Closeup"] }
      },
      {
        "camera_id": "CAM-SRV-02", "location_name": "Server Room", "zone": "SERVER_ROOM",
        "ip_address": "192.168.16.121", "codec": "H.265", "resolution": "1920x1080",
        "webrtc_endpoint": "/api/v2/streams/CAM-SRV-02/webrtc",
        "ptz": { "supported": True, "presets": ["Aisle_A", "Aisle_B"] }
      },
      {
        "camera_id": "CAM-GATE-02", "location_name": "Main Gate", "zone": "GATE",
        "ip_address": "192.168.16.131", "codec": "H.265", "resolution": "1920x1080",
        "webrtc_endpoint": "/api/v2/streams/CAM-GATE-02/webrtc",
        "ptz": { "supported": True, "presets": ["Side_Entrance", "Gate_Overview"] }
      },
      {
        "camera_id": "CAM-PRK-01", "location_name": "Parking", "zone": "PARKING",
        "ip_address": "192.168.16.140", "codec": "H.265", "resolution": "1920x1080",
        "webrtc_endpoint": "/api/v2/streams/CAM-PRK-01/webrtc",
        "ptz": { "supported": True, "presets": ["Lot_Overview"] }
      },
      {
        "camera_id": "CAM-LBY-02", "location_name": "Lobby", "zone": "LOBBY",
        "ip_address": "192.168.16.150", "codec": "H.264", "resolution": "1920x1080",
        "webrtc_endpoint": "/api/v2/streams/CAM-LBY-02/webrtc",
        "ptz": { "supported": False, "presets": [] }
      },
      {
        "camera_id": "CAM-WH-03", "location_name": "Warehouse", "zone": "WAREHOUSE",
        "ip_address": "192.168.16.160", "codec": "H.264", "resolution": "1280x720",
        "webrtc_endpoint": "/api/v2/streams/CAM-WH-03/webrtc",
        "ptz": { "supported": False, "presets": [] }
      }
    ]
  },

  "live": {
    "meta": {
      "sequence": 184233,
      "generated_at": "2026-03-23T16:47:26Z",
      "stream_mode": "LIVE"
    },

    "system": {
      "state": "ACTIVE",
      "engine_status": "ONLINE",
      "threat_db": { "version": "2026.03", "updated_at": "2026-03-23T02:00:00Z" },
      "unread_badges": { "threat_intelligence": 5, "incident_feed": 0 },
      "notifications_unread": 0
    },

    "threat_overview": {
      "threat_score": 68,
      "open_threats": {
        "by_severity": { "CRITICAL": 1, "HIGH": 1, "MEDIUM": 2, "LOW": 0 }
      }
    },

    "kpi": {
      "stream_latency_ms": 42,
      "camera_fleet": {
        "total": 43,
        "online": 40,
        "offline": [
          { "camera_id": "CAM-PRK-01", "reason": "NO_SIGNAL", "last_seen_at": "2026-03-23T15:52:30Z" },
          { "camera_id": "CAM-LBY-02", "reason": "POWER_LOSS", "last_seen_at": "2026-03-23T09:14:03Z" },
          { "camera_id": "CAM-WH-03", "reason": "AUTH_FAILED", "last_seen_at": "2026-03-22T21:40:51Z" }
        ]
      }
    },

    "infrastructure": {
      "nvr_storage": { "used_tb": 78.72, "capacity_tb": 96.0 },
      "poe": { "state": "ACTIVE", "load_watts": 410, "capacity_watts": 740 }
    },

    "camera_matrix": {
      "layout": "2x2",
      "tiles": [
        {
          "slot": 1,
          "camera_id": "CAM-SRV-01",
          "status": "LIVE",
          "telemetry": { "fps": 30, "bitrate_kbps": 4096 },
          "ptz": { "preset": "Rack_Corridor_A", "pan": 0.0, "tilt": -0.15, "zoom": 1.0 },
          "detections": [
            {
              "detection_id": "DET-9901", "track_id": "TRK-0412", "incident_id": "INC-20260323-003",
              "object_class": "person", "label": "Unauthorized Person", "confidence": 0.84, "severity": "HIGH",
              "detected_at": "2026-03-23T16:47:25.812Z",
              "bbox": { "x_min": 0.42, "y_min": 0.31, "x_max": 0.65, "y_max": 0.92 }
            },
            {
              "detection_id": "DET-9902", "track_id": "TRK-0413", "incident_id": "INC-20260323-003",
              "object_class": "equipment_tamper", "label": "Server Rack Access", "confidence": 0.53, "severity": "MEDIUM",
              "detected_at": "2026-03-23T16:47:25.812Z",
              "bbox": { "x_min": 0.60, "y_min": 0.25, "x_max": 0.82, "y_max": 0.55 }
            }
          ]
        },
        {
          "slot": 2,
          "camera_id": "CAM-GATE-01",
          "status": "LIVE",
          "telemetry": { "fps": 30, "bitrate_kbps": 3890 },
          "ptz": { "preset": "Gate_Overview", "pan": 0.0, "tilt": 0.0, "zoom": 1.0 },
          "detections": []
        },
        {
          "slot": 3,
          "camera_id": "CAM-SRV-02",
          "status": "LIVE",
          "telemetry": { "fps": 29, "bitrate_kbps": 4210 },
          "ptz": { "preset": "Aisle_B", "pan": 0.1, "tilt": -0.05, "zoom": 1.0 },
          "detections": [
            {
              "detection_id": "DET-9903", "track_id": "TRK-0412", "incident_id": "INC-20260323-003",
              "object_class": "person", "label": "Person Detected", "confidence": 0.91, "severity": "MEDIUM",
              "detected_at": "2026-03-23T16:47:25.640Z",
              "bbox": { "x_min": 0.45, "y_min": 0.28, "x_max": 0.62, "y_max": 0.94 }
            }
          ]
        },
        {
          "slot": 4,
          "camera_id": "CAM-GATE-02",
          "status": "LIVE",
          "telemetry": { "fps": 30, "bitrate_kbps": 3975 },
          "ptz": { "preset": "Side_Entrance", "pan": -0.2, "tilt": 0.0, "zoom": 1.5 },
          "detections": [
            {
              "detection_id": "DET-9904", "track_id": "TRK-0507", "incident_id": "INC-20260323-004",
              "object_class": "person", "label": "Perimeter Motion", "confidence": 0.88, "severity": "MEDIUM",
              "detected_at": "2026-03-23T16:47:25.903Z",
              "bbox": { "x_min": 0.40, "y_min": 0.30, "x_max": 0.54, "y_max": 0.89 }
            },
            {
              "detection_id": "DET-9905", "track_id": "TRK-0508", "incident_id": None,
              "object_class": "person", "label": "Staff Verified", "confidence": 0.95, "severity": "INFO",
              "detected_at": "2026-03-23T16:47:25.903Z",
              "bbox": { "x_min": 0.56, "y_min": 0.38, "x_max": 0.65, "y_max": 0.78 }
            }
          ]
        }
      ]
    },

    "recent_threats": [
      {
        "incident_id": "INC-20260323-004",
        "detected_at": "2026-03-23T16:46:55Z",
        "updated_at": "2026-03-23T16:47:25Z",
        "event_type": "PERIMETER_BREACH",
        "title": "Perimeter Motion After Hours",
        "severity": "MEDIUM",
        "status": "OPEN",
        "assignee": None,
        "zone": "GATE",
        "primary_camera_id": "CAM-GATE-02",
        "related_camera_ids": [],
        "detection_ids": ["DET-9904"],
        "snapshots": [
          "/media/snapshots/2026-03-23/inc_20260323_004_1.jpg",
          "/media/snapshots/2026-03-23/inc_20260323_004_2.jpg"
        ],
        "playback": {
          "available": True,
          "video_url": "/media/playback/2026-03-23/inc_20260323_004.mp4",
          "start_offset_sec": 15,
          "duration_sec": 60
        }
      },
      {
        "incident_id": "INC-20260323-003",
        "detected_at": "2026-03-23T16:46:48Z",
        "updated_at": "2026-03-23T16:47:25Z",
        "event_type": "PHYSICAL_INTRUSION",
        "title": "Server Room Intrusion",
        "severity": "HIGH",
        "status": "OPEN",
        "assignee": None,
        "zone": "SERVER_ROOM",
        "primary_camera_id": "CAM-SRV-01",
        "related_camera_ids": ["CAM-SRV-02"],
        "detection_ids": ["DET-9901", "DET-9902", "DET-9903"],
        "snapshots": [
          "/media/snapshots/2026-03-23/inc_20260323_003_1.jpg",
          "/media/snapshots/2026-03-23/inc_20260323_003_2.jpg"
        ],
        "playback": {
          "available": True,
          "video_url": "/media/playback/2026-03-23/inc_20260323_003.mp4",
          "start_offset_sec": 10,
          "duration_sec": 90
        }
      },
      {
        "incident_id": "INC-20260323-002",
        "detected_at": "2026-03-23T15:52:34Z",
        "updated_at": "2026-03-23T15:52:34Z",
        "event_type": "CAMERA_OFFLINE",
        "title": "Camera Signal Lost",
        "severity": "MEDIUM",
        "status": "OPEN",
        "assignee": None,
        "zone": "PARKING",
        "primary_camera_id": "CAM-PRK-01",
        "related_camera_ids": [],
        "detection_ids": [],
        "snapshots": [
          "/media/snapshots/2026-03-23/inc_20260323_002_1.jpg"
        ],
        "playback": {
          "available": True,
          "video_url": "/media/playback/2026-03-23/inc_20260323_002.mp4",
          "start_offset_sec": 0,
          "duration_sec": 30
        }
      },
      {
        "incident_id": "INC-20260323-001",
        "detected_at": "2026-03-23T15:38:55Z",
        "updated_at": "2026-03-23T15:44:10Z",
        "event_type": "EQUIPMENT_TAMPER",
        "title": "Server Rack Tamper",
        "severity": "CRITICAL",
        "status": "INVESTIGATING",
        "assignee": "analyst-01",
        "zone": "SERVER_ROOM",
        "primary_camera_id": "CAM-SRV-01",
        "related_camera_ids": [],
        "detection_ids": [],
        "snapshots": [
          "/media/snapshots/2026-03-23/inc_20260323_001_1.jpg",
          "/media/snapshots/2026-03-23/inc_20260323_001_2.jpg"
        ],
        "playback": {
          "available": True,
          "video_url": "/media/playback/2026-03-23/inc_20260323_001.mp4",
          "start_offset_sec": 20,
          "duration_sec": 120
        }
      }
    ]
  }
}


@pytest.fixture(scope="session")
def mock_target_url():
    """Starts the mock target server on a background thread on localhost:5099."""
    app = create_mock_target_app()
    server = make_server("127.0.0.1", 5099, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:5099"
    server.shutdown()


@pytest.fixture
def test_client(mock_target_url, tmp_path):
    """Creates a test client for the gateway pointing to the mock target server."""
    dlq_dir = str(tmp_path / "dlq")
    config = IngestionConfig(
        TARGET_SERVER_BASE_URL=mock_target_url,
        TARGET_SERVER_TIMEOUT_MS=2000,
        TARGET_SERVER_MAX_RETRIES=2,
        DLQ_STORAGE_PATH=dlq_dir,
    )
    app = create_app(config)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ==============================================================
# TESTS FOR ALL 11 ROUTES & ERROR CASES
# ==============================================================

def test_health_check(test_client):
    res = test_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "HEALTHY"
    assert "dlq_pending_records" in data


def test_r01_session(test_client):
    payload = SAMPLE_FULL_INPUT["session"]
    res = test_client.post("/api/v1/session", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["authenticated"] is False


def test_r02_system_config(test_client):
    payload = SAMPLE_FULL_INPUT["config"]
    res = test_client.post("/api/v1/config/system", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["site_id"] == "SITE-HQ-01"


def test_r03_camera_fleet_config(test_client):
    payload = SAMPLE_FULL_INPUT["config"]["cameras"]
    res = test_client.post("/api/v1/config/cameras", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["total_cameras_configured"] == 7


def test_r04_live_meta(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["meta"]
    res = test_client.post("/api/v1/live/meta", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["sequence"] == 184233


def test_r05_live_system(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["system"]
    res = test_client.post("/api/v1/live/system", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["engine_status"] == "ONLINE"


def test_r06_threat_overview(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["threat_overview"]
    res = test_client.post("/api/v1/live/threat-overview", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["threat_score"] == 68


def test_r07_live_kpi(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["kpi"]
    res = test_client.post("/api/v1/live/kpi", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["latency_ms"] == 42
    assert data["summary"]["cameras_online"] == 40


def test_r08_live_infrastructure(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["infrastructure"]
    res = test_client.post("/api/v1/live/infrastructure", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["storage_used_tb"] == 78.72


def test_r09_camera_matrix(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["camera_matrix"]
    res = test_client.post("/api/v1/live/camera-matrix", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["layout"] == "2x2"
    assert data["summary"]["tiles_count"] == 4


def test_r10_recent_threats_and_hitl(test_client):
    payload = SAMPLE_FULL_INPUT["live"]["recent_threats"]
    res = test_client.post("/api/v1/live/incidents", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["incidents_count"] == 4


def test_r11_master_full_ingest(test_client):
    res = test_client.post("/api/v1/ingest/full", json=SAMPLE_FULL_INPUT)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["forward_status"] == "FORWARDED"
    assert data["summary"]["has_session"] is True
    assert data["summary"]["has_config"] is True
    assert data["summary"]["has_live"] is True


def test_schema_validation_rejection(test_client):
    # Threat score out of range (> 100)
    bad_payload = {
        "threat_score": 999,
        "open_threats": { "by_severity": {} }
    }
    res = test_client.post("/api/v1/live/threat-overview", json=bad_payload)
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert "Schema Validation Error" in data["error"]


def test_method_not_allowed(test_client):
    res = test_client.get("/api/v1/session")
    assert res.status_code == 405


def test_target_server_unreachable_dlq_fallback(tmp_path):
    dlq_dir = str(tmp_path / "dlq_unreachable")
    # Point to non-existent target port
    config = IngestionConfig(
        TARGET_SERVER_BASE_URL="http://127.0.0.1:54321",
        TARGET_SERVER_TIMEOUT_MS=500,
        TARGET_SERVER_MAX_RETRIES=2,
        DLQ_STORAGE_PATH=dlq_dir,
    )
    app = create_app(config)
    app.config["TESTING"] = True
    with app.test_client() as client:
        payload = SAMPLE_FULL_INPUT["live"]["meta"]
        res = client.post("/api/v1/live/meta", json=payload)
        # Should return 502 with buffered DLQ
        assert res.status_code == 502
        data = res.get_json()
        assert data["forward_status"] == "FORWARD_FAILED"
        assert data["target_response"]["buffered_to_dlq"] is True

        # Verify DLQ file was written
        dlq_file = os.path.join(dlq_dir, "failed_packets.jsonl")
        assert os.path.exists(dlq_file)
        with open(dlq_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["route"] == "/api/soc/live/meta"
            assert record["payload"]["sequence"] == 184233


def test_hitl_safeguard_enforcement_high_critical(test_client):
    """
    Test Rule [CD-04]: HIGH and CRITICAL events without OPERATOR_CONFIRMED
    must have requires_operator_verification = True injected.
    """
    from ..forwarder import ForwarderService
    forwarder = ForwarderService(IngestionConfig())
    unverified_incidents = [
        {"incident_id": "INC-01", "severity": "CRITICAL", "status": "INVESTIGATING", "assignee": "analyst-01"},
        {"incident_id": "INC-02", "severity": "HIGH", "status": "OPEN", "assignee": None},
        {"incident_id": "INC-03", "severity": "LOW", "status": "OPEN", "assignee": None},
    ]
    secured = forwarder.enforce_hitl_check(unverified_incidents, "INCIDENTS_TEST")
    # INC-01 is CRITICAL without OPERATOR_CONFIRMED
    assert secured[0].get("requires_operator_verification") is True
    assert secured[0].get("dispatch_restricted") is True
    # INC-02 is HIGH without OPERATOR_CONFIRMED
    assert secured[1].get("requires_operator_verification") is True
    assert secured[1].get("dispatch_restricted") is True
    # INC-03 is LOW
    assert secured[2].get("requires_operator_verification") is None
