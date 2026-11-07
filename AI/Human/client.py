#!/usr/bin/env python3
"""Urban Safety AI-SOC: Standalone Edge Camera Client.

Chạy trực tiếp trên bất kỳ Laptop/PC nào để kết nối Webcam và truyền hình ảnh
về máy chủ suy luận AI trung gian:
    python3 client.py --server-url http://<IP_SERVER>:8000 --camera 0 --camera-id LAPTOP_01

Yêu cầu môi trường phía client: Cực kỳ nhẹ nhàng (Zero AI / Zero GPU)!
Chỉ cần: opencv-python, requests.
"""

import argparse
import os
import subprocess
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Dependency check & auto venv handoff
try:
    import cv2
    import requests
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
                    [candidate, "-c", "import cv2, requests"],
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
            "LỖI: Chưa cài đặt thư viện 'cv2' hoặc 'requests'.\n"
            "Vui lòng cài đặt:\n"
            "    pip install opencv-python requests\n",
            file=sys.stderr,
        )
        sys.exit(1)

# 2. Ensure src/ package is accessible
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from urbansoc.client.edge_client import EdgeCameraClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Urban Safety AI-SOC: Edge Laptop Camera Client",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://localhost:8000",
        help="Intermediate AI Inference Server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--camera",
        type=str,
        default="auto",
        help="Webcam device index (default: auto - probes and selects physical camera)",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default=None,
        help="Unique Camera ID (default: auto - detected from machine hostname)",
    )
    parser.add_argument(
        "--camera-name",
        type=str,
        default=None,
        help="Descriptive name (default: auto - detected from username & hostname)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=15.0,
        help="Target streaming FPS (default: 15.0)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="JPEG compression quality 1-100 (default: 80)",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=10.776889,
        help="Camera GPS latitude (default: 10.776889)",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=106.700806,
        help="Camera GPS longitude (default: 106.700806)",
    )
    parser.add_argument(
        "--address",
        type=str,
        default="Laptop Client Zone",
        help="Physical installation address (default: Laptop Client Zone)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run without local GUI preview window (default: False)",
    )
    parser.add_argument(
        "--test-action",
        type=str,
        default=None,
        choices=["WEAPON_THREAT", "FALLEN", "HANDS_UP", "CROUCHING", "RUNNING", "FIGHTING", "NORMAL"],
        help="Simulate a specific human behavior action for test verification",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Maximum frames to stream before exiting (useful for testing)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP POST stream timeout in seconds (default: 30.0)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cam_index = int(args.camera) if args.camera.isdigit() else args.camera

    client = EdgeCameraClient(
        server_url=args.server_url,
        camera_id=args.camera_id,
        camera_name=args.camera_name,
        camera_index=cam_index,
        fps=args.fps,
        quality=args.quality,
        lat=args.lat,
        lon=args.lon,
        address=args.address,
        headless=args.headless,
        test_action=args.test_action,
        timeout=args.timeout,
    )

    print("=" * 70)
    print("URBAN SAFETY AI-SOC: EDGE LAPTOP CAMERA CLIENT")
    print("=" * 70)
    print(f"• Server URL:    {client.server_url}")
    print(f"• Camera ID:     {client.camera_id} ({client.camera_name})")
    print(f"• Device Index:  {client.camera_index}")
    print(f"• Target FPS:    {client.fps} (JPEG Quality: {client.quality}%)")
    print(f"• GPS Location:  Lat={client.lat}, Lon={client.lon}")
    print(f"• Mode:          {'HEADLESS (No local GUI)' if client.headless else 'CAMERA WINDOW (Interactive HUD - [q] to exit, [s] to snapshot)'}")
    if client.test_action:
        print(f"• Sim Action:    {client.test_action}")
    print("=" * 70)

    client.stream_loop(max_frames=args.max_frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())
