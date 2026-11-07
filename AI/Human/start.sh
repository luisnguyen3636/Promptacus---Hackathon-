#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: ALL-IN-ONE MASTER STARTUP SCRIPT
# ==============================================================================
# Khởi chạy toàn bộ hệ sinh thái giám sát an ninh AI-SOC chỉ bằng 1 lệnh:
#
#   1. Khởi động TẤT CẢ (Server + Cloudflare Tunnel + Camera Client):
#      ./start.sh
#
#   2. Khởi động riêng Máy chủ Suy luận Trung gian (Server):
#      ./start.sh server
#      ./start.sh server 8080
#
#   3. Khởi động riêng Camera Client:
#      ./start.sh client
#      ./start.sh client --camera 0 --camera-id LAPTOP_01
#      ./start.sh client --server-url http://192.168.1.15:8000
#
#   4. Chạy bộ kiểm thử tự động (Test Suite):
#      ./start.sh test
#      ./start.sh test unit
#      ./start.sh test live
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ------------------------------------------------------------------------------
# 1. Phát hiện môi trường Python Virtual Environment
# ------------------------------------------------------------------------------
PYTHON_BIN=""
PYTEST_BIN=""
if [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
    PYTEST_BIN="${SCRIPT_DIR}/.venv/bin/pytest"
elif [[ -x "/home/test/Hackathon-Test-/.venv/bin/python" ]]; then
    PYTHON_BIN="/home/test/Hackathon-Test-/.venv/bin/python"
    PYTEST_BIN="/home/test/Hackathon-Test-/.venv/bin/pytest"
elif [[ -x "${SCRIPT_DIR}/../.venv/bin/python" ]]; then
    PYTHON_BIN="${SCRIPT_DIR}/../.venv/bin/python"
    PYTEST_BIN="${SCRIPT_DIR}/../.venv/bin/pytest"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
    PYTEST_BIN="$(command -v pytest || echo "pytest")"
else
    echo "❌ Lỗi: Không tìm thấy Python 3 executable trong hệ thống!" >&2
    exit 1
fi

export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

# ------------------------------------------------------------------------------
# 2. Tiện ích kiểm tra & tự động tải Cloudflared
# ------------------------------------------------------------------------------
ensure_cloudflared() {
    if command -v cloudflared &>/dev/null; then
        echo "$(command -v cloudflared)"
        return 0
    fi
    local bin_dir="${SCRIPT_DIR}/bin"
    local cf_bin="${bin_dir}/cloudflared"
    if [[ -x "${cf_bin}" ]]; then
        echo "${cf_bin}"
        return 0
    fi

    mkdir -p "${bin_dir}"
    echo "⬇️ Đang tải bản binary Cloudflare Tunnel (cloudflared)..." >&2
    local dl_url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    if command -v curl &>/dev/null; then
        curl -fsSL -o "${cf_bin}" "${dl_url}"
    elif command -v wget &>/dev/null; then
        wget -qO "${cf_bin}" "${dl_url}"
    else
        echo "❌ Cần curl hoặc wget để tải cloudflared." >&2
        return 1
    fi
    chmod +x "${cf_bin}"
    echo "${cf_bin}"
}

# ------------------------------------------------------------------------------
# 3. Phân luồng điều phối theo tham số đầu vào
# ------------------------------------------------------------------------------
ACTION="${1:-all}"

case "${ACTION}" in
    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 1: Khởi động riêng Central Server
    # --------------------------------------------------------------------------
    server)
        shift
        echo "======================================================================"
        echo "🚀 Khởi động Urban Safety Central Inference Server"
        echo "🐍 Python: $PYTHON_BIN"
        echo "📁 Thư mục: $SCRIPT_DIR"
        echo "======================================================================"
        exec "$PYTHON_BIN" "$SCRIPT_DIR/server.py" "$@"
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 2: Khởi động riêng Camera Client
    # --------------------------------------------------------------------------
    client)
        shift
        echo "======================================================================"
        echo "📹 Khởi động Edge Camera Client"
        echo "🐍 Python: $PYTHON_BIN"
        echo "📁 Thư mục: $SCRIPT_DIR"
        echo "======================================================================"
        exec "$PYTHON_BIN" "$SCRIPT_DIR/client.py" "$@"
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 3: Chạy bộ kiểm thử tự động
    # --------------------------------------------------------------------------
    test)
        shift
        TEST_SUB="${1:-unit}"
        echo "======================================================================"
        echo "🛡️ URBAN SAFETY AI-SOC: KIỂM THỬ TỰ ĐỘNG"
        echo "======================================================================"
        case "${TEST_SUB}" in
            unit|"")
                echo "📋 Đang chạy bộ kiểm thử toàn diện..."
                "$PYTEST_BIN" tests/test_rate_limit_and_rules.py tests/test_mjpeg_stream.py tests/test_multicam.py tests/test_soc_dashboard_logging.py -v
                echo "✅ Toàn bộ bài kiểm thử đã VƯỢT QUA thành công 100%!"
                ;;
            live)
                echo "🚀 Khởi chạy hệ thống kiểm tra trực tiếp (Live Camera)..."
                "$PYTHON_BIN" run_system.py
                ;;
            test-weapon)
                "$PYTHON_BIN" run_system.py --test-action WEAPON_THREAT
                ;;
            test-fallen)
                "$PYTHON_BIN" run_system.py --test-action FALLEN
                ;;
            test-knife)
                "$PYTHON_BIN" run_system.py --test-action KNIFE_THREAT
                ;;
            all)
                "$PYTEST_BIN" tests/ -v
                ;;
            *)
                "$PYTEST_BIN" "$@"
                ;;
        esac
        exit 0
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 4: Khởi động TẤT CẢ (Default / all)
    # Khởi chạy Server + Cloudflare Tunnel + Camera Client đồng thời
    # --------------------------------------------------------------------------
    all|*)
        if [[ "${ACTION}" == "all" ]]; then
            shift
        fi

        SERVER_PORT="${PORT:-8000}"
        SERVER_URL="http://127.0.0.1:${SERVER_PORT}"
        SERVER_PID=""
        TUNNEL_PID=""
        CLIENT_PID=""

        cleanup() {
            echo ""
            echo "🛑 Đang dọn dẹp và dừng các dịch vụ AI-SOC..."
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

        echo "======================================================================"
        echo "🌐 URBAN SAFETY AI-SOC: ALL-IN-ONE AUTOMATED RUNNER"
        echo "======================================================================"
        echo "🐍 Python Interpreter: ${PYTHON_BIN}"
        echo "📁 Working Directory:  ${SCRIPT_DIR}"
        echo "🔌 Cổng Server:        ${SERVER_PORT}"
        echo "======================================================================"

        # 4.1 Khởi động Central Server nếu chưa chạy
        if curl -s -f -m 1 "${SERVER_URL}/api/v1/cameras" &>/dev/null; then
            echo "✅ Central Inference Server đã chạy sẵn trên cổng ${SERVER_PORT}."
        else
            echo "🚀 [1/3] Đang khởi động Central Inference Server trên cổng ${SERVER_PORT}..."
            "${PYTHON_BIN}" server.py "${SERVER_PORT}" > /tmp/soc_server.log 2>&1 &
            SERVER_PID=$!

            # Đợi server sẵn sàng
            WAIT_COUNT=0
            until curl -s -f -m 1 "${SERVER_URL}/api/v1/cameras" &>/dev/null; do
                sleep 0.4
                WAIT_COUNT=$((WAIT_COUNT + 1))
                if [[ ${WAIT_COUNT} -gt 35 ]]; then
                    echo "❌ Lỗi: Server không phản hồi sau 15 giây. Xem log: /tmp/soc_server.log"
                    exit 1
                fi
            done
            echo "✅ Central Inference Server đã sẵn sàng."
        fi

        # 4.2 Khởi động Cloudflare Tunnel
        CLOUDFLARED_BIN="$(ensure_cloudflared || true)"
        PUBLIC_URL=""
        if [[ -n "${CLOUDFLARED_BIN}" && -x "${CLOUDFLARED_BIN}" ]]; then
            echo "🌐 [2/3] Đang khởi tạo Cloudflare Public Tunnel..."
            TUNNEL_LOG="/tmp/soc_tunnel.log"
            rm -f "${TUNNEL_LOG}"
            "${CLOUDFLARED_BIN}" tunnel --url "${SERVER_URL}" --no-autoupdate > "${TUNNEL_LOG}" 2>&1 &
            TUNNEL_PID=$!

            for i in {1..25}; do
                if [[ -f "${TUNNEL_LOG}" ]]; then
                    FOUND_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "${TUNNEL_LOG}" | head -n 1 || true)
                    if [[ -n "${FOUND_URL}" ]]; then
                        PUBLIC_URL="${FOUND_URL}"
                        break
                    fi
                fi
                sleep 0.4
            done
        fi

        # 4.3 In thông tin điều khiển hệ thống
        LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")"
        echo "======================================================================"
        echo "✨ HỆ THỐNG URBAN SAFETY AI-SOC ĐÃ KHỞI CHẠY THÀNH CÔNG!"
        echo "======================================================================"
        echo "• 📊 SOC Web Dashboard:   ${SERVER_URL}/dashboard"
        echo "• 📹 Local MJPEG Stream:  ${SERVER_URL}/stream.mjpg"
        echo "• 📡 LAN Access URL:      http://${LOCAL_IP}:${SERVER_PORT}/dashboard"
        if [[ -n "${PUBLIC_URL}" ]]; then
            echo "• 🌍 Public Tunnel URL:   ${PUBLIC_URL}/dashboard"
            echo "• 🌍 Public Video Stream: ${PUBLIC_URL}/stream.mjpg"
        fi
        echo "======================================================================"

        # 4.4 Khởi động Camera Client
        echo "📹 [3/3] Đang kết nối Camera Client..."
        echo "💡 Mẹo: Nhấn phím 'q' trên cửa sổ camera hoặc Ctrl+C trong terminal để dừng."
        echo ""

        exec "${PYTHON_BIN}" client.py --server-url "${SERVER_URL}" "$@"
        ;;
esac
