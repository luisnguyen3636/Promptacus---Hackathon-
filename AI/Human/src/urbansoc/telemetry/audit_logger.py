"""SOC-Grade Behavior Audit Logger for structured JSONL and human-readable logs."""

import json
import logging
import os
from dataclasses import asdict
from typing import Optional

from urbansoc.domain.schemas import BehaviorAuditLogEntry

logger = logging.getLogger("urbansoc.telemetry.audit_logger")


class BehaviorAuditLogger:
    """SOC-grade dual audit logger for structured JSONL events and human-readable text logs."""

    def __init__(self, output_dir: str = "output", heartbeat_interval: float = 1.0) -> None:
        self.output_dir = os.path.abspath(output_dir)
        self.heartbeat_interval = heartbeat_interval

        os.makedirs(self.output_dir, exist_ok=True)
        self.jsonl_path = os.path.join(self.output_dir, "behavior_events.jsonl")
        self.text_path = os.path.join(self.output_dir, "behavior_audit.log")

        # Open files in append mode with line-buffering (buffering=1)
        self._jsonl_file = open(self.jsonl_path, mode="a", encoding="utf-8", buffering=1)
        self._text_file = open(self.text_path, mode="a", encoding="utf-8", buffering=1)

    def log_event(self, entry: BehaviorAuditLogEntry) -> None:
        """Write an audit entry to both JSONL and formatted text log, flushing immediately."""
        try:
            # 1. JSONL output
            entry_dict = asdict(entry)
            json_line = json.dumps(entry_dict, ensure_ascii=False)
            self._jsonl_file.write(json_line + "\n")
            self._jsonl_file.flush()

            # 2. Formatted human-readable audit text line
            prev_str = entry.previous_behavior if entry.previous_behavior else "INIT"
            spine_val = entry.telemetry.get("spine_angle", 0.0)
            spd_val = entry.telemetry.get("speed", 0.0)
            score_pct = int(round(entry.threat_score * 100))

            text_line = (
                f"[{entry.timestamp}] [{entry.event_type}] ID #{entry.track_id}: "
                f"{prev_str} -> {entry.current_behavior} "
                f"({entry.threat_level} {score_pct}%) | "
                f"Spine:{spine_val:.0f}° Spd:{spd_val:.2f} | "
                f"Reason: {entry.reasoning}\n"
            )
            self._text_file.write(text_line)
            self._text_file.flush()
        except Exception as e:
            logger.error("Failed to write behavior audit log entry for ID #%s: %s", entry.track_id, e, exc_info=True)

    def close(self) -> None:
        """Safely flush and close all audit file handles."""
        try:
            if hasattr(self, "_jsonl_file") and self._jsonl_file and not self._jsonl_file.closed:
                self._jsonl_file.flush()
                self._jsonl_file.close()
        except Exception as e:
            logger.warning("Error while closing JSONL audit log handle: %s", e, exc_info=True)

        try:
            if hasattr(self, "_text_file") and self._text_file and not self._text_file.closed:
                self._text_file.flush()
                self._text_file.close()
        except Exception as e:
            logger.warning("Error while closing text audit log handle: %s", e, exc_info=True)
