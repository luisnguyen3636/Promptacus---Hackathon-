"""Dedicated Logging and Audit Engine for Urban Safety AI-SOC."""

from datetime import datetime, timezone
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("urbansoc.telemetry.soc_logger")


class SOCLogger:
    """Manages 4-layer persistent and real-time structured logging for AI-SOC events."""

    def __init__(self, log_dir: str = "output/logs", max_memory_entries: int = 250) -> None:
        self.log_dir = os.path.abspath(log_dir)
        self.max_memory_entries = max_memory_entries
        self.lock = threading.Lock()

        os.makedirs(self.log_dir, exist_ok=True)

        self.reasoning_jsonl_path = os.path.join(self.log_dir, "ai_soc_reasoning.jsonl")
        self.alerts_log_path = os.path.join(self.log_dir, "ai_soc_alerts.log")
        self.audit_log_path = os.path.join(self.log_dir, "ai_soc_audit.log")

        # In-memory rolling log buffer for real-time dashboard viewing and querying
        self.memory_logs: List[Dict[str, Any]] = []

    def record_ai_reasoning(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record full structured AI inference & tactical reasoning into JSONL and memory."""
        now = datetime.now(timezone.utc)
        iso_time = now.isoformat()
        display_time = now.strftime("%H:%M:%S")

        cam_id = str(event_data.get("camera_id") or "UNKNOWN_CAM")
        cam_name = str(
            event_data.get("active_camera", {}).get("camera_name")
            or event_data.get("camera_name")
            or cam_id
        )
        sev = str(event_data.get("severity") or event_data.get("highest_threat") or "low").upper()
        action = str(event_data.get("primary_action") or event_data.get("action_type") or "NORMAL").upper()
        score = float(event_data.get("highest_threat_score") or event_data.get("threat_score") or 0.0)
        summary = str(event_data.get("reasoning") or event_data.get("description") or f"AI phát hiện hành vi {action}")
        chain_hash = event_data.get("chain_hash") or event_data.get("evidence", {}).get("chain_hash")
        event_id = event_data.get("event_id")

        log_item = {
            "timestamp": iso_time,
            "time": display_time,
            "type": "AI_REASONING",
            "camera_id": cam_id,
            "camera_name": cam_name,
            "severity": sev,
            "action": action,
            "threat_score": score,
            "summary": summary,
            "chain_hash": chain_hash,
            "event_id": event_id,
            "anti_false_positive_audit": event_data.get("anti_false_positive_audit", {}),
            "multi_camera_blind_spot_reasoning": event_data.get("multi_camera_blind_spot_reasoning", {}),
            "operator_directives": event_data.get("operator_dashboard_directives", {}),
            "raw_event": event_data,
        }

        with self.lock:
            # 1. Append to persistent JSONL
            try:
                with open(self.reasoning_jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_item, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Failed to write to %s: %s", self.reasoning_jsonl_path, e)

            # 2. Append to persistent alerts.log if elevated severity
            if sev in ("HIGH", "CRITICAL") or action != "NORMAL":
                alert_line = (
                    f"[{iso_time}] [{sev}] [{cam_id} - {cam_name}] "
                    f"Action: {action} (Score: {score:.1f}/100) | "
                    f"AI Reasoning: {summary} | Merkle: {chain_hash or 'N/A'}\n"
                )
                try:
                    with open(self.alerts_log_path, "a", encoding="utf-8") as f:
                        f.write(alert_line)
                except Exception as e:
                    logger.error("Failed to write alert log: %s", e)

            # 3. Add to in-memory buffer
            self.memory_logs.append(log_item)
            if len(self.memory_logs) > self.max_memory_entries:
                self.memory_logs.pop(0)

        return log_item

    def record_audit(
        self,
        operator_id: str,
        action: str,
        camera_id: str,
        event_id: Optional[str] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record Human Operator (Operational HITL) directive into audit log."""
        now = datetime.now(timezone.utc)
        iso_time = now.isoformat()
        display_time = now.strftime("%H:%M:%S")

        audit_item = {
            "timestamp": iso_time,
            "time": display_time,
            "type": "OPERATOR_AUDIT",
            "operator_id": operator_id,
            "action": action.upper(),
            "camera_id": camera_id,
            "event_id": event_id,
            "notes": notes,
            "summary": f"Vận hành viên {operator_id} thực hiện [{action.upper()}] cho sự cố {event_id or camera_id}. Ghi chú: {notes or 'Không có'}",
        }

        audit_line = (
            f"[{iso_time}] [AUDIT] Operator: {operator_id} | Decision: {action.upper()} | "
            f"Camera: {camera_id} | Event: {event_id or 'N/A'} | Notes: {notes}\n"
        )

        with self.lock:
            try:
                with open(self.audit_log_path, "a", encoding="utf-8") as f:
                    f.write(audit_line)
            except Exception as e:
                logger.error("Failed to write audit log: %s", e)

            self.memory_logs.append(audit_item)
            if len(self.memory_logs) > self.max_memory_entries:
                self.memory_logs.pop(0)

        return audit_item

    def query_logs(
        self,
        severity: Optional[str] = None,
        camera_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query in-memory logs with multi-factor filtering."""
        with self.lock:
            entries = list(reversed(self.memory_logs))

        filtered = []
        sev_clean = severity.strip().upper() if severity else None
        cam_clean = camera_id.strip() if camera_id else None
        kw_clean = keyword.strip().lower() if keyword else None

        for item in entries:
            # Severity filter
            if sev_clean and sev_clean != "ALL":
                item_sev = item.get("severity", "").upper()
                item_type = item.get("type", "").upper()
                if sev_clean == "AUDIT" and item_type != "OPERATOR_AUDIT":
                    continue
                elif sev_clean != "AUDIT" and item_sev != sev_clean:
                    continue

            # Camera ID filter
            if cam_clean and cam_clean != "ALL":
                if item.get("camera_id") != cam_clean:
                    continue

            # Keyword search
            if kw_clean:
                searchable_text = (
                    f"{item.get('summary', '')} {item.get('action', '')} "
                    f"{item.get('camera_name', '')} {item.get('operator_id', '')} "
                    f"{item.get('notes', '')} {item.get('chain_hash', '')}"
                ).lower()
                if kw_clean not in searchable_text:
                    continue

            filtered.append(item)

        return filtered[offset : offset + limit]

    def export_logs_text(self, max_lines: int = 500) -> str:
        """Export formatted comprehensive log summary for download or compliance export."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"URBAN SAFETY AI-SOC COMPREHENSIVE INCIDENT & AUDIT LOG EXPORT")
        lines.append(f"Export Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}")
        lines.append("=" * 80)
        lines.append("")

        with self.lock:
            recent = list(self.memory_logs[-max_lines:])

        for it in recent:
            t = it.get("timestamp", "")
            itype = it.get("type", "LOG")
            cam = it.get("camera_id", "UNKNOWN")
            act = it.get("action", "")
            sev = it.get("severity", "INFO")
            summ = it.get("summary", "")
            chain = it.get("chain_hash")
            chain_str = f" | Chain: {chain}" if chain else ""
            lines.append(f"[{t}] [{itype}] [{sev}] [{cam}] {act}: {summ}{chain_str}")

        return "\n".join(lines)
