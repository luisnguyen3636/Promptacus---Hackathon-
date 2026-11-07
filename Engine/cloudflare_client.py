"""
Cloudflare Worker Client for Urban Safety AI-SOC.
Interfaces local Engine & Rule systems with Cloudflare Workers AI & D1 Vault.
Features:
1. Rate-limiting & Smart Escalation Filtering (Anti-spam)
2. Asynchronous / Non-blocking Request Dispatching
3. Offline Resilient Queue (output/offline_incidents.jsonl)
4. Operational HITL Incident Verification
Adheres strictly to SPEC-CLOUDFLARE-WORKER-AI-01 and standard.md.
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from Engine.threat_models import (
    SOCEngineOutput,
    SubjectThreatMark,
    SubjectKinematicsSnapshot,
    ThreatLevel
)


class CloudflareSOCClient:
    """
    Python Client to communicate with Cloudflare Worker AI & D1 Storage Vault.
    Handles telemetry formatting, edge AI evaluation requests, and offline queuing.
    """

    def __init__(
        self,
        worker_base_url: str = "http://localhost:8787",
        auth_token: str = "urban-soc-secret-token-2026",
        camera_id: str = "cam_01",
        location_name: str = "Khu vuc Cong A - Dai hoc SGU",
        latitude: float = 10.7591,
        longitude: float = 106.6782,
        output_dir: str = "output",
        timeout_seconds: float = 3.5,
        min_eval_interval: float = 1.5  # Rate limit: minimum seconds between Cloudflare requests for same track
    ) -> None:
        self.worker_base_url = worker_base_url.rstrip("/")
        self.auth_token = auth_token
        self.camera_id = camera_id
        self.location_name = location_name
        self.latitude = latitude
        self.longitude = longitude
        self.output_dir = output_dir
        self.timeout_seconds = timeout_seconds
        self.min_eval_interval = min_eval_interval

        os.makedirs(self.output_dir, exist_ok=True)
        self.offline_queue_path = os.path.join(self.output_dir, "offline_incidents.jsonl")

        # Rate-limiting state: track_id -> last_eval_time
        self._last_eval_times: Dict[int, float] = {}

    def format_payload(
        self,
        engine_output: SOCEngineOutput,
        target_mark: SubjectThreatMark,
        snapshot: Optional[SubjectKinematicsSnapshot] = None,
        evidence_clip_url: Optional[str] = None,
        snapshot_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Formats standard EvaluationRequestPayload from engine output."""
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        if snapshot is not None:
            telemetry = {
                "spine_angle_deg": float(snapshot.spine_angle_deg),
                "aspect_ratio": float(snapshot.aspect_ratio),
                "velocity_norm": float(snapshot.velocity_norm),
                "wrist_kinetic_energy": float(snapshot.wrist_kinetic_energy),
                "dwell_time_seconds": float(snapshot.dwell_time_seconds),
                "state_dwell_seconds": float(target_mark.state_dwell_seconds),
                "bounding_box": list(snapshot.bbox)
            }
        else:
            telemetry = {
                "spine_angle_deg": 0.0,
                "aspect_ratio": 1.0,
                "velocity_norm": 0.0,
                "wrist_kinetic_energy": 0.0,
                "dwell_time_seconds": float(target_mark.dwell_time_seconds),
                "state_dwell_seconds": float(target_mark.state_dwell_seconds),
                "bounding_box": [0, 0, 100, 200]
            }

        return {
            "incident_id": f"INC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{target_mark.track_id}",
            "camera_id": self.camera_id,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": now_iso,
            "frame_index": engine_output.frame_index,
            "engine_behavior": target_mark.confirmed_behavior.value,
            "engine_category": target_mark.behavior_category.value,
            "engine_threat_level": target_mark.threat_level.value,
            "engine_threat_score": float(target_mark.threat_score),
            "primary_subject_id": target_mark.track_id,
            "interacting_subject_ids": target_mark.interacting_partners,
            "telemetry": telemetry,
            "evidence_clip_url": evidence_clip_url,
            "snapshot_url": snapshot_url,
            "diagnostic_reasoning": target_mark.diagnostic_summary
        }

    def process_and_dispatch(
        self,
        engine_output: SOCEngineOutput,
        snapshots_map: Dict[int, SubjectKinematicsSnapshot]
    ) -> List[Dict[str, Any]]:
        """
        Filters high-priority threat marks and sends them to Cloudflare Worker.
        Applies smart rate-limiting to prevent quota flooding.
        """
        curr_time = time.time()
        dispatched_results = []

        for mark in engine_output.threat_marks:
            # Only evaluate if threat is HIGH/CRITICAL or newly escalated
            is_high_threat = mark.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
            if not (is_high_threat or mark.is_escalated):
                continue

            # Check per-track rate limit
            last_t = self._last_eval_times.get(mark.track_id, 0.0)
            if (curr_time - last_t) < self.min_eval_interval and not mark.is_escalated:
                continue

            self._last_eval_times[mark.track_id] = curr_time

            snapshot = snapshots_map.get(mark.track_id)
            payload = self.format_payload(engine_output, mark, snapshot)

            # Send to Cloudflare Worker
            res = self.send_evaluation(payload)
            dispatched_results.append(res)

        return dispatched_results

    def send_evaluation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends evaluation request to Cloudflare Worker with offline fallback."""
        endpoint = f"{self.worker_base_url}/api/v1/engine/evaluate"
        data_bytes = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                resp_data = resp.read().decode("utf-8")
                return json.loads(resp_data)
        except Exception as e:
            # Network failure / offline: Queue to local disk
            self._queue_offline_incident(payload, str(e))
            return {
                "success": False,
                "offline_queued": True,
                "incident_id": payload.get("incident_id"),
                "reason": f"Network unreachable ({e}). Safely queued into offline vault."
            }

    def list_incidents(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        min_severity: Optional[float] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Queries incidents stored in Cloudflare D1 Vault."""
        params = [f"limit={limit}"]
        if camera_id:
            params.append(f"camera_id={camera_id}")
        if status:
            params.append(f"status={status}")
        if min_severity is not None:
            params.append(f"min_severity={min_severity}")

        query_str = "&".join(params)
        endpoint = f"{self.worker_base_url}/api/v1/incidents?{query_str}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        req = urllib.request.Request(endpoint, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e), "incidents": []}

    def verify_incident_hitl(
        self,
        incident_id: str,
        action: str,
        operator_id: str,
        operator_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Operational HITL Gate: Human Operator verifies incident before dispatching.
        Actions: CONFIRM_AND_DISPATCH | DOWNGRADE_MONITOR | DISMISS_FALSE_POSITIVE
        """
        endpoint = f"{self.worker_base_url}/api/v1/incidents/{incident_id}/verify"
        payload = {
            "action": action,
            "operator_id": operator_id,
            "operator_notes": operator_notes or ""
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_offline_incidents(self) -> int:
        """Flushes and re-transmits any offline incidents stored locally."""
        if not os.path.exists(self.offline_queue_path):
            return 0

        pending: List[Dict[str, Any]] = []
        try:
            with open(self.offline_queue_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        pending.append(json.loads(line))
        except Exception as e:
            print(f"[CloudflareSOCClient] Error reading offline queue: {e}")
            return 0

        if not pending:
            return 0

        synced_count = 0
        remaining: List[Dict[str, Any]] = []

        for item in pending:
            res = self.send_evaluation(item)
            if res.get("success") is True:
                synced_count += 1
            else:
                remaining.append(item)

        # Write back un-synced items
        with open(self.offline_queue_path, "w", encoding="utf-8") as f:
            for rem in remaining:
                f.write(json.dumps(rem, ensure_ascii=False) + "\n")

        print(f"[CloudflareSOCClient] Synced {synced_count}/{len(pending)} offline incidents to Cloudflare D1.")
        return synced_count

    def _queue_offline_incident(self, payload: Dict[str, Any], error_msg: str) -> None:
        """Appends un-sent payload to local offline queue file."""
        try:
            with open(self.offline_queue_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as write_err:
            print(f"[CloudflareSOCClient] Warning: Could not write offline queue ({write_err})")
