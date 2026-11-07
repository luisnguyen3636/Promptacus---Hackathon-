"""Unit tests for EvidenceClipRecorder pre-roll and post-roll video extraction."""

import json
import os

import numpy as np

from urbansoc.io.evidence import EvidenceClipRecorder


def test_evidence_clip_recording_lifecycle(tmp_path):
    fps = 20.0
    recorder = EvidenceClipRecorder(
        output_dir=str(tmp_path),
        fps=fps,
        frame_size=(320, 240),
        pre_roll_seconds=1.0,  # 20 frames
        post_roll_seconds=1.0, # 20 frames
    )

    dummy_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Phase 1: 15 frames with no human (accumulates in pre-roll buffer)
    for i in range(15):
        saved = recorder.update(dummy_frame, is_event_active=False)
        assert saved is None
    assert len(recorder.pre_roll_buffer) == 15
    assert not recorder.is_recording

    # Phase 2: 25 frames with human present (triggers recording and flushes pre-roll)
    for i in range(25):
        saved = recorder.update(dummy_frame, is_event_active=True)
        assert saved is None
    assert recorder.is_recording
    # Total recorded frames: 15 (pre-roll) + 25 (active) = 40 frames

    # Phase 3: 20 frames without human (post-roll cooldown)
    finalized_clip = None
    for i in range(20):
        saved = recorder.update(dummy_frame, is_event_active=False)
        if saved:
            finalized_clip = saved
            break

    assert finalized_clip is not None
    assert os.path.exists(finalized_clip)
    assert os.path.getsize(finalized_clip) > 0
    assert not recorder.is_recording

    # Verify detection_events.jsonl
    events_jsonl = os.path.join(tmp_path, "detection_events.jsonl")
    assert os.path.exists(events_jsonl)

    with open(events_jsonl, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 1
        record = json.loads(lines[0])

    expected_keys = [
        "event_id",
        "type",
        "start_time",
        "end_time",
        "duration_seconds",
        "frame_count",
        "output_file",
    ]
    for key in expected_keys:
        assert key in record

    recorder.release()
