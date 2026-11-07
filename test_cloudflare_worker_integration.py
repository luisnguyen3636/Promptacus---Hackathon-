"""
Automated Verification Suite for Cloudflare Worker AI & D1 Storage Integration.
Tests:
1. Telemetry & Incident Schema Validation
2. Workers AI 10-point Severity & False Positive Evaluation
3. Multi-dimensional Forensic Metadata Storage (Time, Location, Subject Traits, Weapons, Victims, Dispatch)
4. Operational HITL Gate Verification (AWAITING_OPERATOR_VERIFICATION -> OPERATOR_CONFIRMED)
5. Python Cloudflare Client HTTP Integration & Offline Queue Resilience
Adheres strictly to PLAN-CLOUDFLARE-WORKER-AI-01.
"""

import os
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
from datetime import datetime

from Engine.threat_models import (
    SOCEngineOutput,
    SubjectThreatMark,
    SubjectKinematicsSnapshot,
    ThreatLevel,
    BehaviorType,
    BehaviorCategory
)
from Engine.cloudflare_client import CloudflareSOCClient


# =============================================================================
# Mock Cloudflare Worker Server for End-to-End HTTP Testing
# =============================================================================

class MockCloudflareWorkerHandler(BaseHTTPRequestHandler):
    """
    Simulates Cloudflare Worker Edge Runtime:
    - Workers AI evaluation engine
    - D1 SQL Database storage in-memory
    - Operational HITL verification endpoints
    """
    incidents_db: Dict[str, Dict[str, Any]] = {}
    audit_logs: list = []

    def log_message(self, format, *args):
        # Suppress standard HTTP request logging in test stdout
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/v1/health":
            self._send_json({
                "status": "ONLINE",
                "service": "Mock Cloudflare Worker Edge Gateway",
                "workers_ai_ready": True,
                "d1_database_ready": True
            })
            return

        if self.path.startswith("/api/v1/incidents"):
            incidents_list = list(self.incidents_db.values())
            self._send_json({
                "incidents": incidents_list,
                "count": len(incidents_list),
                "limit": 20,
                "offset": 0
            })
            return

        self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8")
        payload = json.loads(post_body) if post_body else {}

        # 1. Route: POST /api/v1/engine/evaluate
        if self.path == "/api/v1/engine/evaluate":
            incident_id = payload.get("incident_id") or f"INC_{int(time.time()*1000)}"
            behavior = payload.get("engine_behavior", "NORMAL")
            telemetry = payload.get("telemetry", {})

            # Simulate Workers AI 10-point evaluation logic
            wrist_energy = telemetry.get("wrist_kinetic_energy", 0.0)
            dwell_time = telemetry.get("dwell_time_seconds", 0.0)

            if "FIGHT" in behavior or "GRAPPLE" in behavior:
                score10 = 9.5 if wrist_energy > 1200 else 8.8
                fp_prob = 0.08
                verdict = "CRITICAL_EMERGENCY"
                weapon_type = "NONE"
                has_weapon = False
                victim_cond = "UNDER_ATTACK"
                dispatch_priority = "IMMEDIATE_RESPONSE"
                dispatch_units = ["POLICE", "SECURITY_GUARD"]
            elif "FALLEN" in behavior:
                score10 = 9.4
                fp_prob = 0.05
                verdict = "CRITICAL_EMERGENCY"
                weapon_type = "NONE"
                has_weapon = False
                victim_cond = "FALLEN_UNRESPONSIVE"
                dispatch_priority = "IMMEDIATE_RESPONSE"
                dispatch_units = ["AMBULANCE", "SECURITY_GUARD"]
            elif "CONCEAL" in behavior:
                score10 = 7.8
                fp_prob = 0.20
                verdict = "SUSPICIOUS_MONITOR"
                weapon_type = "CONCEALED_FIREARM"
                has_weapon = True
                victim_cond = "NONE"
                dispatch_priority = "URGENT"
                dispatch_units = ["POLICE", "SECURITY_GUARD"]
            elif "LOITER" in behavior:
                score10 = 6.8 if dwell_time > 20 else 4.8
                fp_prob = 0.40
                verdict = "SUSPICIOUS_MONITOR"
                weapon_type = "NONE"
                has_weapon = False
                victim_cond = "NONE"
                dispatch_priority = "ROUTINE"
                dispatch_units = ["SECURITY_GUARD"]
            else:
                score10 = 1.5
                fp_prob = 0.90
                verdict = "BENIGN_ACTIVITY"
                weapon_type = "NONE"
                has_weapon = False
                victim_cond = "NONE"
                dispatch_priority = "DISMISS"
                dispatch_units = []

            evaluation = {
                "severity_score_10": score10,
                "false_positive_probability": fp_prob,
                "is_false_positive": fp_prob >= 0.70,
                "threat_verdict": verdict,
                "subject_features": {
                    "posture_assessment": "Assessed physical posture",
                    "suspicious_concealment": has_weapon,
                    "movement_intent": "Active observation",
                    "estimated_threat_actor_count": 1
                },
                "weapons_identified": {
                    "has_weapon_indicator": has_weapon,
                    "weapon_type": weapon_type,
                    "weapon_confidence": 0.85 if has_weapon else 0.0,
                    "description": "Detected weapon signature" if has_weapon else "No overt weapon"
                },
                "victim_assessment": {
                    "has_victim_present": victim_cond != "NONE",
                    "victim_condition": victim_cond,
                    "bystander_count": 0
                },
                "dispatch_recommendation": {
                    "priority": dispatch_priority,
                    "recommended_units": dispatch_units,
                    "action_notes": f"Tactical response required for {behavior}"
                },
                "investigation_summary": f"Workers AI verified {behavior} incident with severity {score10}/10."
            }

            # Persist to Mock D1 Vault with mandatory AWAITING_OPERATOR_VERIFICATION
            record = {
                "id": incident_id,
                "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                "camera_id": payload.get("camera_id"),
                "location_name": payload.get("location_name"),
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
                "engine_behavior": behavior,
                "engine_threat_score": payload.get("engine_threat_score", 0.0),
                "ai_severity_score_10": score10,
                "false_positive_prob": fp_prob,
                "is_false_positive": fp_prob >= 0.70,
                "threat_verdict": verdict,
                "subject_features": evaluation["subject_features"],
                "weapons_identified": evaluation["weapons_identified"],
                "victim_assessment": evaluation["victim_assessment"],
                "dispatch_recommendation": evaluation["dispatch_recommendation"],
                "investigation_summary": evaluation["investigation_summary"],
                "operator_status": "AWAITING_OPERATOR_VERIFICATION",
                "operator_id": None,
                "verified_at": None,
                "operator_notes": None
            }
            self.incidents_db[incident_id] = record

            self._send_json({
                "success": True,
                "incident_id": incident_id,
                "operator_status": "AWAITING_OPERATOR_VERIFICATION",
                "evaluation": evaluation,
                "persisted_to_d1": True
            }, 201)
            return

        # 2. Route: POST /api/v1/incidents/:id/verify (HITL Gate)
        if self.path.startswith("/api/v1/incidents/") and self.path.endswith("/verify"):
            parts = self.path.split("/")
            incident_id = parts[4]

            if incident_id not in self.incidents_db:
                self._send_json({"error": "Incident not found"}, 404)
                return

            action = payload.get("action")
            operator_id = payload.get("operator_id")
            notes = payload.get("operator_notes", "")

            new_status = "OPERATOR_CONFIRMED" if action == "CONFIRM_AND_DISPATCH" else (
                "DISMISSED_FALSE_POSITIVE" if action == "DISMISS_FALSE_POSITIVE" else "AWAITING_OPERATOR_VERIFICATION"
            )

            rec = self.incidents_db[incident_id]
            rec["operator_status"] = new_status
            rec["operator_id"] = operator_id
            rec["verified_at"] = datetime.now().isoformat()
            rec["operator_notes"] = notes

            self._send_json({
                "success": True,
                "message": f"Incident successfully updated to {new_status}",
                "incident": rec
            })
            return

        self._send_json({"error": "Not Found"}, 404)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


# =============================================================================
# Automated Verification Tests
# =============================================================================

def test_payload_schema_and_formatting():
    print("\n--- [TEST 1/5] Testing Telemetry & Payload Schema Formatting ---")
    client = CloudflareSOCClient(
        worker_base_url="http://127.0.0.1:8787",
        camera_id="cam_gate_01",
        location_name="Cong A - Dai hoc SGU",
        latitude=10.7591,
        longitude=106.6782
    )

    mark = SubjectThreatMark(
        track_id=1,
        threat_level=ThreatLevel.CRITICAL,
        threat_score=0.95,
        confirmed_behavior=BehaviorType.FIGHTING_STRIKE,
        behavior_category=BehaviorCategory.IN_PROGRESS_CRIME,
        dwell_time_seconds=12.5,
        state_dwell_seconds=4.2,
        is_escalated=True,
        requires_operator_attention=True,
        interacting_partners=[2],
        diagnostic_summary="Violent fighting strike with ID #2",
        color_hex="#FF1744"
    )

    out = SOCEngineOutput(
        frame_index=150,
        timestamp="2026-11-07T14:30:00.000Z",
        subjects_count=2,
        threat_marks=[mark],
        highest_threat_level=ThreatLevel.CRITICAL,
        highest_threat_score=0.95,
        active_alerts=["FIGHTING_STRIKE ID #1"]
    )

    payload = client.format_payload(out, mark)

    # Assert standard fields
    assert payload["camera_id"] == "cam_gate_01"
    assert payload["location_name"] == "Cong A - Dai hoc SGU"
    assert payload["latitude"] == 10.7591
    assert payload["longitude"] == 106.6782
    assert payload["engine_behavior"] == "FIGHTING_STRIKE"
    assert payload["engine_threat_level"] == "CRITICAL"
    assert payload["engine_threat_score"] == 0.95
    assert payload["primary_subject_id"] == 1
    assert payload["interacting_subject_ids"] == [2]
    assert "telemetry" in payload
    assert payload["telemetry"]["state_dwell_seconds"] == 4.2
    assert payload["telemetry"]["bounding_box"] == [0, 0, 100, 200]

    print("  -> PASSED: Payload formatted with 100% adherence to Cloudflare Worker schema.")


def test_ai_severity_and_false_positive_evaluation(client: CloudflareSOCClient):
    print("\n--- [TEST 2/5] Testing Workers AI 10-Point Severity & False Positive Analysis ---")

    # Scenario A: Violent Fighting Strike
    fight_payload = {
        "camera_id": "cam_gate_01",
        "location_name": "Cong A",
        "latitude": 10.7591,
        "longitude": 106.6782,
        "timestamp": datetime.now().isoformat(),
        "frame_index": 100,
        "engine_behavior": "FIGHTING_STRIKE",
        "engine_category": "IN_PROGRESS_CRIME",
        "engine_threat_level": "CRITICAL",
        "engine_threat_score": 0.95,
        "primary_subject_id": 10,
        "interacting_subject_ids": [11],
        "telemetry": {
            "spine_angle_deg": 15.0,
            "aspect_ratio": 2.2,
            "velocity_norm": 0.8,
            "wrist_kinetic_energy": 1450.0,
            "dwell_time_seconds": 15.0,
            "state_dwell_seconds": 3.0,
            "bounding_box": [100, 100, 200, 300]
        },
        "diagnostic_reasoning": "High wrist kinetic energy violent strike"
    }

    res_fight = client.send_evaluation(fight_payload)
    assert res_fight["success"] is True
    eval_f = res_fight["evaluation"]
    # Must evaluate on 10-point scale: severity >= 8.5/10
    assert 8.5 <= eval_f["severity_score_10"] <= 10.0, f"Expected severity >= 8.5, got {eval_f['severity_score_10']}"
    # False positive probability must be low (< 0.15)
    assert eval_f["false_positive_probability"] <= 0.15
    assert eval_f["is_false_positive"] is False
    assert eval_f["threat_verdict"] == "CRITICAL_EMERGENCY"
    print(f"  -> Scenario A (FIGHTING): Severity = {eval_f['severity_score_10']}/10, FP Prob = {eval_f['false_positive_probability']*100:.0f}%, Verdict = {eval_f['threat_verdict']}.")

    # Scenario B: Benign Walking / False Alarm
    benign_payload = {
        "camera_id": "cam_gate_01",
        "location_name": "Cong A",
        "latitude": 10.7591,
        "longitude": 106.6782,
        "timestamp": datetime.now().isoformat(),
        "frame_index": 105,
        "engine_behavior": "NORMAL",
        "engine_category": "BENIGN",
        "engine_threat_level": "LOW",
        "engine_threat_score": 0.10,
        "primary_subject_id": 15,
        "telemetry": {
            "spine_angle_deg": 5.0,
            "aspect_ratio": 2.6,
            "velocity_norm": 0.3,
            "wrist_kinetic_energy": 120.0,
            "dwell_time_seconds": 5.0,
            "state_dwell_seconds": 5.0,
            "bounding_box": [150, 100, 230, 300]
        },
        "diagnostic_reasoning": "Normal gait speed upright posture"
    }

    res_benign = client.send_evaluation(benign_payload)
    eval_b = res_benign["evaluation"]
    # Benign severity <= 3.0/10
    assert eval_b["severity_score_10"] <= 3.0
    # False positive probability >= 0.70 (marked as false alarm)
    assert eval_b["false_positive_probability"] >= 0.70
    assert eval_b["is_false_positive"] is True
    print(f"  -> Scenario B (BENIGN): Severity = {eval_b['severity_score_10']}/10, FP Prob = {eval_b['false_positive_probability']*100:.0f}%, is_false_positive = {eval_b['is_false_positive']}.")


def test_multi_dimensional_forensic_storage(client: CloudflareSOCClient):
    print("\n--- [TEST 3/5] Testing Multi-Dimensional Forensic Metadata Storage in D1 ---")

    # Scenario C: Concealed Weapon Reach
    conceal_payload = {
        "camera_id": "cam_server_room_02",
        "location_name": "Phong May Chu - Tang 3",
        "latitude": 10.7595,
        "longitude": 106.6788,
        "timestamp": datetime.now().isoformat(),
        "frame_index": 200,
        "engine_behavior": "CONCEALED_REACH",
        "engine_category": "PRE_CRIME",
        "engine_threat_level": "HIGH",
        "engine_threat_score": 0.65,
        "primary_subject_id": 25,
        "telemetry": {
            "spine_angle_deg": 12.0,
            "aspect_ratio": 2.4,
            "velocity_norm": 0.15,
            "wrist_kinetic_energy": 80.0,
            "dwell_time_seconds": 6.0,
            "state_dwell_seconds": 4.0,
            "bounding_box": [200, 150, 280, 350]
        },
        "diagnostic_reasoning": "Right hand hidden behind waistband while approaching secure door"
    }

    res = client.send_evaluation(conceal_payload)
    inc_id = res["incident_id"]
    eval_c = res["evaluation"]

    # 1. Subject traits
    assert "subject_features" in eval_c
    assert "posture_assessment" in eval_c["subject_features"]
    assert eval_c["subject_features"]["suspicious_concealment"] is True

    # 2. Weapons
    assert "weapons_identified" in eval_c
    assert eval_c["weapons_identified"]["has_weapon_indicator"] is True
    assert eval_c["weapons_identified"]["weapon_type"] == "CONCEALED_FIREARM"
    assert eval_c["weapons_identified"]["weapon_confidence"] > 0.50

    # 3. Tactical Dispatch recommendation
    assert "dispatch_recommendation" in eval_c
    assert "POLICE" in eval_c["dispatch_recommendation"]["recommended_units"]
    assert eval_c["dispatch_recommendation"]["priority"] in ("URGENT", "IMMEDIATE_RESPONSE")

    # Query back from D1 Vault
    list_res = client.list_incidents(camera_id="cam_server_room_02")
    assert list_res["count"] >= 1
    found = next((i for i in list_res["incidents"] if i["id"] == inc_id), None)
    assert found is not None
    assert found["location_name"] == "Phong May Chu - Tang 3"
    assert found["latitude"] == 10.7595
    assert found["weapons_identified"]["has_weapon_indicator"] is True
    assert found["operator_status"] == "AWAITING_OPERATOR_VERIFICATION"

    print("  -> PASSED: Time, GPS, Subject Features, Weapon Signature, Victims, and Dispatch saved in D1.")


def test_operational_hitl_verification_gate(client: CloudflareSOCClient):
    print("\n--- [TEST 4/5] Testing Operational Human-in-the-Loop (HITL) Verification Gate ---")

    # 1. Create a high-priority incident
    payload = {
        "camera_id": "cam_gate_01",
        "location_name": "Cong A",
        "latitude": 10.7591,
        "longitude": 106.6782,
        "timestamp": datetime.now().isoformat(),
        "frame_index": 300,
        "engine_behavior": "FIGHTING_STRIKE",
        "engine_category": "IN_PROGRESS_CRIME",
        "engine_threat_level": "CRITICAL",
        "engine_threat_score": 0.95,
        "primary_subject_id": 99,
        "telemetry": {
            "spine_angle_deg": 18.0,
            "aspect_ratio": 2.1,
            "velocity_norm": 0.9,
            "wrist_kinetic_energy": 1600.0,
            "dwell_time_seconds": 10.0,
            "state_dwell_seconds": 2.0,
            "bounding_box": [120, 100, 220, 300]
        },
        "diagnostic_reasoning": "Severe violent confrontation in progress"
    }

    res = client.send_evaluation(payload)
    inc_id = res["incident_id"]

    # MUST initialize at AWAITING_OPERATOR_VERIFICATION
    assert res["operator_status"] == "AWAITING_OPERATOR_VERIFICATION"

    # Verify query shows awaiting verification
    incidents = client.list_incidents()
    target_inc = next((i for i in incidents["incidents"] if i["id"] == inc_id), None)
    assert target_inc["operator_status"] == "AWAITING_OPERATOR_VERIFICATION"
    print("  -> Initial State: 'AWAITING_OPERATOR_VERIFICATION' (Automated dispatch blocked by HITL).")

    # 2. Human Operator performs CONFIRM_AND_DISPATCH
    verify_res = client.verify_incident_hitl(
        incident_id=inc_id,
        action="CONFIRM_AND_DISPATCH",
        operator_id="OP_LEAD_NGUYEN",
        operator_notes="Xác nhận ẩu đả nghiêm trọng qua camera trực tiếp. Điều động bảo vệ và báo 113."
    )

    assert verify_res["success"] is True
    updated_inc = verify_res["incident"]
    assert updated_inc["operator_status"] == "OPERATOR_CONFIRMED"
    assert updated_inc["operator_id"] == "OP_LEAD_NGUYEN"
    assert updated_inc["verified_at"] is not None
    assert "Xác nhận ẩu đả" in updated_inc["operator_notes"]

    print("  -> Operator Action: 'CONFIRM_AND_DISPATCH' successfully approved incident for police dispatch.")


def test_offline_queue_and_resilience():
    print("\n--- [TEST 5/5] Testing Client Offline Resilience & Auto-Sync Queue ---")
    offline_dir = "output"
    queue_file = os.path.join(offline_dir, "offline_incidents.jsonl")

    # Point client to invalid/dead URL to simulate network outage
    dead_client = CloudflareSOCClient(
        worker_base_url="http://127.0.0.1:9999", # Non-existent port
        output_dir=offline_dir,
        timeout_seconds=0.5
    )

    test_payload = {
        "incident_id": "INC_OFFLINE_TEST_01",
        "camera_id": "cam_offline_01",
        "engine_behavior": "FALLEN_COLLAPSE",
        "engine_threat_score": 0.95,
        "telemetry": {"wrist_kinetic_energy": 0.0, "dwell_time_seconds": 10.0}
    }

    # Send should safely failover to offline queue
    res = dead_client.send_evaluation(test_payload)
    assert res["success"] is False
    assert res["offline_queued"] is True
    assert os.path.exists(queue_file)

    # Check offline queue contents
    with open(queue_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) >= 1
    stored_obj = json.loads(lines[-1])
    assert stored_obj["incident_id"] == "INC_OFFLINE_TEST_01"
    assert stored_obj["engine_behavior"] == "FALLEN_COLLAPSE"

    print("  -> Offline Detection: Network failure gracefully caught; payload persisted to output/offline_incidents.jsonl.")

    # Now point client to working mock server and sync
    live_client = CloudflareSOCClient(
        worker_base_url="http://127.0.0.1:8787",
        output_dir=offline_dir
    )
    synced = live_client.sync_offline_incidents()
    assert synced >= 1
    print(f"  -> Recovery & Sync: Successfully re-transmitted {synced} offline incident(s) to Cloudflare.")


# =============================================================================
# Main Verification Entrypoint
# =============================================================================

def run_all_tests():
    print("========================================================================")
    print(" URBAN SAFETY AI-SOC: CLOUDFLARE WORKER AI & D1 INTEGRATION VERIFICATION")
    print("========================================================================")

    # 1. Start Mock Cloudflare Worker Server on localhost:8787
    server_address = ("127.0.0.1", 8787)
    mock_server = HTTPServer(server_address, MockCloudflareWorkerHandler)
    server_thread = threading.Thread(target=mock_server.serve_forever, daemon=True)
    server_thread.start()
    print("[TestHarness] Mock Cloudflare Worker running at http://127.0.0.1:8787")

    client = CloudflareSOCClient(worker_base_url="http://127.0.0.1:8787")

    try:
        test_payload_schema_and_formatting()
        test_ai_severity_and_false_positive_evaluation(client)
        test_multi_dimensional_forensic_storage(client)
        test_operational_hitl_verification_gate(client)
        test_offline_queue_and_resilience()

        print("\n========================================================================")
        print(" ALL 5 CLOUDFLARE WORKER AI INTEGRATION PHASES PASSED SUCCESSFULLY (100%)")
        print("========================================================================")
    finally:
        mock_server.shutdown()
        mock_server.server_close()


if __name__ == "__main__":
    run_all_tests()
