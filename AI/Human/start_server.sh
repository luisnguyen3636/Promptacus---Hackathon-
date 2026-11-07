#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: START CENTRAL CAMERA & NVIDIA VLM INFERENCE SERVER
# ==============================================================================
# Hướng dẫn sử dụng:
#   1. Chạy mặc định (Port 8000, tự động đọc .env, kích hoạt Cloudflare Tunnel):
#      ./start_server.sh
#
#   2. Chạy với Port tùy chỉnh:
#      ./start_server.sh 8080
#
#   3. Chạy không dùng Cloudflare Tunnel (chỉ LAN local):
#      ./start_server.sh 8000 --no-tunnel
#
#   4. Chạy với device CPU/CUDA cụ thể:
#      ./start_server.sh 8000 --device cuda
#
#   5. Chạy kết nối sang Test Receiver Server (Port 9000):
#      ./start_server.sh 8000 --webhook-forward-url http://127.0.0.1:9000/api/v1/test/receive
#
# Cấu hình API Key NVIDIA VLM:
#   - Đặt NVIDIA_API_KEY=nvapi-... vào file .env trong thư mục hiện tại.
#   - Model mặc định: meta/llama-3.2-11b-vision-instruct (tùy chỉnh qua NVIDIA_MODEL trong .env)
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
echo "🚀 Khởi động Urban Safety Central Inference & NVIDIA VLM Server"
echo "🐍 Python Interpreter: $PYTHON_BIN"
echo "📁 Working Directory:  $SCRIPT_DIR"
echo "======================================================================"

# 2. Thực thi server.py kèm theo tất cả tham số truyền vào
exec "$PYTHON_BIN" "$SCRIPT_DIR/server.py" "$@"
