#!/usr/bin/env python3
"""Urban Safety AI-SOC: Single Entrypoint.

Chỉ cần chạy:
    python main.py
hoặc:
    python3 main.py

Hệ thống sẽ tự động khởi động camera giám sát trực tiếp, nạp mô hình YOLO từ thư mục
'yolo/yolo11n-pose.pt', hiển thị giao diện HUD giám sát và các bảng điều khiển thời gian thực.
(Nếu chưa có file model trong 'yolo/', hệ thống sẽ tự động kích hoạt chế độ dự phòng an toàn).
"""

import os
import subprocess
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Dependency check & auto venv handoff
try:
    import cv2
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
                ret = subprocess.run([candidate, "-c", "import cv2"], capture_output=True)
                if ret.returncode == 0:
                    os.execv(candidate, [candidate] + sys.argv)
                    re_exec_done = True
                    break
            except Exception:
                pass

    if not re_exec_done:
        print(
            "LỖI: Chưa cài đặt thư viện 'cv2' (opencv-python) trong môi trường Python hiện tại.\n"
            "Vui lòng kích hoạt virtualenv đã có hoặc cài đặt dependencies:\n"
            "    source .venv/bin/activate\n"
            "    python main.py\n"
            "hoặc:\n"
            "    pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

# 2. Ensure src/ package is accessible
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from urbansoc.cli import main

if __name__ == "__main__":
    sys.exit(main())
