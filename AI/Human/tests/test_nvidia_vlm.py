"""Unit and integration tests for NVIDIA Vision-Language Model (VLM) client and server endpoints."""

import base64
import json
import os
import tempfile
import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from urbansoc.ai.nvidia_vlm import NvidiaVisionClient, load_env_file
from urbansoc.server.inference_server import InferenceServer


def test_load_env_file() -> None:
    """Test custom .env parser with comments, quotes, and empty lines."""
    with tempfile.NamedTemporaryFile("w+", suffix=".env", delete=False) as tf:
        tf.write("""
# This is a comment
NVIDIA_API_KEY=nvapi-test-key-12345
NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL='meta/llama-3.2-11b-vision-instruct'
EMPTY_VAL=
# Another comment
EXTRA_WHITESPACE = padded_value
""")
        tf_path = tf.name

    try:
        env = load_env_file(tf_path)
        assert env.get("NVIDIA_API_KEY") == "nvapi-test-key-12345"
        assert env.get("NVIDIA_BASE_URL") == "https://integrate.api.nvidia.com/v1"
        assert env.get("NVIDIA_MODEL") == "meta/llama-3.2-11b-vision-instruct"
        assert env.get("EXTRA_WHITESPACE") == "padded_value"
        assert env.get("EMPTY_VAL") == ""
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_nvidia_client_schema_and_metadata() -> None:
    """Test that NvidiaVisionClient produces strict schema output with rich metadata."""
    client = NvidiaVisionClient(api_key="")  # Forces mock fallback
    assert client.api_key == ""
    assert not client.is_configured

    # Dummy test image (e.g. 100x100 blue canvas)
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_frame[:, :] = (255, 0, 0)

    result = client.analyze_frame(
        frame=dummy_frame,
        camera_id="TEST_CAM_01",
        location={"address": "Khu phố 1, Quận 1", "latitude": 10.77, "longitude": 106.70},
        context_notes="Test frame analysis",
    )

    # 1. Core user-specified fields
    assert "severity" in result
    assert result["severity"] in ["low", "medium", "high", "critical"]
    assert "timestamp" in result
    assert isinstance(result["timestamp"], (str, float, int))

    # 2. Rich extended metadata fields
    assert "action_type" in result
    assert "threat_score" in result
    assert 0.0 <= result["threat_score"] <= 1.0
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert "is_urgent" in result
    assert isinstance(result["is_urgent"], bool)
    assert "actors" in result
    assert isinstance(result["actors"], list)
    assert "visual_cues" in result
    assert isinstance(result["visual_cues"], (dict, list))
    assert "recommended_action" in result
    assert "description" in result
    assert "reasoning" in result
    assert "camera_id" in result
    assert result["camera_id"] == "TEST_CAM_01"
    assert "location" in result
    assert result["location"]["address"] == "Khu phố 1, Quận 1"


def test_nvidia_client_sanitization_robustness() -> None:
    """Test sanitization handles invalid model outputs gracefully without crashing."""
    client = NvidiaVisionClient(api_key="mock_key")

    # Incomplete dictionary missing required keys
    raw_bad_data = {
        "severity": "INVALID_LEVEL",
        "threat_score": "not_a_number",
        "actors": "should_be_a_list",
    }

    sanitized = client._validate_and_sanitize_result(
        data=raw_bad_data,
        camera_id="ROBUST_CAM",
        location={"address": "Test"},
    )

    assert sanitized["severity"] == "low"  # Invalid level falls back to low
    assert sanitized["threat_score"] == 0.0
    assert isinstance(sanitized["actors"], list)
    assert "timestamp" in sanitized
    assert sanitized["camera_id"] == "ROBUST_CAM"


def test_server_nvidia_analyze_endpoint(tmp_path: Any) -> None:
    """Integration test verifying POST /api/v1/analyze/nvidia handles base64 frames."""
    import requests

    output_dir = str(tmp_path / "server_test_out")
    os.makedirs(output_dir, exist_ok=True)

    server = InferenceServer(
        host="127.0.0.1",
        port=8089,
        output_dir=output_dir,
        enable_tunnel=False,
        webhook_url=None,
    )
    server.start(blocking=False)
    time.sleep(0.3)

    try:
        # Create small test image
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        _, enc = cv2.imencode(".jpg", img)
        b64_str = base64.b64encode(enc.tobytes()).decode("utf-8")

        # 1. Test GET / returns pure JSON status (dashboard removed)
        resp_root = requests.get("http://127.0.0.1:8089/")
        assert resp_root.status_code == 200
        data_root = resp_root.json()
        assert data_root["status"] == "online"
        assert "endpoints" in data_root
        assert "analyze_nvidia_vlm" in data_root["endpoints"]
        assert data_root["endpoints"]["analyze_nvidia_vlm"] == "POST /api/v1/analyze/nvidia"

        # 2. Test POST /api/v1/analyze/nvidia
        payload = {
            "camera_id": "BENCHMARK_CAM_01",
            "frame_base64": b64_str,
            "location": {"address": "Cổng Bắc", "latitude": 10.78, "longitude": 106.69},
            "context_notes": "Unit test automated ingestion",
        }
        resp = requests.post(
            "http://127.0.0.1:8089/api/v1/analyze/nvidia",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5.0,
        )
        assert resp.status_code == 200
        analysis = resp.json()
        assert analysis["status"] == "success"
        res = analysis["result"]
        assert "severity" in res
        assert res["severity"] in ["low", "medium", "high", "critical"]
        assert "timestamp" in res
        assert "actors" in res
        assert "action_type" in res
        assert res["camera_id"] == "BENCHMARK_CAM_01"

    finally:
        server.stop()
