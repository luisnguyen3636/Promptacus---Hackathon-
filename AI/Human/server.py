#!/usr/bin/env python3
"""Dedicated Urban Safety AI-SOC Multi-Camera Inference & Webhook Server.

Khởi động Máy chủ Suy luận Trung gian cho toàn bộ mạng lưới Camera/Laptop:
    python3 server.py 8000

Tính năng:
1. Chạy đa luồng nhận video từ nhiều chiếc Laptop khác gửi về qua mạng Wi-Fi/LAN.
2. Nạp mô hình YOLOv11-Pose tập trung trên máy chủ, cách ly 100% Track ID theo từng Laptop.
3. Cung cấp Giao diện Web Dashboard thời gian thực (http://localhost:8000).
4. Tiếp nhận và kiểm chứng chữ ký băm mật mã học Forensic SHA-256 (Raw Bytes + Timestamp).
"""

import argparse
import os
import subprocess
import sys
from typing import List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Dependency check & auto venv handoff
try:
    import cv2
    import numpy as np
except ImportError:
    candidate_pythons = [
        os.path.join(current_dir, ".venv", "bin", "python"),
        os.path.join(current_dir, ".venv", "bin", "python3"),
        os.path.join(current_dir, "..", ".venv", "bin", "python"),
        "/home/test/Hackathon-Test-/.venv/bin/python",
    ]
    re_exec_done = False
    for candidate in candidate_pythons:
        if os.path.exists(candidate) and os.path.abspath(candidate) != os.path.abspath(sys.executable):
            try:
                ret = subprocess.run(
                    [candidate, "-c", "import cv2, numpy"],
                    capture_output=True,
                )
                if ret.returncode == 0:
                    os.execv(candidate, [candidate] + sys.argv)
                    re_exec_done = True
                    break
            except Exception:
                pass

    if not re_exec_done:
        print(
            "LỖI: Chưa cài đặt thư viện 'cv2' hoặc 'numpy'.\n"
            "Vui lòng cài đặt:\n"
            "    pip install opencv-python numpy\n",
            file=sys.stderr,
        )
        sys.exit(1)

# 2. Ensure src/ package is accessible
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from urbansoc.config import HARDCODED_MODEL_URL
from urbansoc.server.inference_server import InferenceServer

try:
    from alert_server import AlertServer
except ImportError:
    AlertServer = None


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Urban Safety AI-SOC: Multi-Camera Intermediate Inference Server",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "port",
        type=int,
        nargs="?",
        default=8000,
        help="Server listening port (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="yolo/yolo11n-pose.pt",
        help="Path to YOLO11-Pose weights (default: yolo/yolo11n-pose.pt)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Compute device: 'cpu', 'cuda', or auto-detect (default: None)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save audit logs, evidence, and webhooks (default: output)",
    )
    parser.add_argument(
        "--url",
        "--webhook-forward-url",
        "--webhook-url",
        dest="webhook_forward_url",
        type=str,
        default="auto",
        help=f"Target endpoint to automatically POST all alerts and metadata (default: 'auto' routes to {HARDCODED_MODEL_URL})",
    )
    parser.add_argument(
        "--cooldown",
        "--webhook-cooldown",
        dest="webhook_cooldown",
        type=float,
        default=0.5,
        help="Cooldown between webhook event posts in seconds (default: 0.5s to ensure >= 30 req/30s capability)",
    )
    parser.add_argument(
        "--max-rpm",
        type=int,
        default=120,
        help="Max webhook requests per minute (default: 120)",
    )
    parser.add_argument(
        "--tunnel",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="DEPRECATED: public tunnel is now created by the camera client only (default: False)",
    )
    parser.add_argument(
        "--always-vlm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Always analyze every incoming camera request with NVIDIA VLM without batching (default: False)",
    )
    parser.add_argument(
        "--mock-vlm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use master local reasoning engine for VLM instead of external WAN API (default: False)",
    )
    parser.add_argument(
        "--batch",
        "--batch-ai",
        dest="batch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Batch 20-30 detects before sending to AI and dispatching webhook (default: True)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Number of detects to batch (range 20-30) before AI analysis (default: 25)",
    )
    return parser.parse_args(args)


def main() -> int:
    args = parse_args()
    webhook_url = args.webhook_forward_url
    if webhook_url == "auto":
        webhook_url = HARDCODED_MODEL_URL
    elif webhook_url and webhook_url.lower() in ("none", "disabled", "false", "off"):
        webhook_url = None

    if args.tunnel:
        print(
            "⚠️  Cờ --tunnel của server đã bị tắt: tunnel công khai chỉ do CAMERA CLIENT tạo.\n"
            "    Hãy chạy: ./start.sh client   (client sẽ tự tạo URL HLS để stream video)"
        )

    server = InferenceServer(
        host=args.host,
        port=args.port,
        model_weights=args.weights,
        device=args.device,
        output_dir=args.output_dir,
        webhook_url=webhook_url,
        webhook_cooldown=args.webhook_cooldown,
        max_requests_per_minute=args.max_rpm,
        # Tunnel công khai chỉ do camera client quản lý -> server luôn tắt tunnel
        enable_tunnel=False,
        always_vlm=bool(args.always_vlm),
        mock_vlm=bool(args.mock_vlm),
        enable_batching=bool(args.batch),
        batch_size=args.batch_size,
    )
    server.start(blocking=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
