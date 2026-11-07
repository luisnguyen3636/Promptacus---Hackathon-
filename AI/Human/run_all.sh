#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: ALL-IN-ONE AUTOMATION RUNNER
# Khởi chạy toàn bộ hệ thống: Central Server + Cloudflare Tunnel + Camera Client
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# 1. Detect Python Virtual Environment
PYTHON_BIN=""
if [[ -x "/home/test/Hackathon-Test-/.venv/bin/python" ]]; then
    PYTHON_BIN="/home/test/Hackathon-Test-/.venv/bin/python"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "❌ Error: Python 3 executable not found!" >&2
    exit 1
fi

# 2. Check & Setup Cloudflared
CLOUDFLARED_BIN=""
if command -v cloudflared &>/dev/null; then
    CLOUDFLARED_BIN="$(command -v cloudflared)"
elif [[ -x "${SCRIPT_DIR}/bin/cloudflared" ]]; then
    CLOUDFLARED_BIN="${SCRIPT_DIR}/bin/cloudflared"
else
    echo "⚙️ cloudflared chưa được cài đặt. Đang tự động tải về..."
    "${SCRIPT_DIR}/scripts/setup_cloudflared.sh"
    CLOUDFLARED_BIN="${SCRIPT_DIR}/bin/cloudflared"
fi

SERVER_PID=""
TUNNEL_PID=""
CLIENT_PID=""

cleanup() {
    echo ""
    echo "🛑 Đang dọn dẹp và dừng các dịch vụ..."
    if [[ -n "${CLIENT_PID}" ]] && kill -0 "${CLIENT_PID}" 2>/dev/null; then
        echo "• Dừng Camera Client (PID: ${CLIENT_PID})..."
        kill -SIGINT "${CLIENT_PID}" 2>/dev/null || true
    fi
    if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
        echo "• Dừng Cloudflare Tunnel (PID: ${TUNNEL_PID})..."
        kill -SIGTERM "${TUNNEL_PID}" 2>/dev/null || true
    fi
    if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
        echo "• Dừng Central Server (PID: ${SERVER_PID})..."
        kill -SIGINT "${SERVER_PID}" 2>/dev/null || true
    fi
    echo "✅ Hệ thống đã tắt hoàn toàn."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 3. Check / Start Central Inference Server on Port 8000
SERVER_URL="http://127.0.0.1:8000"
SERVER_LOG="/tmp/soc_server.log"

if curl -s -f -m 1 "${SERVER_URL}/api/v1/cameras" &>/dev/null; then
    echo "✅ Central Inference Server đã chạy sẵn tại port 8000."
else
    echo "🚀 Khởi động Central Inference Server trên port 8000..."
    "${PYTHON_BIN}" server.py 8000 > "${SERVER_LOG}" 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to become responsive
    WAIT_COUNT=0
    until curl -s -f -m 1 "${SERVER_URL}/api/v1/cameras" &>/dev/null; do
        sleep 0.5
        WAIT_COUNT=$((WAIT_COUNT + 1))
        if [[ ${WAIT_COUNT} -gt 30 ]]; then
            echo "❌ Lỗi: Server không phản hồi sau 15 giây. Xem log tại ${SERVER_LOG}"
            exit 1
        fi
    done
    echo "✅ Central Inference Server đã sẵn sàng."
fi

# 4. Start Cloudflare Tunnel & Extract Public URL
TUNNEL_LOG="/tmp/soc_tunnel.log"
rm -f "${TUNNEL_LOG}"

echo "🌐 Đang kết nối Cloudflare Quick Tunnel..."
"${CLOUDFLARED_BIN}" tunnel --url "${SERVER_URL}" --no-autoupdate > "${TUNNEL_LOG}" 2>&1 &
TUNNEL_PID=$!

PUBLIC_TUNNEL_URL=""
echo "⏳ Đang tạo URL công khai từ Cloudflare..."
for i in {1..30}; do
    if [[ -f "${TUNNEL_LOG}" ]]; then
        FOUND_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "${TUNNEL_LOG}" | head -n 1 || true)
        if [[ -n "${FOUND_URL}" ]]; then
            PUBLIC_TUNNEL_URL="${FOUND_URL}"
            break
        fi
    fi
    sleep 0.5
done

if [[ -z "${PUBLIC_TUNNEL_URL}" ]]; then
    echo "⚠️ Cảnh báo: Chưa lấy được URL Cloudflare trong 15s. Sẽ dùng IP LAN tạm thời."
    LOCAL_IP=$("${PYTHON_BIN}" -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")
    PUBLIC_TUNNEL_URL="http://${LOCAL_IP}:8000"
fi

# 5. Output Prominent Information Banner
echo ""
echo "============================================================================"
echo "🌍 URBAN SAFETY AI-SOC: KẾT NỐI TRUY CẬP TỪ XA ĐÃ SẴN SÀNG"
echo "============================================================================"
echo "• 🔗 Public Domain:        ${PUBLIC_TUNNEL_URL}"
echo "• 📹 Real-Time MJPEG:      ${PUBLIC_TUNNEL_URL}/api/v1/cameras/LAPTOP_01/stream"
echo "• ⚡ Quick Stream Link:    ${PUBLIC_TUNNEL_URL}/stream.mjpg"
echo "• 🖥️ Web SOC Dashboard:    ${PUBLIC_TUNNEL_URL}/dashboard"
echo "• 📡 Status API:           ${PUBLIC_TUNNEL_URL}/api/v1/cameras"
echo "----------------------------------------------------------------------------"
echo "🚀 Webhook Auto-Forward:   https://urbanstrike.tech/api/incidents"
echo "👉 Hướng dẫn xem luồng:"
echo "   1. Mở bất kỳ trình duyệt ngoài Internet / điện thoại: dán link 'Real-Time MJPEG'"
echo "   2. Xem dashboard đa camera đầy đủ: dán link 'Web SOC Dashboard'"
echo "============================================================================"
echo ""

# 6. Launch Edge Camera Client (with HUD display window)
export DISPLAY="${DISPLAY:-:0}"
echo "🎥 Đang mở cửa sổ Camera Client (HUD & Bounding Box) trên màn hình..."
echo "👉 Nhấn 'q' tại cửa sổ camera hoặc Ctrl+C tại terminal này để thoát."
echo ""

"${PYTHON_BIN}" client.py --server-url "${SERVER_URL}" --camera 0 --camera-id LAPTOP_01
