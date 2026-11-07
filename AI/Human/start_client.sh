#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: START EDGE CAMERA CLIENT
# ==============================================================================
# Hướng dẫn sử dụng:
#   1. Chạy mặc định (kết nối về http://localhost:8000, tự động nhận diện webcam):
#      ./start_client.sh
#
#   2. Kết nối tới Server trên máy chủ qua mạng LAN / Wi-Fi:
#      ./start_client.sh --server-url http://192.168.1.15:8000 --camera-id LAPTOP_01
#
#   3. Kết nối từ xa qua Public Cloudflare Tunnel URL:
#      ./start_client.sh --server-url https://your-tunnel-domain.trycloudflare.com --camera-id LAPTOP_REMOTE
#
#   4. Chỉ định chỉ số Webcam hoặc file video test:
#      ./start_client.sh --server-url http://localhost:8000 --camera 0
#      ./start_client.sh --server-url http://localhost:8000 --camera path/to/video.mp4
#
#   5. Điều chỉnh FPS và chất lượng ảnh JPEG:
#      ./start_client.sh --server-url http://localhost:8000 --fps 15 --quality 80
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Tự động phát hiện và kích hoạt Python Virtual Environment
PYTHON_BIN="python3"
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/../.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/../.venv/bin/python"
elif [ -f "/home/test/Hackathon-Test-/.venv/bin/python" ]; then
    PYTHON_BIN="/home/test/Hackathon-Test-/.venv/bin/python"
fi

export PYTHONPATH="$SCRIPT_DIR/src:${PYTHONPATH:-}"

echo "======================================================================"
echo "📹 Khởi động Edge Camera Client"
echo "🐍 Python Interpreter: $PYTHON_BIN"
echo "📁 Working Directory:  $SCRIPT_DIR"
echo "======================================================================"

# 2. Thực thi client.py kèm theo tất cả tham số truyền vào
exec "$PYTHON_BIN" "$SCRIPT_DIR/client.py" "$@"
