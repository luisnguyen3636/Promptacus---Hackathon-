"""Unit tests for BehaviorAuditLogger verifying JSONL structure and text format."""

import json
import os

from urbansoc.domain.schemas import BehaviorAuditLogEntry
from urbansoc.telemetry.audit_logger import BehaviorAuditLogger


def test_audit_logger_write_and_flush(tmp_path):
    logger = BehaviorAuditLogger(output_dir=str(tmp_path))

    entry = BehaviorAuditLogEntry(
        event_id="EVT_20261107_120000_1",
        timestamp="2026-11-07 12:00:00.123",
        frame_index=15,
        track_id=1,
        event_type="CRITICAL_ALERT",
        previous_behavior="NORMAL",
        current_behavior="FALLEN",
        threat_level="CRITICAL",
        threat_score=0.98,
        telemetry={"spine_angle": 75.0, "aspect_ratio": 0.45, "speed": 0.0, "wrist_velocity": 0.0},
        reasoning="Torso angle 75° horizontal",
        dwell_time_seconds=1.2,
    )

    logger.log_event(entry)
    logger.close()

    jsonl_path = os.path.join(tmp_path, "behavior_events.jsonl")
    text_path = os.path.join(tmp_path, "behavior_audit.log")

    assert os.path.exists(jsonl_path)
    assert os.path.exists(text_path)

    # 1. Verify JSONL line
    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])

    expected_keys = [
        "event_id",
        "timestamp",
        "frame_index",
        "track_id",
        "event_type",
        "previous_behavior",
        "current_behavior",
        "threat_level",
        "threat_score",
        "telemetry",
        "reasoning",
        "dwell_time_seconds",
    ]
    for key in expected_keys:
        assert key in data, f"Key '{key}' missing from JSONL entry"

    assert data["track_id"] == 1
    assert data["current_behavior"] == "FALLEN"
    assert data["threat_level"] == "CRITICAL"
    assert data["threat_score"] == 0.98

    # 2. Verify text log formatting
    with open(text_path, "r", encoding="utf-8") as f:
        log_text = f.read()

    assert "[2026-11-07 12:00:00.123] [CRITICAL_ALERT] ID #1: NORMAL -> FALLEN (CRITICAL 98%)" in log_text
    assert "Reason: Torso angle 75° horizontal" in log_text
