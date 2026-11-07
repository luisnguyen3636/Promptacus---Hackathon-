"""Comprehensive Test Suite for AI-SOC Dashboard, Real-time Reasoning and Logging Engine.

Covers:
1. SOCLogger persistent JSONL, alert, and audit trail operations.
2. Log query filtering by severity, camera, keyword, and pagination.
3. Server REST APIs: /api/v1/dashboard/logs, /api/v1/dashboard/logs/download.
4. AI-Reasoned Truth fidelity (5-gate audit, dynamic threat scoring, blind-spot predictions).
5. Client-Server live streaming and log emission lifecycle.
"""

import json
import os
import socket
import sys
import threading
import time
from typing import Any, Dict, Generator, Tuple

import cv2
import numpy as np
import pytest
import requests

from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
from urbansoc.client.edge_client import EdgeCameraClient
from urbansoc.server.inference_server import InferenceServer
from urbansoc.telemetry.soc_logger import SOCLogger


def get_free_port() -> int:
    """Acquire an isolated free ephemeral port for socket tests."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ==============================================================================
# 1. SOCLOGGER UNIT TESTS (10 TESTS)
# ==============================================================================

class TestSOCLoggerUnit:
    @pytest.fixture
    def soc_logger(self, tmp_path: pytest.TempPathFactory) -> SOCLogger:
        log_dir = str(tmp_path / "soc_logger_tests")
        return SOCLogger(log_dir=log_dir)

    def test_logger_creates_log_directory_automatically(self, soc_logger: SOCLogger) -> None:
        """Verify logger ensures directory existence."""
        assert os.path.exists(soc_logger.log_dir)

    def test_record_ai_reasoning_creates_valid_jsonl(self, soc_logger: SOCLogger) -> None:
        """Verify record_ai_reasoning writes structured JSON to reasoning_jsonl_path."""
        evt = {
            "camera_id": "CAM_01",
            "camera_name": "CAM_01 - Cổng Chu Văn An",
            "severity": "CRITICAL",
            "primary_action": "WEAPON_THREAT",
            "highest_threat_score": 92.5,
            "reasoning": "Đối tượng rút hung khí đe dọa.",
            "chain_hash": "a1b2c3d4e5f60718293a",
            "event_id": "EVT_001",
        }
        res = soc_logger.record_ai_reasoning(evt)
        assert res["camera_id"] == "CAM_01"
        assert res["severity"] == "CRITICAL"
        assert os.path.exists(soc_logger.reasoning_jsonl_path)

        with open(soc_logger.reasoning_jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_id"] == "EVT_001"
        assert parsed["threat_score"] == 92.5

    def test_record_ai_reasoning_appends_to_alerts_log_on_high_severity(
        self, soc_logger: SOCLogger
    ) -> None:
        """Verify that high or critical severity writes formatted line to alerts.log."""
        evt = {
            "camera_id": "CAM_02",
            "severity": "CRITICAL",
            "primary_action": "FIGHTING",
            "reasoning": "Ẩu đả bạo lực giữa hai người.",
        }
        soc_logger.record_ai_reasoning(evt)
        assert os.path.exists(soc_logger.alerts_log_path)
        with open(soc_logger.alerts_log_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "[CRITICAL]" in content
        assert "CAM_02" in content
        assert "FIGHTING" in content

    def test_record_ai_reasoning_ignores_alerts_log_for_normal_low(
        self, soc_logger: SOCLogger
    ) -> None:
        """Verify normal low threat does not pollute alerts.log."""
        evt = {
            "camera_id": "CAM_01",
            "severity": "LOW",
            "primary_action": "NORMAL",
            "reasoning": "Hoạt động bình thường.",
        }
        soc_logger.record_ai_reasoning(evt)
        assert not os.path.exists(soc_logger.alerts_log_path)

    def test_record_operator_audit_creates_audit_log(self, soc_logger: SOCLogger) -> None:
        """Verify operator HITL decision is written to audit.log."""
        audit_res = soc_logger.record_audit(
            operator_id="OPERATOR_LE_HA",
            action="CONFIRM_AND_DISPATCH",
            camera_id="CAM_01",
            event_id="EVT_999",
            notes="Xác nhận đối tượng cầm dao, đã gọi cảnh sát khu vực.",
        )
        assert audit_res["type"] == "OPERATOR_AUDIT"
        assert audit_res["action"] == "CONFIRM_AND_DISPATCH"
        assert os.path.exists(soc_logger.audit_log_path)

        with open(soc_logger.audit_log_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "OPERATOR_LE_HA" in content
        assert "CONFIRM_AND_DISPATCH" in content
        assert "EVT_999" in content

    def test_query_logs_filter_by_severity(self, soc_logger: SOCLogger) -> None:
        """Verify query_logs correctly filters by severity tag."""
        soc_logger.record_ai_reasoning({"camera_id": "C1", "severity": "LOW", "primary_action": "NORMAL"})
        soc_logger.record_ai_reasoning({"camera_id": "C2", "severity": "HIGH", "primary_action": "SNATCHING"})
        soc_logger.record_ai_reasoning({"camera_id": "C3", "severity": "CRITICAL", "primary_action": "FIGHTING"})

        high_logs = soc_logger.query_logs(severity="HIGH")
        assert len(high_logs) == 1
        assert high_logs[0]["action"] == "SNATCHING"

        crit_logs = soc_logger.query_logs(severity="CRITICAL")
        assert len(crit_logs) == 1
        assert crit_logs[0]["action"] == "FIGHTING"

    def test_query_logs_filter_by_camera_id(self, soc_logger: SOCLogger) -> None:
        """Verify query_logs correctly filters by camera ID."""
        soc_logger.record_ai_reasoning({"camera_id": "CAM_A", "severity": "LOW", "primary_action": "NORMAL"})
        soc_logger.record_ai_reasoning({"camera_id": "CAM_B", "severity": "MEDIUM", "primary_action": "LOITERING"})
        soc_logger.record_ai_reasoning({"camera_id": "CAM_A", "severity": "HIGH", "primary_action": "FALLEN"})

        cam_a_logs = soc_logger.query_logs(camera_id="CAM_A")
        assert len(cam_a_logs) == 2
        for l in cam_a_logs:
            assert l["camera_id"] == "CAM_A"

    def test_query_logs_filter_by_keyword(self, soc_logger: SOCLogger) -> None:
        """Verify full-text search across actions, summaries and hashes."""
        soc_logger.record_ai_reasoning({
            "camera_id": "CAM_01",
            "severity": "HIGH",
            "primary_action": "PURSUIT",
            "reasoning": "Đối tượng đuổi theo giật túi xách",
            "chain_hash": "deadbeef9999",
        })
        soc_logger.record_ai_reasoning({
            "camera_id": "CAM_02",
            "severity": "LOW",
            "primary_action": "NORMAL",
            "reasoning": "Học sinh đi bộ bình thường",
        })

        found = soc_logger.query_logs(keyword="túi xách")
        assert len(found) == 1
        assert found[0]["action"] == "PURSUIT"

        found_hash = soc_logger.query_logs(keyword="deadbeef")
        assert len(found_hash) == 1

    def test_query_logs_pagination_limit(self, soc_logger: SOCLogger) -> None:
        """Verify query_logs pagination honors limit."""
        for i in range(20):
            soc_logger.record_ai_reasoning({
                "camera_id": f"CAM_{i}",
                "severity": "MEDIUM",
                "primary_action": "LOITERING",
            })
        paged = soc_logger.query_logs(limit=5)
        assert len(paged) == 5

    def test_export_logs_text(self, soc_logger: SOCLogger) -> None:
        """Verify export_logs_text formats summary for export."""
        soc_logger.record_ai_reasoning({
            "camera_id": "CAM_TEST",
            "severity": "HIGH",
            "primary_action": "WEAPON_THREAT",
            "reasoning": "Rút dao",
        })
        text = soc_logger.export_logs_text(max_lines=10)
        assert "URBAN SAFETY AI-SOC COMPREHENSIVE INCIDENT & AUDIT LOG EXPORT" in text
        assert "WEAPON_THREAT" in text
        assert "CAM_TEST" in text


# ==============================================================================
# 2. SERVER REST API LOGGING ENDPOINTS (8 TESTS)
# ==============================================================================

class TestServerLoggingAPIs:
    @pytest.fixture
    def test_server(self, tmp_path: pytest.TempPathFactory) -> Generator[Tuple[InferenceServer, str], None, None]:
        port = get_free_port()
        srv = InferenceServer(
            host="127.0.0.1",
            port=port,
            output_dir=str(tmp_path / "server_log_test"),
            always_vlm=True,
            mock_vlm=True,
        )
        srv.start(blocking=False)
        time.sleep(0.3)
        base_url = f"http://127.0.0.1:{port}"
        try:
            yield srv, base_url
        finally:
            srv.stop()

    def test_api_dashboard_logs_empty(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/logs returns structured 200 JSON even when empty."""
        _, base_url = test_server
        resp = requests.get(f"{base_url}/api/v1/dashboard/logs", timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_api_dashboard_logs_after_ai_event(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/logs reflects recorded AI reasoning events."""
        srv, base_url = test_server
        srv.record_dashboard_event({
            "camera_id": "CAM_01",
            "severity": "CRITICAL",
            "primary_action": "WEAPON_THREAT",
            "reasoning": "Đối tượng cầm dao tại Cổng Chu Văn An",
        })

        resp = requests.get(f"{base_url}/api/v1/dashboard/logs", timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        entry = data["logs"][0]
        assert entry["camera_id"] == "CAM_01"
        assert entry["severity"] == "CRITICAL"
        assert entry["action"] == "WEAPON_THREAT"

    def test_api_dashboard_logs_filter_by_severity(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/logs?severity=CRITICAL filters properly."""
        srv, base_url = test_server
        srv.record_dashboard_event({"camera_id": "C1", "severity": "LOW", "primary_action": "NORMAL"})
        srv.record_dashboard_event({"camera_id": "C2", "severity": "CRITICAL", "primary_action": "FIGHTING"})

        resp = requests.get(f"{base_url}/api/v1/dashboard/logs?severity=CRITICAL", timeout=2.0)
        data = resp.json()
        assert data["count"] == 1
        assert data["logs"][0]["action"] == "FIGHTING"

    def test_api_dashboard_logs_filter_by_camera_id(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/logs?camera_id=CAM_XYZ filters properly."""
        srv, base_url = test_server
        srv.record_dashboard_event({"camera_id": "CAM_TARGET", "severity": "HIGH", "primary_action": "SNATCHING"})
        srv.record_dashboard_event({"camera_id": "CAM_OTHER", "severity": "HIGH", "primary_action": "SNATCHING"})

        resp = requests.get(f"{base_url}/api/v1/dashboard/logs?camera_id=CAM_TARGET", timeout=2.0)
        data = resp.json()
        assert data["count"] == 1
        assert data["logs"][0]["camera_id"] == "CAM_TARGET"

    def test_api_dashboard_logs_keyword_search(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/logs?keyword=hung_khi searches reasoning text."""
        srv, base_url = test_server
        srv.record_dashboard_event({
            "camera_id": "C1",
            "severity": "CRITICAL",
            "reasoning": "Nghi vấn mang theo hung_khi nguy hiểm",
        })
        resp = requests.get(f"{base_url}/api/v1/dashboard/logs?keyword=hung_khi", timeout=2.0)
        data = resp.json()
        assert data["count"] == 1
        assert "hung_khi" in data["logs"][0]["summary"]

    def test_api_dashboard_logs_download_attachment(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/logs/download returns plain text attachment."""
        srv, base_url = test_server
        srv.record_dashboard_event({
            "camera_id": "CAM_DL",
            "severity": "HIGH",
            "reasoning": "Sự cố kiểm toán tải log",
        })
        resp = requests.get(f"{base_url}/api/v1/dashboard/logs/download", timeout=2.0)
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        assert "URBAN SAFETY AI-SOC" in resp.text
        assert "CAM_DL" in resp.text

    def test_operator_action_persists_to_audit_log(self, test_server: Tuple[InferenceServer, str]) -> None:
        """POST /api/v1/operator/action automatically persists to audit.log."""
        srv, base_url = test_server
        payload = {
            "action": "DOWNGRADE_MONITOR",
            "camera_id": "CAM_01",
            "event_id": "EVT_AUDIT_888",
            "operator_id": "OPERATOR_MINH",
            "notes": "Hạ mức để tiếp tục giám sát ngã ba.",
        }
        resp = requests.post(f"{base_url}/api/v1/operator/action", json=payload, timeout=2.0)
        assert resp.status_code == 200

        # Query logs for AUDIT type
        resp_logs = requests.get(f"{base_url}/api/v1/dashboard/logs?severity=AUDIT", timeout=2.0)
        data = resp_logs.json()
        assert data["count"] >= 1
        assert any(l["operator_id"] == "OPERATOR_MINH" for l in data["logs"] if "operator_id" in l)

    def test_dashboard_state_includes_recent_logs(self, test_server: Tuple[InferenceServer, str]) -> None:
        """GET /api/v1/dashboard/state returns both recent_logs and latest_incident."""
        srv, base_url = test_server
        srv.record_dashboard_event({
            "camera_id": "CAM_DASH",
            "severity": "HIGH",
            "primary_action": "PURSUIT",
            "reasoning": "Rượt đuổi",
        })
        resp = requests.get(f"{base_url}/api/v1/dashboard/state", timeout=2.0)
        data = resp.json()
        assert data["latest_incident"] is not None
        assert data["latest_incident"]["camera_id"] == "CAM_DASH"
        assert len(data["recent_logs"]) >= 1


# ==============================================================================
# 3. AI-REASONED TRUTH FIDELITY TESTS (8 TESTS)
# ==============================================================================

class TestAIReasonedTruthFidelity:
    """Ensure every single metric on the dashboard is reasoned by AI and not static."""

    @pytest.fixture
    def vlm_client(self) -> NvidiaVisionClient:
        return NvidiaVisionClient(mock_mode=True)

    def test_ai_reasons_five_gate_falsification_structure(self, vlm_client: NvidiaVisionClient) -> None:
        """AI analysis strictly reasons all 5 falsification gates."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="WEAPON_THREAT")
        audit = res["anti_false_positive_audit"]
        assert "gate_1_ground_plane_depth" in audit
        assert "gate_2_pose_jerk_filter" in audit
        assert "gate_3_action_reaction_coupling" in audit
        assert "gate_4_posture_and_context" in audit
        assert "gate_5_adversarial_benign_hypothesis" in audit

    def test_ai_reasons_temporal_threat_escalation(self, vlm_client: NvidiaVisionClient) -> None:
        """AI dynamically computes temporal threat score and escalation history."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="WEAPON_THREAT")
        assert res["threat_score"] > 0.0
        assert res["severity"] in ("high", "critical")
        sub = res["evaluated_subjects"][0]
        assert "temporal_threat_score" in sub
        assert "threat_escalation_history" in sub
        assert "Low ->" in sub["threat_escalation_history"]

    def test_ai_reasons_blind_spot_trajectory_predictions(self, vlm_client: NvidiaVisionClient) -> None:
        """AI reasons suspect exit gate, dominant hand, and target camera ranking."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="RUNNING")
        bs = res["multi_camera_blind_spot_reasoning"]
        assert bs["is_triggered"] is True
        assert len(bs["predicted_next_cameras"]) >= 1
        top_cam = bs["predicted_next_cameras"][0]
        assert "target_camera_id" in top_cam
        assert "target_camera_name" in top_cam
        assert "expected_entry_gate_on_target_cam" in top_cam
        assert "probability" in top_cam

    def test_ai_reasons_operator_dashboard_directives(self, vlm_client: NvidiaVisionClient) -> None:
        """AI dynamically produces directives for human operator focus."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="WEAPON_THREAT")
        dirs = res["operator_dashboard_directives"]
        assert "suggested_operator_focus" in dirs
        assert len(dirs["suggested_operator_focus"]) > 10

    def test_ai_reasons_false_positive_suppression_resets_threat(self, vlm_client: NvidiaVisionClient) -> None:
        """When 5-gate audit rejects anomaly, AI reasons threat suppression to Low."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        # Umbrella is benign keyword; Gate 3 rejects as weapon
        res = vlm_client.analyze_frame(
            dummy,
            camera_id="CAM_01",
            action_hint="WEAPON_THREAT",
            held_object="cầm chiếc ô che mưa",
        )
        audit = res["anti_false_positive_audit"]
        assert audit["false_positive_suppressed"] is True
        assert res["severity"] == "low"

    def test_ai_reasons_situation_assessment(self, vlm_client: NvidiaVisionClient) -> None:
        """AI generates structured situation assessment."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="FALLEN")
        assert "situation_assessment" in res
        sa = res["situation_assessment"]
        assert "scenario_type" in sa
        assert "power_dynamics" in sa
        assert "environmental_context" in sa
        assert "victim_vulnerability" in sa

    def test_ai_reasons_intent_prediction(self, vlm_client: NvidiaVisionClient) -> None:
        """AI generates intent prediction based on posture and movement."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="SNATCHING")
        assert "intent_prediction" in res
        ip = res["intent_prediction"]
        assert "primary_intent" in ip
        assert "escalation_risk" in ip
        assert "predicted_next_action" in ip
        assert "time_to_critical_harm_estimate" in ip

    def test_ai_reasons_strict_hitl_state_awaiting_verification(self, vlm_client: NvidiaVisionClient) -> None:
        """AI output strictly obeys CD-04 HITL rule: never auto-confirmed."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        res = vlm_client.analyze_frame(dummy, camera_id="CAM_01", action_hint="WEAPON_THREAT")
        assert res["incident_status"] != "OPERATOR_CONFIRMED"
        assert res["incident_status"] == "AWAITING_OPERATOR_VERIFICATION"


# ==============================================================================
# 4. CLIENT-SERVER STREAMING & LIVE LOG LIFECYCLE (6 TESTS)
# ==============================================================================

class TestClientServerStreamingAndLogging:
    @pytest.fixture
    def active_env(self, tmp_path: pytest.TempPathFactory) -> Generator[Tuple[InferenceServer, EdgeCameraClient, str], None, None]:
        port = get_free_port()
        srv = InferenceServer(
            host="127.0.0.1",
            port=port,
            output_dir=str(tmp_path / "stream_env_test"),
            always_vlm=True,
            mock_vlm=True,
        )
        srv.start(blocking=False)
        time.sleep(0.3)
        base_url = f"http://127.0.0.1:{port}"

        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_STREAM_01",
            camera_name="CAM_STREAM_01 - Cổng Nam",
            headless=True,
        )
        try:
            yield srv, client, base_url
        finally:
            srv.stop()

    def test_client_registration_appears_in_server_dashboard(
        self, active_env: Tuple[InferenceServer, EdgeCameraClient, str]
    ) -> None:
        """Client register() causes camera to appear in server dashboard state."""
        _, client, base_url = active_env
        ok = client.register()
        assert ok is True

        resp = requests.get(f"{base_url}/api/v1/dashboard/state", timeout=2.0)
        data = resp.json()
        assert data["active_cameras"] >= 1
        cam_ids = [c["camera_id"] for c in data["cameras"]]
        assert "CAM_STREAM_01" in cam_ids

    def test_client_stream_frame_emits_ai_log_record(
        self, active_env: Tuple[InferenceServer, EdgeCameraClient, str]
    ) -> None:
        """Each streamed frame generates a structured log entry on server."""
        srv, client, base_url = active_env
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        res = client.stream_frame_post(frame, int(time.time() * 1000))
        assert res is not None

        # Check server logger
        logs = srv.soc_logger.query_logs(camera_id="CAM_STREAM_01")
        assert len(logs) >= 1
        assert logs[0]["camera_id"] == "CAM_STREAM_01"

    def test_client_stream_with_simulated_action_updates_ai_truth(
        self, active_env: Tuple[InferenceServer, EdgeCameraClient, str]
    ) -> None:
        """Client X-Test-Action header influences server AI reasoning truth."""
        srv, client, base_url = active_env
        client.test_action = "WEAPON_THREAT"
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        res = client.stream_frame_post(frame, int(time.time() * 1000))
        assert res is not None
        assert res["primary_action"] == "WEAPON_THREAT"

        # Check latest incident on server
        resp = requests.get(f"{base_url}/api/v1/dashboard/state", timeout=2.0)
        state = resp.json()
        assert state["latest_incident"] is not None
        assert state["latest_incident"]["primary_action"] == "WEAPON_THREAT"
        assert state["latest_incident"]["severity"] in ("high", "critical")

    def test_evidence_ledger_linked_with_log_chain_hash(
        self, active_env: Tuple[InferenceServer, EdgeCameraClient, str]
    ) -> None:
        """Verify evidence chain_hash is preserved in server structured log."""
        srv, client, base_url = active_env
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        res = client.stream_frame_post(frame, int(time.time() * 1000))
        assert "chain_hash" in res

        logs = srv.soc_logger.query_logs(camera_id="CAM_STREAM_01")
        assert len(logs) >= 1
        assert logs[0]["chain_hash"] == res["chain_hash"]

    def test_multi_client_concurrent_logging(
        self, active_env: Tuple[InferenceServer, EdgeCameraClient, str]
    ) -> None:
        """Multiple camera clients streaming concurrently create distinct logs without race conditions."""
        srv, _, base_url = active_env
        clients = [
            EdgeCameraClient(server_url=base_url, camera_id=f"CONCURRENT_CAM_{i}", headless=True)
            for i in range(3)
        ]
        frame = np.zeros((120, 160, 3), dtype=np.uint8)

        def worker(c: EdgeCameraClient) -> None:
            c.stream_frame_post(frame, int(time.time() * 1000))

        threads = [threading.Thread(target=worker, args=(c,)) for c in clients]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(3):
            cam_logs = srv.soc_logger.query_logs(camera_id=f"CONCURRENT_CAM_{i}")
            assert len(cam_logs) >= 1

    def test_sse_broadcasts_live_log_entry(
        self, active_env: Tuple[InferenceServer, EdgeCameraClient, str]
    ) -> None:
        """Server broadcasts live log payload via Server-Sent Events."""
        srv, client, base_url = active_env
        resp = requests.get(f"{base_url}/api/v1/dashboard/events", stream=True, timeout=3.0)
        assert resp.status_code == 200

        # Post a frame from client in separate thread
        def push_frame() -> None:
            time.sleep(0.2)
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            client.stream_frame_post(frame, int(time.time() * 1000))

        th = threading.Thread(target=push_frame)
        th.start()

        # Read SSE events
        chunks_read = []
        for line_bytes in resp.iter_lines(chunk_size=1):
            if line_bytes:
                line = line_bytes.decode("utf-8")
                if "data:" in line:
                    chunks_read.append(line)
                    if len(chunks_read) >= 2:
                        break
        resp.close()
        th.join()

        assert len(chunks_read) >= 1
