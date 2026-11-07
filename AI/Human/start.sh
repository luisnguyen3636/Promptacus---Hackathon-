#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: ALL-IN-ONE MASTER STARTUP SCRIPT
# ==============================================================================
# Khởi chạy toàn bộ hệ sinh thái giám sát an ninh AI-SOC chỉ bằng 1 lệnh:
#
#   1. Khởi động TẤT CẢ (Server + Cloudflare Tunnel + Camera Client):
#      ./start.sh
#      ./start.sh --url https://target-webhook-server.com
#
#   2. Khởi động Server kèm Cloudflare Tunnel để streaming camera ra ngoài Internet:
#      ./start.sh server --tunnel
#      ./start.sh server 8000 --tunnel
#      ./start.sh server 8000 --tunnel --url https://target-webhook-server.com
#
#   3. Khởi động riêng Cloudflare Tunnel (Forwarding cho bất kỳ cổng nào):
#      ./start.sh tunnel
#      ./start.sh tunnel 8000
#
#   4. Khởi động riêng Camera Client:
#      ./start.sh client
#      ./start.sh client --camera 0 --camera-id LAPTOP_01
#      ./start.sh client --server-url https://xxxx.trycloudflare.com
#
#   5. Chạy bộ kiểm thử tự động (Test Suite):
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
    help|--help|-h)
        echo "======================================================================"
        echo "🌐 URBAN SAFETY AI-SOC: CÁCH DÙNG START.SH"
        echo "======================================================================"
        echo "1. Khởi động TẤT CẢ (Server + Cloudflare Tunnel + Camera Client):"
        echo "   ./start.sh"
        echo "   ./start.sh --url https://target-webhook-server.com"
        echo ""
        echo "2. Khởi động Server kèm Cloudflare Tunnel để streaming camera ra ngoài Internet:"
        echo "   ./start.sh server --tunnel"
        echo "   ./start.sh server 8000 --tunnel"
        echo "   ./start.sh server 8000 --tunnel --url https://target-webhook-server.com"
        echo ""
        echo "3. Khởi động riêng Cloudflare Tunnel (Forwarding cho bất kỳ cổng nào):"
        echo "   ./start.sh tunnel"
        echo "   ./start.sh tunnel 8000"
        echo ""
        echo "4. Khởi động riêng Camera Client:"
        echo "   ./start.sh client"
        echo "   ./start.sh client --camera 0 --camera-id LAPTOP_01"
        echo "   ./start.sh client --server-url https://xxxx.trycloudflare.com"
        echo ""
        echo "5. Chạy bộ kiểm thử tự động (Test Suite):"
        echo "   ./start.sh test"
        echo "   ./start.sh test unit"
        echo "======================================================================"
        exit 0
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 1: Khởi động Central Server (Hỗ trợ cờ --tunnel để stream ra Internet)
    # --------------------------------------------------------------------------
    server)
        shift
        WANT_TUNNEL=false
        SERVER_ARGS=()
        SERVER_PORT="8000"

        while [[ $# -gt 0 ]]; do
            case "$1" in
                --tunnel|-t)
                    WANT_TUNNEL=true
                    shift
                    ;;
                [0-9]*)
                    SERVER_PORT="$1"
                    SERVER_ARGS+=("$1")
                    shift
                    ;;
                *)
                    SERVER_ARGS+=("$1")
                    shift
                    ;;
            esac
        done

        if [[ "${WANT_TUNNEL}" == "false" ]]; then
            echo "======================================================================"
            echo "🚀 Khởi động Urban Safety Central Inference Server (Cổng ${SERVER_PORT})"
            echo "🐍 Python: $PYTHON_BIN"
            echo "📁 Thư mục: $SCRIPT_DIR"
            echo "💡 Muốn stream ra ngoài Internet? Chạy: ./start.sh server --tunnel"
            echo "======================================================================"
            exec "$PYTHON_BIN" "$SCRIPT_DIR/server.py" ${SERVER_ARGS[@]+"${SERVER_ARGS[@]}"}
        fi

        # Server + Cloudflare Tunnel đồng thời
        echo "======================================================================"
        echo "🚀 Khởi động Urban Safety Server + Cloudflare Public Streaming Tunnel"
        echo "🐍 Python: $PYTHON_BIN"
        echo "🔌 Cổng Server: $SERVER_PORT"
        echo "======================================================================"

        SERVER_PID=""
        TUNNEL_PID=""

        cleanup_server_tunnel() {
            echo ""
            echo "🛑 Đang dừng Server và Cloudflare Tunnel..."
            if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
                kill -SIGTERM "${TUNNEL_PID}" 2>/dev/null || true
            fi
            if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
                kill -SIGINT "${SERVER_PID}" 2>/dev/null || true
            fi
            exit 0
        }
        trap cleanup_server_tunnel SIGINT SIGTERM EXIT

        # Khởi chạy server nền
        "$PYTHON_BIN" "$SCRIPT_DIR/server.py" ${SERVER_ARGS[@]+"${SERVER_ARGS[@]}"} &
        SERVER_PID=$!

        # Đợi server sẵn sàng
        SERVER_LOCAL_URL="http://127.0.0.1:${SERVER_PORT}"
        WAIT_COUNT=0
        until curl -s -f -m 1 "${SERVER_LOCAL_URL}/api/v1/cameras" &>/dev/null; do
            sleep 0.4
            WAIT_COUNT=$((WAIT_COUNT + 1))
            if [[ ${WAIT_COUNT} -gt 35 ]]; then
                echo "❌ Lỗi: Server không phản hồi sau 15 giây."
                exit 1
            fi
        done
        echo "✅ Central Inference Server đã sẵn sàng."

        # Khởi chạy Cloudflare Tunnel
        CLOUDFLARED_BIN="$(ensure_cloudflared || true)"
        PUBLIC_URL=""
        if [[ -n "${CLOUDFLARED_BIN}" && -x "${CLOUDFLARED_BIN}" ]]; then
            echo "🌐 Đang khởi tạo Cloudflare Public Tunnel..."
            TUNNEL_LOG="/tmp/soc_tunnel_server.log"
            rm -f "${TUNNEL_LOG}"
            "${CLOUDFLARED_BIN}" tunnel --url "${SERVER_LOCAL_URL}" --no-autoupdate > "${TUNNEL_LOG}" 2>&1 &
            TUNNEL_PID=$!

            for i in {1..30}; do
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

        echo "======================================================================"
        echo "✨ CLOUDFLARE PUBLIC TUNNEL SẴN SÀNG CHO STREAMING CAMERA:"
        echo "======================================================================"
        echo "• 📹 Public Video Stream (MJPEG):  ${PUBLIC_URL:-[Đang kết nối]}/stream.mjpg"
        echo "• 📺 Public Video Stream (HLS):    ${PUBLIC_URL:-[Đang kết nối]}/live.m3u8"
        echo "• 📸 Public Camera Snapshot:       ${PUBLIC_URL:-[Đang kết nối]}/snapshot.jpg"
        echo "• 📊 Public SOC Web Dashboard:     ${PUBLIC_URL:-[Đang kết nối]}/dashboard"
        echo "• 📡 Public Remote Ingestion POST: ${PUBLIC_URL:-[Đang kết nối]}/api/v1/frame"
        echo "======================================================================"
        if [[ -n "${PUBLIC_URL}" ]]; then
            echo "${PUBLIC_URL}" > /tmp/soc_public_url.txt
        fi

        wait "${SERVER_PID}"
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 2: Khởi động riêng Cloudflare Tunnel
    # --------------------------------------------------------------------------
    tunnel)
        shift
        TUNNEL_PORT="${1:-8000}"
        CLOUDFLARED_BIN="$(ensure_cloudflared || true)"
        if [[ -z "${CLOUDFLARED_BIN}" || ! -x "${CLOUDFLARED_BIN}" ]]; then
            echo "❌ Không thể khởi động Cloudflare Tunnel: không tìm thấy binary cloudflared." >&2
            exit 1
        fi
        echo "======================================================================"
        echo "🌐 KHỞI ĐỘNG CLOUDFLARE TUNNEL ĐỘC LẬP (FORWARD PORT ${TUNNEL_PORT})"
        echo "======================================================================"
        TUNNEL_LOG="/tmp/soc_tunnel_standalone.log"
        rm -f "${TUNNEL_LOG}"
        "${CLOUDFLARED_BIN}" tunnel --url "http://127.0.0.1:${TUNNEL_PORT}" --no-autoupdate > "${TUNNEL_LOG}" 2>&1 &
        TUNNEL_PID=$!

        cleanup_tunnel_standalone() {
            echo ""
            echo "🛑 Đang dừng Cloudflare Tunnel..."
            if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
                kill -SIGTERM "${TUNNEL_PID}" 2>/dev/null || true
            fi
            exit 0
        }
        trap cleanup_tunnel_standalone SIGINT SIGTERM EXIT

        echo "⏳ Đang kết nối mạng lưới Cloudflare Edge..."
        PUBLIC_URL=""
        for i in {1..30}; do
            if [[ -f "${TUNNEL_LOG}" ]]; then
                FOUND_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "${TUNNEL_LOG}" | head -n 1 || true)
                if [[ -n "${FOUND_URL}" ]]; then
                    PUBLIC_URL="${FOUND_URL}"
                    break
                fi
            fi
            sleep 0.4
        done

        if [[ -n "${PUBLIC_URL}" ]]; then
            echo "======================================================================"
            echo "✨ CLOUDFLARE TUNNEL ĐÃ SẴN SÀNG STREAMING CAMERA RA NGOÀI INTERNET:"
            echo "======================================================================"
            echo "• 📹 Public Video Stream (MJPEG):  ${PUBLIC_URL}/stream.mjpg"
            echo "• 📺 Public Video Stream (HLS):    ${PUBLIC_URL}/live.m3u8"
            echo "• 📸 Public Camera Snapshot:       ${PUBLIC_URL}/snapshot.jpg"
            echo "• 📊 Public SOC Web Dashboard:     ${PUBLIC_URL}/dashboard"
            echo "• 📡 Public Ingestion Endpoint:    ${PUBLIC_URL}/api/v1/frame"
            echo "======================================================================"
            echo "${PUBLIC_URL}" > /tmp/soc_public_url.txt
        else
            echo "⚠️ Chưa lấy được URL public ngay lập tức. Xem log: ${TUNNEL_LOG}"
        fi
        wait "${TUNNEL_PID}"
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

        TARGET_FORWARD_URL=""
        REMAINING_ARGS=()
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --url|--webhook-url|--webhook-forward-url)
                    TARGET_FORWARD_URL="$2"
                    shift 2
                    ;;
                *)
                    REMAINING_ARGS+=("$1")
                    shift
                    ;;
            esac
        done

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
            SERVER_CMD=("${PYTHON_BIN}" server.py "${SERVER_PORT}")
            if [[ -n "${TARGET_FORWARD_URL}" ]]; then
                SERVER_CMD+=(--url "${TARGET_FORWARD_URL}")
                echo "🎯 Cấu hình đẩy dữ liệu tự động tới Target: ${TARGET_FORWARD_URL}"
            fi
            "${SERVER_CMD[@]}" > /tmp/soc_server.log 2>&1 &
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
        echo "• 📺 Local HLS Stream:    ${SERVER_URL}/live.m3u8"
        echo "• 📡 LAN Access URL:      http://${LOCAL_IP}:${SERVER_PORT}/dashboard"
        if [[ -n "${PUBLIC_URL}" ]]; then
            echo "• 🌍 Public Tunnel Dashboard:     ${PUBLIC_URL}/dashboard"
            echo "• 🌍 Public Video Stream (MJPEG): ${PUBLIC_URL}/stream.mjpg"
            echo "• 🌍 Public Video Stream (HLS):   ${PUBLIC_URL}/live.m3u8"
            echo "• 📸 Public Camera Snapshot:      ${PUBLIC_URL}/snapshot.jpg"
            echo "• 📡 Public Frame Ingestion POST: ${PUBLIC_URL}/api/v1/frame"
            echo "${PUBLIC_URL}" > /tmp/soc_public_url.txt
        fi
        echo "======================================================================"

        # 4.4 Khởi động Camera Client
        echo "📹 [3/3] Đang kết nối Camera Client..."
        echo "💡 Mẹo: Nhấn phím 'q' trên cửa sổ camera hoặc Ctrl+C trong terminal để dừng."
        echo ""

        exec "${PYTHON_BIN}" client.py --server-url "${SERVER_URL}" ${REMAINING_ARGS[@]+"${REMAINING_ARGS[@]}"}
        ;;
esac
