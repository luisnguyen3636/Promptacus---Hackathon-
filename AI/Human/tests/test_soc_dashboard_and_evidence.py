"""Comprehensive Unit and Integration tests for SOC Dashboard, Camera Client-Server Streaming,
AI 4-Attempt Retry Policy, and Cryptographic Evidence Keeping (SHA-256, Merkle Chain).

Strictly adheres to AGENTS.md requirements:
- CD-01, CD-02: Strict Architectural Lock
- CD-04: Operational HITL Integrity (max state: AWAITING_OPERATOR_VERIFICATION, human confirmation required)
- CD-05: >= 30 test cases for rock-solid stability and zero bug tolerance.
"""

import base64
import json
import os
import socket
import threading
import time
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
import pytest
import requests

from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
from urbansoc.ai.retry_executor import AIRetryExhaustedError, execute_ai_with_retry
from urbansoc.client.edge_client import EdgeCameraClient
from urbansoc.evidence.keeper import (
    DEFAULT_HMAC_KEY,
    GENESIS_HASH,
    EvidenceKeeper,
    EvidenceRecord,
)
from urbansoc.server.inference_server import InferenceServer


def get_free_port() -> int:
    """Find a random available TCP port for isolated integration testing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ==============================================================================
# 1. EVIDENCE KEEPING & CRYPTOGRAPHIC INTEGRITY TESTS (10 TESTS)
# ==============================================================================

class TestEvidenceKeepingIntegrity:
    @pytest.fixture
    def keeper(self, tmp_path: pytest.TempPathFactory) -> EvidenceKeeper:
        return EvidenceKeeper(storage_dir=str(tmp_path / "evidence_test"))

    def test_compute_sha256(self) -> None:
        """Verify deterministic SHA-256 computation."""
        data = b"UrbanSafetyAI-SOC-Forensic-2026"
        digest1 = EvidenceKeeper.compute_sha256(data)
        digest2 = EvidenceKeeper.compute_sha256(data)
        assert digest1 == digest2
        assert len(digest1) == 64
        assert digest1 == "465a8de0f9496eefb4acc6d37273c56317e9f5d6b25dfddfd4e3f795561b3628"

    def test_compute_hmac_signature(self, keeper: EvidenceKeeper) -> None:
        """Verify HMAC-SHA256 signature generation."""
        data = b"Critical_Incident_Evidence_Frame_001"
        sig1 = keeper.compute_hmac(data)
        sig2 = keeper.compute_hmac(data)
        assert sig1 == sig2
        assert len(sig1) == 64

    def test_record_evidence_generates_valid_record(self, keeper: EvidenceKeeper) -> None:
        """Verify evidence recording persists JPEG keyframe, metadata, and hashes."""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(frame, "EVIDENCE", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        meta = {"threat": "CRITICAL", "action": "WEAPON_THREAT", "camera": "CAM_01"}

        rec = keeper.record_evidence(
            camera_id="CAM_01",
            frame_bgr=frame,
            metadata=meta,
            event_id="EVT_TEST_001",
        )

        assert rec.event_id == "EVT_TEST_001"
        assert rec.camera_id == "CAM_01"
        assert os.path.exists(rec.frame_path)
        assert rec.previous_chain_hash == GENESIS_HASH
        assert len(rec.chain_hash) == 64
        assert rec.verification_status == "VERIFIED_VALID"

    def test_verify_evidence_integrity_passes_untampered(self, keeper: EvidenceKeeper) -> None:
        """Verify that newly recorded evidence passes integrity check."""
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        rec = keeper.record_evidence(
            camera_id="CAM_02",
            frame_bgr=frame,
            metadata={"action": "FIGHTING"},
        )
        is_valid, msg = keeper.verify_evidence_integrity(rec)
        assert is_valid is True
        assert "cryptographically valid" in msg

    def test_verify_evidence_detects_frame_tampering(self, keeper: EvidenceKeeper) -> None:
        """Detect bit-level tampering in evidence image file."""
        frame = np.zeros((120, 120, 3), dtype=np.uint8)
        rec = keeper.record_evidence(
            camera_id="CAM_03",
            frame_bgr=frame,
            metadata={"action": "SNATCHING"},
        )
        # Modify file on disk to simulate tampering
        with open(rec.frame_path, "ab") as f:
            f.write(b"CORRUPTED_BYTES_INJECTED")

        is_valid, msg = keeper.verify_evidence_integrity(rec)
        assert is_valid is False
        assert "Tampering detected" in msg

    def test_verify_evidence_detects_missing_file(self, keeper: EvidenceKeeper) -> None:
        """Detect deleted evidence file."""
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        rec = keeper.record_evidence("CAM_01", frame, {"note": "test"})
        os.remove(rec.frame_path)

        is_valid, msg = keeper.verify_evidence_integrity(rec)
        assert is_valid is False
        assert "Evidence file missing" in msg

    def test_merkle_chain_continuity_multiple_blocks(self, keeper: EvidenceKeeper) -> None:
        """Verify unbroken Merkle chain across 5 sequential evidence records."""
        frame = np.zeros((60, 60, 3), dtype=np.uint8)
        for i in range(5):
            keeper.record_evidence(
                camera_id=f"CAM_0{i+1}",
                frame_bgr=frame,
                metadata={"seq": i},
                event_id=f"EVT_CHAIN_{i}",
            )

        assert len(keeper.records) == 5
        is_valid, errors = keeper.verify_chain_integrity()
        assert is_valid is True
        assert len(errors) == 0

        # Check hash chaining links
        for i in range(1, 5):
            assert keeper.records[i].previous_chain_hash == keeper.records[i - 1].chain_hash

    def test_merkle_chain_detects_retroactive_tampering(self, keeper: EvidenceKeeper) -> None:
        """Modifying an intermediate block's hash invalidates the chain."""
        frame = np.zeros((40, 40, 3), dtype=np.uint8)
        for i in range(3):
            keeper.record_evidence("CAM_01", frame, {"i": i}, event_id=f"EVT_TAMPER_{i}")

        # Tamper with block 1's chain_hash
        keeper.records[1].chain_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        is_valid, errors = keeper.verify_chain_integrity()
        assert is_valid is False
        assert len(errors) > 0

    def test_package_incident_evidence(self, keeper: EvidenceKeeper) -> None:
        """Verify packaging generates complete forensic evidence bundle with manifest."""
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        keeper.record_evidence("CAM_04", frame, {"action": "FALLEN"}, event_id="EVT_PKG_01")

        pkg = keeper.package_incident_evidence("EVT_PKG_01")
        assert pkg["event_id"] == "EVT_PKG_01"
        assert pkg["camera_id"] == "CAM_04"
        assert pkg["integrity_verified"] is True
        assert os.path.exists(pkg["manifest_path"])

        with open(pkg["manifest_path"], "r", encoding="utf-8") as f:
            manifest_content = f.read()
        assert "FORENSIC EVIDENCE MANIFEST" in manifest_content
        assert pkg["frame_sha256"] in manifest_content

    def test_load_ledger_replay(self, tmp_path: pytest.TempPathFactory) -> None:
        """Instantiating a new EvidenceKeeper from the same dir restores state."""
        store_dir = str(tmp_path / "replay_test")
        keeper1 = EvidenceKeeper(storage_dir=store_dir)
        frame = np.zeros((60, 60, 3), dtype=np.uint8)
        r1 = keeper1.record_evidence("CAM_01", frame, {"action": "A"}, event_id="EVT_01")
        r2 = keeper1.record_evidence("CAM_02", frame, {"action": "B"}, event_id="EVT_02")

        keeper2 = EvidenceKeeper(storage_dir=store_dir)
        assert len(keeper2.records) == 2
        assert keeper2.records[0].event_id == "EVT_01"
        assert keeper2.records[1].event_id == "EVT_02"
        assert keeper2.latest_chain_hash == r2.chain_hash


# ==============================================================================
# 2. AI RETRY MECHANISM (4 ATTEMPTS, 3S INTERVAL) TESTS (8 TESTS)
# ==============================================================================

class TestAIRetryMechanism:
    def test_retry_succeeds_first_attempt(self) -> None:
        """Succeeds immediately on attempt 1 without retries."""
        calls = 0

        def op() -> str:
            nonlocal calls
            calls += 1
            return "SUCCESS"

        res = execute_ai_with_retry(op, max_retries=4, retry_delay_seconds=0.01)
        assert res == "SUCCESS"
        assert calls == 1

    def test_retry_succeeds_on_second_attempt(self) -> None:
        """Fails on attempt 1, succeeds on attempt 2."""
        calls = 0

        def op() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionResetError("Connection dropped")
            return "SUCCESS_ON_2"

        res = execute_ai_with_retry(op, max_retries=4, retry_delay_seconds=0.01)
        assert res == "SUCCESS_ON_2"
        assert calls == 2

    def test_retry_succeeds_on_fourth_attempt(self) -> None:
        """Fails 3 times and succeeds on the 4th attempt."""
        calls = 0

        def op() -> str:
            nonlocal calls
            calls += 1
            if calls < 4:
                raise TimeoutError(f"Timeout on attempt {calls}")
            return "SUCCESS_ON_4"

        res = execute_ai_with_retry(op, max_retries=4, retry_delay_seconds=0.01)
        assert res == "SUCCESS_ON_4"
        assert calls == 4

    def test_retry_exhausted_raises_error(self) -> None:
        """Fails all 4 attempts and raises AIRetryExhaustedError."""
        calls = 0

        def op() -> None:
            nonlocal calls
            calls += 1
            raise RuntimeError("Persistent network outage")

        with pytest.raises(AIRetryExhaustedError) as exc_info:
            execute_ai_with_retry(op, max_retries=4, retry_delay_seconds=0.01)

        assert calls == 4
        assert exc_info.value.attempts == 4

    def test_retry_exhausted_invokes_fallback(self) -> None:
        """When 4 attempts fail, fallback_factory is executed safely."""
        calls = 0

        def op() -> None:
            nonlocal calls
            calls += 1
            raise ValueError("VLM API 500 error")

        fallback_called = False

        def fallback() -> Dict[str, str]:
            nonlocal fallback_called
            fallback_called = True
            return {"source": "local_fallback", "status": "safe"}

        res = execute_ai_with_retry(
            op,
            max_retries=4,
            retry_delay_seconds=0.01,
            fallback_factory=fallback,
        )
        assert calls == 4
        assert fallback_called is True
        assert res["source"] == "local_fallback"

    def test_retry_callback_invoked_on_each_failure(self) -> None:
        """on_retry callback receives attempt number and error."""
        attempts_recorded = []

        def on_retry_cb(attempt: int, err: Exception, delay: float) -> None:
            attempts_recorded.append((attempt, str(err)))

        def failing_op() -> None:
            raise KeyError("API Key rate limited")

        try:
            execute_ai_with_retry(
                failing_op,
                max_retries=4,
                retry_delay_seconds=0.01,
                on_retry=on_retry_cb,
            )
        except AIRetryExhaustedError:
            pass

        assert len(attempts_recorded) == 3  # Callback invoked before retries 2, 3, 4
        assert attempts_recorded[0][0] == 1
        assert attempts_recorded[1][0] == 2
        assert attempts_recorded[2][0] == 3

    def test_retry_timing_delay_respected(self) -> None:
        """Verify that retry delay is observed between attempts."""
        start = time.time()
        calls = 0

        def op() -> None:
            nonlocal calls
            calls += 1
            raise ConnectionError("Temporary blip")

        try:
            execute_ai_with_retry(op, max_retries=3, retry_delay_seconds=0.05)
        except AIRetryExhaustedError:
            pass

        elapsed = time.time() - start
        assert calls == 3
        assert elapsed >= 0.09  # 2 delays * 0.05s = 0.10s

    def test_client_analyze_frame_uses_retry_and_falls_back(self) -> None:
        """NvidiaVisionClient.analyze_frame handles API failure with retry and fallback."""
        client = NvidiaVisionClient(api_key="sk-antigravity-real-key-attempt")
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)

        # Force invalid base url to trigger network failure
        client.base_url = "http://127.0.0.1:54321/invalid_vlm"
        client.timeout_seconds = 0.1

        res = client.analyze_frame(
            frame=dummy,
            camera_id="CAM_01",
            action_hint="FIGHTING",
            ai_retry_delay=0.01,
            ai_max_retries=3,
        )
        assert res is not None
        assert "vlm_local_fallback" in res.get("source", "")
        assert res.get("action_type") == "FIGHTING"


# ==============================================================================
# 3. CAMERA CLIENT HTTP POST STREAMING TESTS (6 TESTS)
# ==============================================================================

class TestCameraClientHttpStreaming:
    @pytest.fixture
    def test_server(self, tmp_path: pytest.TempPathFactory) -> Tuple[InferenceServer, str]:
        port = get_free_port()
        srv = InferenceServer(
            host="127.0.0.1",
            port=port,
            output_dir=str(tmp_path / "server_out"),
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

    def test_client_registration_success(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify client registration with custom camera ID and name."""
        _, base_url = test_server
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="TEST_CAM_01",
            camera_name="Test Laptop A",
            headless=True,
        )
        ok = client.register()
        assert ok is True

    def test_client_stream_frame_post_success(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify direct HTTP POST video frame streaming."""
        _, base_url = test_server
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="TEST_CAM_02",
            camera_name="Test Laptop B",
            headless=True,
        )
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        now_ms = int(time.time() * 1000)

        res = client.stream_frame_post(frame, now_ms, timeout=2.0)
        assert res is not None
        assert res.get("status") == "processed"
        assert res.get("camera_id") == "TEST_CAM_02"
        assert "evidence" in res
        assert "chain_hash" in res

    def test_client_stream_frame_post_with_test_action(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify client test action header influences server behavioral analysis."""
        _, base_url = test_server
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="TEST_CAM_03",
            test_action="WEAPON_THREAT",
            headless=True,
        )
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        res = client.stream_frame_post(frame, int(time.time() * 1000))
        assert res is not None
        assert res.get("primary_action") == "WEAPON_THREAT"

    def test_client_stream_frame_post_retries_on_connection_error(self) -> None:
        """Client stream_frame_post retries upon connection failure and returns None."""
        client = EdgeCameraClient(
            server_url="http://127.0.0.1:59999",  # Unused port
            camera_id="RETRY_CAM",
            headless=True,
        )
        frame = np.zeros((60, 60, 3), dtype=np.uint8)
        res = client.stream_frame_post(
            frame,
            int(time.time() * 1000),
            timeout=0.1,
            max_retries=2,
            retry_delay_sec=0.01,
        )
        assert res is None

    def test_client_send_frame_wraps_stream_frame_post(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify that legacy send_frame delegates to stream_frame_post seamlessly."""
        _, base_url = test_server
        client = EdgeCameraClient(server_url=base_url, camera_id="CAM_LEGACY", headless=True)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        res = client.send_frame(frame, int(time.time() * 1000))
        assert res is not None
        assert res.get("camera_id") == "CAM_LEGACY"

    def test_multi_client_concurrent_registration(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Multiple clients register concurrently without collision."""
        _, base_url = test_server
        clients = [
            EdgeCameraClient(server_url=base_url, camera_id=f"CLIENT_CAM_{i}", headless=True)
            for i in range(4)
        ]
        results = [c.register() for c in clients]
        assert all(results)

        resp = requests.get(f"{base_url}/api/v1/cameras")
        data = resp.json()
        cam_ids = [c["camera_id"] for c in data["cameras"]]
        for i in range(4):
            assert f"CLIENT_CAM_{i}" in cam_ids


# ==============================================================================
# 4. SOC DASHBOARD & OPERATIONAL HITL TESTS (8 TESTS)
# ==============================================================================

class TestSOCDashboardAndHITL:
    @pytest.fixture
    def test_server(self, tmp_path: pytest.TempPathFactory) -> Tuple[InferenceServer, str]:
        port = get_free_port()
        srv = InferenceServer(
            host="127.0.0.1",
            port=port,
            output_dir=str(tmp_path / "dash_out"),
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

    def test_dashboard_html_served_on_root(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify GET / and GET /dashboard serve complete HTML dashboard with 200."""
        _, base_url = test_server
        resp1 = requests.get(f"{base_url}/", headers={"Accept": "text/html"}, timeout=2.0)
        assert resp1.status_code == 200
        assert "URBAN SAFETY AI-SOC COMMAND CENTER" in resp1.text
        assert "5-GATE FALSIFICATION PROTOCOL" in resp1.text
        assert "MERKLE CHAIN VERIFIED" in resp1.text

        resp2 = requests.get(f"{base_url}/dashboard", timeout=2.0)
        assert resp2.status_code == 200
        assert "BLIND-SPOT TRAJECTORY" in resp2.text

    def test_dashboard_state_api(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify GET /api/v1/dashboard/state returns structured JSON."""
        srv, base_url = test_server
        srv.record_dashboard_event({
            "camera_id": "CAM_01",
            "action": "WEAPON_THREAT",
            "severity": "CRITICAL",
            "reasoning": "Đối tượng mang hung khí",
        })

        resp = requests.get(f"{base_url}/api/v1/dashboard/state", timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert "cameras" in data
        assert "recent_logs" in data
        assert data["latest_incident"] is not None
        assert data["latest_incident"]["action"] == "WEAPON_THREAT"

    def test_operator_action_confirm_and_dispatch(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify operator CONFIRM_AND_DISPATCH logs confirmation."""
        _, base_url = test_server
        payload = {
            "action": "CONFIRM_AND_DISPATCH",
            "camera_id": "CAM_01",
            "event_id": "EVT_TEST_100",
            "operator_id": "OPERATOR_HA_LE",
            "notes": "Xác nhận cướp giật có hung khí, phát lệnh can thiệp.",
        }
        resp = requests.post(f"{base_url}/api/v1/operator/action", json=payload, timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "CONFIRM_AND_DISPATCH"
        assert data["operator_id"] == "OPERATOR_HA_LE"
        assert "verified_at" in data

    def test_operator_action_downgrade_monitor(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify operator DOWNGRADE_MONITOR updates state."""
        _, base_url = test_server
        payload = {
            "action": "DOWNGRADE_MONITOR",
            "camera_id": "CAM_02",
            "event_id": "EVT_TEST_101",
            "operator_id": "OPERATOR_TRAN_MINH",
        }
        resp = requests.post(f"{base_url}/api/v1/operator/action", json=payload, timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "DOWNGRADE_MONITOR"

    def test_operator_action_dismiss_false_positive(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify operator DISMISS_FALSE_POSITIVE."""
        _, base_url = test_server
        payload = {
            "action": "DISMISS_FALSE_POSITIVE",
            "camera_id": "CAM_03",
            "event_id": "EVT_TEST_102",
            "operator_id": "OPERATOR_NGUYEN_AN",
        }
        resp = requests.post(f"{base_url}/api/v1/operator/action", json=payload, timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "DISMISS_FALSE_POSITIVE"

    def test_evidence_verify_api(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify GET /api/v1/evidence/{event_id}/verify validates cryptographic hash."""
        srv, base_url = test_server
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        rec = srv.evidence_keeper.record_evidence(
            camera_id="CAM_01",
            frame_bgr=frame,
            metadata={"incident": "test"},
            event_id="EVT_VERIFY_200",
        )

        resp = requests.get(f"{base_url}/api/v1/evidence/EVT_VERIFY_200/verify", timeout=2.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == "EVT_VERIFY_200"
        assert data["integrity_verified"] is True
        assert data["frame_sha256"] == rec.frame_sha256

    def test_evidence_verify_api_404_on_unknown(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify 404 returned for non-existent evidence ID."""
        _, base_url = test_server
        resp = requests.get(f"{base_url}/api/v1/evidence/EVT_NONEXISTENT_999/verify", timeout=2.0)
        assert resp.status_code == 404

    def test_dashboard_sse_event_stream(self, test_server: Tuple[InferenceServer, str]) -> None:
        """Verify GET /api/v1/dashboard/events connects to SSE stream."""
        _, base_url = test_server
        resp = requests.get(f"{base_url}/api/v1/dashboard/events", stream=True, timeout=3.0)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("Content-Type", "")

        # Read first chunk
        for chunk in resp.iter_lines(chunk_size=1):
            if chunk:
                line = chunk.decode("utf-8")
                if "data:" in line:
                    assert "Connected to SOC Live Stream" in line or "init" in line
                    break
        resp.close()


# ==============================================================================
# 5. END-TO-END SOC WORKFLOW INTEGRATION TESTS (4 TESTS)
# ==============================================================================

class TestEndToEndSOCWorkflow:
    @pytest.fixture
    def test_server(self, tmp_path: pytest.TempPathFactory) -> Tuple[InferenceServer, str]:
        port = get_free_port()
        srv = InferenceServer(
            host="127.0.0.1",
            port=port,
            output_dir=str(tmp_path / "e2e_out"),
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

    def test_e2e_camera_stream_to_ai_to_evidence_to_dashboard(
        self, test_server: Tuple[InferenceServer, str]
    ) -> None:
        """Full pipeline: Client POST stream -> AI Reasoning -> Evidence Ledger -> Dashboard State."""
        srv, base_url = test_server
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_01",
            camera_name="CAM_01 - Cổng Chu Văn An",
            test_action="WEAPON_THREAT",
            headless=True,
        )

        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        now_ms = int(time.time() * 1000)
        res = client.stream_frame_post(frame, now_ms)

        assert res is not None
        assert res.get("primary_action") == "WEAPON_THREAT"
        assert "evidence" in res
        ev = res["evidence"]
        assert len(ev["frame_sha256"]) == 64
        assert len(ev["chain_hash"]) == 64

        # Verify incident appears in dashboard state
        resp = requests.get(f"{base_url}/api/v1/dashboard/state", timeout=2.0)
        state = resp.json()
        assert state["latest_incident"] is not None
        assert state["latest_incident"]["primary_action"] == "WEAPON_THREAT"

    def test_e2e_multi_camera_blind_spot_handover(
        self, test_server: Tuple[InferenceServer, str]
    ) -> None:
        """Blind spot reasoning output is emitted and contains target camera prediction."""
        _, base_url = test_server
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_01",
            test_action="RUNNING",
            headless=True,
        )
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        res = client.stream_frame_post(frame, int(time.time() * 1000))
        assert res is not None

        # Check VLM telemetry output
        vlm_data = res.get("nvidia_vlm_analysis") or res
        assert "multi_camera_blind_spot_reasoning" in vlm_data
        bs_info = vlm_data["multi_camera_blind_spot_reasoning"]
        assert bs_info.get("is_triggered") is True
        preds = bs_info.get("predicted_next_cameras", [])
        assert len(preds) >= 1
        assert "target_camera_name" in preds[0]

    def test_e2e_evidence_tamper_detection_via_api(
        self, test_server: Tuple[InferenceServer, str]
    ) -> None:
        """Tampering with image file on server disk causes API verification to fail."""
        srv, base_url = test_server
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        rec = srv.evidence_keeper.record_evidence("CAM_02", frame, {"action": "FIGHTING"}, event_id="EVT_TAMPER_API")

        # Initial check passes
        resp1 = requests.get(f"{base_url}/api/v1/evidence/EVT_TAMPER_API/verify")
        assert resp1.json()["integrity_verified"] is True

        # Tamper with file
        with open(rec.frame_path, "wb") as f:
            f.write(b"TAMPERED_MALICIOUS_DATA")

        resp2 = requests.get(f"{base_url}/api/v1/evidence/EVT_TAMPER_API/verify")
        assert resp2.json()["integrity_verified"] is False

    def test_e2e_hitl_guardrail_rule_cd04(
        self, test_server: Tuple[InferenceServer, str]
    ) -> None:
        """Verify strict HITL: Incident status is never auto-confirmed before human operator action."""
        _, base_url = test_server
        client = EdgeCameraClient(
            server_url=base_url,
            camera_id="CAM_01",
            test_action="WEAPON_THREAT",
            headless=True,
        )
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        res = client.stream_frame_post(frame, int(time.time() * 1000))
        assert res is not None

        vlm_data = res.get("nvidia_vlm_analysis") or res
        incident_status = vlm_data.get("incident_status")
        # Assert never auto-confirmed
        assert incident_status != "OPERATOR_CONFIRMED", "Violation of CD-04 HITL"
        assert incident_status in ("OBSERVING", "MONITORING", "AWAITING_OPERATOR_VERIFICATION")
