#!/usr/bin/env python3
"""All-in-One Automated System Runner for Urban Safety AI-SOC.

Khởi động đồng thời cả Central Server và Camera Client chỉ với 1 lệnh duy nhất:
    python3 run_system.py

Các tùy chọn:
    python3 run_system.py --headless                  # Chạy client không mở cửa sổ GUI
    python3 run_system.py --test-action WEAPON_THREAT # Giả lập thử nghiệm hành vi vũ khí
    python3 run_system.py --port 8000                 # Đổi cổng lắng nghe của server
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request


def find_python_executable() -> str:
    """Find the most suitable Python interpreter with venv dependencies."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, ".venv", "bin", "python"),
        os.path.join(current_dir, ".venv", "bin", "python3"),
        "/home/test/Hackathon-Test-/.venv/bin/python",
        sys.executable,
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return sys.executable


def wait_for_server(url: str, timeout_seconds: float = 8.0) -> bool:
    """Poll health endpoint until server responds or timeout occurs."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SOC-Runner"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Urban Safety AI-SOC: All-in-One Central Server & Client Launcher",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--camera", type=str, default="auto", help="Webcam device index or video file (default: auto)")
    parser.add_argument("--camera-id", type=str, default=None, help="Camera ID (default: auto from hostname)")
    parser.add_argument("--camera-name", type=str, default=None, help="Camera Name (default: auto)")
    parser.add_argument("--headless", action="store_true", help="Run client in headless mode (no camera GUI)")
    parser.add_argument("--test-action", type=str, default=None, help="Simulate a dangerous action for quick testing")
    parser.add_argument("--max-frames", type=int, default=None, help="Stop client after N frames (useful for tests)")
    args = parser.parse_args()

    python_bin = find_python_executable()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(root_dir, "server.py")
    client_script = os.path.join(root_dir, "client.py")

    print("=" * 72)
    print("🌐 URBAN SAFETY AI-SOC: ALL-IN-ONE AUTOMATED RUNNER")
    print("=" * 72)
    print(f"• Python Environment: {python_bin}")
    print(f"• Server Listening:   http://0.0.0.0:{args.port}")
    print(f"• Client Camera:      {args.camera} ({'HEADLESS' if args.headless else 'INTERACTIVE GUI HUD'})")
    if args.test_action:
        print(f"• Simulated Action:   {args.test_action}")
    print("=" * 72)

    # 1. Start Server Process
    server_cmd = [python_bin, server_script, str(args.port)]
    print("\n[1/2] Đang khởi động AI-SOC Central Inference Server...", flush=True)
    server_proc = subprocess.Popen(
        server_cmd,
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Helper thread or non-blocking check
    server_health_url = f"http://127.0.0.1:{args.port}/api/v1/cameras"
    server_ready = wait_for_server(server_health_url, timeout_seconds=10.0)

    if not server_ready:
        print("❌ LỖI: Server không thể khởi động trong 10 giây.", file=sys.stderr)
        server_proc.terminate()
        return 1

    print(f"✅ Server đã sẵn sàng tại http://127.0.0.1:{args.port}!", flush=True)

    # 2. Build Client Command
    client_cmd = [
        python_bin,
        client_script,
        "--server-url", f"http://127.0.0.1:{args.port}",
        "--camera", str(args.camera),
    ]
    if args.camera_id:
        client_cmd.extend(["--camera-id", args.camera_id])
    if args.camera_name:
        client_cmd.extend(["--camera-name", args.camera_name])
    if args.headless:
        client_cmd.append("--headless")
    if args.test_action:
        client_cmd.extend(["--test-action", args.test_action])
    if args.max_frames:
        client_cmd.extend(["--max-frames", str(args.max_frames)])

    print("\n[2/2] Đang khởi động Edge Camera Client...", flush=True)
    print("👉 Mở trình duyệt tại http://localhost:8000 để xem Multi-Camera SOC Grid.")
    print("👉 Nhấn [q] trên cửa sổ camera hoặc Ctrl+C tại đây để dừng hệ thống.\n", flush=True)

    client_proc = None
    try:
        client_env = os.environ.copy()
        if "DISPLAY" not in client_env:
            client_env["DISPLAY"] = ":0"

        client_proc = subprocess.Popen(client_cmd, cwd=root_dir, env=client_env)
        client_proc.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Nhận tín hiệu dừng từ người dùng (Ctrl+C)...")
    finally:
        print("🧹 Đang dọn dẹp và đóng tất cả tiến trình an toàn...", flush=True)
        if client_proc and client_proc.poll() is None:
            client_proc.terminate()
            try:
                client_proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                client_proc.kill()

        if server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                server_proc.kill()

        print("✅ Toàn bộ tiến trình Server & Client đã dừng sạch sẽ. Cổng mạng đã được giải phóng!\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
