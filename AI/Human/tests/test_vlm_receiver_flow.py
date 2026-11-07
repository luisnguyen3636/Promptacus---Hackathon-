"""Integration test for Always-On VLM Analysis and Test Receiver Server workflow."""

import base64
import json
import os
import sys
import threading
import time
from typing import Any, Dict

import cv2
import numpy as np
import pytest
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from test_receiver_server import TestReceiverHandler, ThreadedReceiverServer
from urbansoc.server.inference_server import InferenceServer


def test_always_vlm_and_receiver_dispatch(tmp_path: Any) -> None:
    """End-to-End test: Camera POST -> AI Server (Always-VLM) -> Test Receiver Server."""
    receiver_port = 9095
    ai_server_port = 8095

    output_dir = str(tmp_path / "soc_out")
    rec_output_dir = str(tmp_path / "receiver_out")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(rec_output_dir, exist_ok=True)

    # 1. Start Test Receiver Server
    TestReceiverHandler.received_events = []
    TestReceiverHandler.output_dir = rec_output_dir
    receiver_httpd = ThreadedReceiverServer(("127.0.0.1", receiver_port), TestReceiverHandler)
    receiver_thread = threading.Thread(target=receiver_httpd.serve_forever, daemon=True)
    receiver_thread.start()

    # 2. Start Central AI Server with always_vlm=True and webhook pointing to Test Receiver
    ai_server = InferenceServer(
        host="127.0.0.1",
        port=ai_server_port,
        output_dir=output_dir,
        enable_tunnel=False,
        webhook_url=f"http://127.0.0.1:{receiver_port}/api/v1/test/receive",
        always_vlm=True,
    )
    ai_server.start(blocking=False)
    time.sleep(0.4)

    try:
        # 3. Create dummy test frame (e.g. 64x64)
        dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
        dummy_frame[:, :] = (0, 120, 255)
        _, encoded = cv2.imencode(".jpg", dummy_frame)
        raw_jpeg = encoded.tobytes()

        # 4. Camera Client sends frame to /api/v1/ingest/frame
        headers = {
            "Content-Type": "image/jpeg",
            "X-Camera-ID": "TEST_CAMERA_E2E",
            "X-Camera-Name": "Camera East Gate",
            "X-Timestamp-Ms": str(int(time.time() * 1000)),
        }
        resp = requests.post(
            f"http://127.0.0.1:{ai_server_port}/api/v1/ingest/frame",
            data=raw_jpeg,
            headers=headers,
            timeout=10.0,
        )

        assert resp.status_code == 200
        data = resp.json()

        # Verify AI output contains strict VLM metadata
        assert "severity" in data
        assert data["severity"] in ["low", "medium", "high", "critical"]
        assert "timestamp" in data
        assert "action_type" in data
        assert "threat_score" in data
        assert "confidence" in data
        assert "actors" in data
        assert isinstance(data["actors"], list)
        assert "visual_cues" in data
        assert "nvidia_vlm_analysis" in data

        # 5. Verify Test Receiver Server received metadata payload
        time.sleep(1.0)  # Wait for non-blocking webhook queue dispatch
        resp_events = requests.get(f"http://127.0.0.1:{receiver_port}/events")
        assert resp_events.status_code == 200
        events_data = resp_events.json()
        assert events_data["count"] >= 1

        last_event = events_data["events"][-1]
        assert "severity" in last_event or "threat_level" in last_event
        assert "action_type" in last_event or "primary_action" in last_event

    finally:
        ai_server.stop()
        receiver_httpd.shutdown()
        receiver_httpd.server_close()
