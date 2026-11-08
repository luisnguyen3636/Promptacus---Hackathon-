#!/usr/bin/env bash
# ==============================================================================
# CYBERGUARD AI · URBAN SAFETY AI-SOC: MASTER START-ALL RUNNER
# ==============================================================================
# Khởi chạy toàn bộ hệ sinh thái giám sát an ninh AI-SOC chỉ bằng 1 lệnh duy nhất:
#
#   1. Khởi động TẤT CẢ (SOC Web App Dashboard + AI Server + Camera Client):
#      ./start_all.sh
#      ./start_all.sh --headless
#      ./start_all.sh --camera 0 --camera-id cam_01
#
#   2. Khởi động chỉ Dashboard & Backend Web App (Cổng 8000):
#      ./start_all.sh dashboard
#      ./start_all.sh dashboard --port 8000
#
#   3. Khởi động Dashboard + Camera Client trực tiếp (Không cần AI Server phụ):
#      ./start_all.sh direct
#      ./start_all.sh direct --camera 0
#
#   4. Khởi động chỉ AI Inference Server (Cổng 7777 đẩy về 8000):
#      ./start_all.sh ai
#
#   5. Khởi động chỉ Camera Client:
#      ./start_all.sh client
#
#   6. Chạy bộ kiểm thử tự động toàn diện:
#      ./start_all.sh test
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ANSI Colors
CYAN="\033[96m"
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
MAGENTA="\033[95m"
BOLD="\033[1m"
RESET="\033[0m"

# ------------------------------------------------------------------------------
# 1. Phát hiện môi trường Python & Node.js
# ------------------------------------------------------------------------------
PYTHON_BIN=""
PYTEST_BIN=""
CANDIDATE_PYTHONS=(
    "${SCRIPT_DIR}/.venv/bin/python"
    "${SCRIPT_DIR}/AI/Human/.venv/bin/python"
    "/home/test/Hackathon-Test-/.venv/bin/python"
    "$(command -v python3 || echo "")"
)

for p in "${CANDIDATE_PYTHONS[@]}"; do
    if [[ -x "${p}" ]]; then
        PYTHON_BIN="${p}"
        pdir="$(dirname "${p}")"
        if [[ -x "${pdir}/pytest" ]]; then
            PYTEST_BIN="${pdir}/pytest"
        fi
        break
    fi
done

if [[ -z "${PYTHON_BIN}" ]]; then
    echo -e "${RED}❌ Lỗi: Không tìm thấy trình thông dịch Python 3 hợp lệ!${RESET}" >&2
    exit 1
fi

if ! command -v node &>/dev/null; then
    echo -e "${RED}❌ Lỗi: Chưa cài đặt Node.js trên hệ thống!${RESET}" >&2
    exit 1
fi

export PYTHONPATH="${SCRIPT_DIR}/AI/Human/src:${PYTHONPATH:-}"

# ------------------------------------------------------------------------------
# 2. Xử lý tham số dòng lệnh
# ------------------------------------------------------------------------------
MODE="all"
if [[ $# -gt 0 ]] && [[ "$1" =~ ^(all|dashboard|ai|client|direct|test)$ ]]; then
    MODE="$1"
    shift
fi

DASHBOARD_PORT=8000
AI_PORT=7777
CAMERA_IDX="0"
CAMERA_ID="cam_01"
HEADLESS_FLAG="--headless"
NO_CLIENT=false
NO_AI=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            DASHBOARD_PORT="$2"
            shift 2
            ;;
        --ai-port)
            AI_PORT="$2"
            shift 2
            ;;
        --camera)
            CAMERA_IDX="$2"
            shift 2
            ;;
        --camera-id)
            CAMERA_ID="$2"
            shift 2
            ;;
        --gui)
            HEADLESS_FLAG=""
            shift
            ;;
        --headless)
            HEADLESS_FLAG="--headless"
            shift
            ;;
        --no-client)
            NO_CLIENT=true
            shift
            ;;
        --no-ai)
            NO_AI=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# ------------------------------------------------------------------------------
# 3. Chế độ TEST: Chạy bộ kiểm thử tự động
# ------------------------------------------------------------------------------
if [[ "${MODE}" == "test" ]]; then
    echo -e "${BOLD}${CYAN}======================================================================${RESET}"
    echo -e "${BOLD}${CYAN}🧪 CHẠY BỘ KIỂM THỬ TỰ ĐỘNG URBAN SAFETY AI-SOC BACKEND${RESET}"
    echo -e "${BOLD}${CYAN}======================================================================${RESET}"
    if [[ -n "${PYTEST_BIN}" ]]; then
        exec "${PYTEST_BIN}" "Dashboard/Back End/tests/test_backend_suite.py" -v
    else
        exec "${PYTHON_BIN}" -m pytest "Dashboard/Back End/tests/test_backend_suite.py" -v
    fi
    exit 0
fi

# ------------------------------------------------------------------------------
# 4. Kiểm tra và đảm bảo Front End Web App đã được biên dịch
# ------------------------------------------------------------------------------
ensure_frontend_built() {
    local dist_index="${SCRIPT_DIR}/Dashboard/Front End/dist/index.html"
    if [[ ! -f "${dist_index}" ]]; then
        echo -e "${YELLOW}⚙️  Đang biên dịch Front End Web App (Dashboard/Front End)...${RESET}"
        (cd "${SCRIPT_DIR}/Dashboard/Front End" && npm run build)
        echo -e "${GREEN}✅ Front End Web App đã biên dịch thành công.${RESET}"
    fi
}

ensure_backend_dependencies() {
    local node_modules="${SCRIPT_DIR}/Dashboard/Back End/node_modules"
    if [[ ! -d "${node_modules}" ]]; then
        echo -e "${YELLOW}📦 Đang cài đặt thư viện Node.js cho Backend...${RESET}"
        (cd "${SCRIPT_DIR}/Dashboard/Back End" && npm install)
    fi
}

# ------------------------------------------------------------------------------
# 5. Quản lý tiến trình & Dọn dẹp (Cleanup trap)
# ------------------------------------------------------------------------------
BACKEND_PID=""
AI_SERVER_PID=""
CLIENT_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Đang dừng toàn bộ các dịch vụ Urban Safety AI-SOC...${RESET}"
    if [[ -n "${CLIENT_PID}" ]] && kill -0 "${CLIENT_PID}" 2>/dev/null; then
        echo "• Dừng Camera Client (PID: ${CLIENT_PID})..."
        kill -SIGINT "${CLIENT_PID}" 2>/dev/null || true
    fi
    if [[ -n "${AI_SERVER_PID}" ]] && kill -0 "${AI_SERVER_PID}" 2>/dev/null; then
        echo "• Dừng AI Inference Server (PID: ${AI_SERVER_PID})..."
        kill -SIGINT "${AI_SERVER_PID}" 2>/dev/null || true
    fi
    if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
        echo "• Dừng SOC Backend & Web App (PID: ${BACKEND_PID})..."
        kill -SIGINT "${BACKEND_PID}" 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Toàn bộ hệ thống đã tắt an toàn.${RESET}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ------------------------------------------------------------------------------
# 6. Khởi động Dịch vụ SOC Backend & Web App (Cổng 8000)
# ------------------------------------------------------------------------------
start_backend() {
    ensure_backend_dependencies
    ensure_frontend_built

    if curl -s -f -m 1 "http://127.0.0.1:${DASHBOARD_PORT}/api/soc/overview" &>/dev/null; then
        echo -e "${GREEN}✅ SOC Backend & Web App đã chạy sẵn trên cổng ${DASHBOARD_PORT}.${RESET}"
        BACKEND_PID=""
    else
        echo -e "${CYAN}🚀 Khởi động SOC Backend & Web App trên cổng ${DASHBOARD_PORT}...${RESET}"
        (
            cd "${SCRIPT_DIR}/Dashboard/Back End"
            PORT="${DASHBOARD_PORT}" node server.js
        ) > /tmp/soc_backend.log 2>&1 &
        BACKEND_PID=$!

        local wait_count=0
        until curl -s -f -m 1 "http://127.0.0.1:${DASHBOARD_PORT}/api/soc/overview" &>/dev/null; do
            sleep 0.3
            wait_count=$((wait_count + 1))
            if [[ ${wait_count} -gt 30 ]]; then
                echo -e "${RED}❌ Lỗi: Backend không phản hồi sau 10s. Xem log: /tmp/soc_backend.log${RESET}" >&2
                cat /tmp/soc_backend.log | tail -n 20 >&2
                exit 1
            fi
        done
        echo -e "${GREEN}✅ SOC Backend & Web App đã sẵn sàng.${RESET}"
    fi
}

# ------------------------------------------------------------------------------
# 7. Khởi động AI Inference Server (Cổng 7777 đẩy về Backend 8000)
# ------------------------------------------------------------------------------
start_ai_server() {
    if curl -s -f -m 1 "http://127.0.0.1:${AI_PORT}/api/v1/cameras" &>/dev/null; then
        echo -e "${GREEN}✅ AI Inference Server đã chạy sẵn trên cổng ${AI_PORT}.${RESET}"
        AI_SERVER_PID=""
    else
        echo -e "${CYAN}🧠 Khởi động AI Inference Server trên cổng ${AI_PORT} (Đẩy dữ liệu về Backend :${DASHBOARD_PORT})...${RESET}"
        (
            cd "${SCRIPT_DIR}/AI/Human"
            "${PYTHON_BIN}" server.py "${AI_PORT}" --no-tunnel --url "http://127.0.0.1:${DASHBOARD_PORT}/api/v1/incidents"
        ) > /tmp/soc_ai_server.log 2>&1 &
        AI_SERVER_PID=$!

        local wait_count=0
        until curl -s -f -m 1 "http://127.0.0.1:${AI_PORT}/api/v1/cameras" &>/dev/null; do
            sleep 0.3
            wait_count=$((wait_count + 1))
            if [[ ${wait_count} -gt 35 ]]; then
                echo -e "${RED}❌ Lỗi: AI Server không phản hồi sau 12s. Xem log: /tmp/soc_ai_server.log${RESET}" >&2
                cat /tmp/soc_ai_server.log | tail -n 20 >&2
                exit 1
            fi
        done
        echo -e "${GREEN}✅ AI Inference Server đã sẵn sàng.${RESET}"
    fi
}

# ------------------------------------------------------------------------------
# 8. Khởi động Camera Client
# ------------------------------------------------------------------------------
start_camera_client() {
    local target_server="$1"
    echo -e "${CYAN}📹 Khởi động Camera Client [${CAMERA_ID}] truyền trực tiếp về ${target_server}...${RESET}"
    
    local client_args=(
        "${PYTHON_BIN}" "AI/Human/client.py"
        --server-url "${target_server}"
        --camera "${CAMERA_IDX}"
        --camera-id "${CAMERA_ID}"
        --camera-name "Cổng Giám Sát ${CAMERA_ID}"
        --no-tunnel
    )
    if [[ -n "${HEADLESS_FLAG}" ]]; then
        client_args+=("${HEADLESS_FLAG}")
    fi

    "${client_args[@]}"
}

# ------------------------------------------------------------------------------
# 9. ĐIỀU PHỐI CÁC CHẾ ĐỘ CHẠY (EXECUTION DISPATCH)
# ------------------------------------------------------------------------------

LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")"

print_banner() {
    echo ""
    echo -e "${BOLD}${GREEN}======================================================================${RESET}"
    echo -e "${BOLD}${GREEN}✨ HỆ THỐNG URBAN SAFETY AI-SOC ĐÃ KHỞI CHẠY THÀNH CÔNG!${RESET}"
    echo -e "${BOLD}${GREEN}======================================================================${RESET}"
    echo -e "• 📊 ${BOLD}SOC Web App:${RESET}      ${CYAN}http://localhost:${DASHBOARD_PORT}/dashboard/${RESET}"
    echo -e "• 📡 ${BOLD}LAN Access:${RESET}       ${CYAN}http://${LOCAL_IP}:${DASHBOARD_PORT}/dashboard/${RESET}"
    echo -e "• 📹 ${BOLD}MJPEG Video Stream:${RESET} ${CYAN}http://localhost:${DASHBOARD_PORT}/api/v1/cameras/${CAMERA_ID}/stream${RESET}"
    echo -e "• 📸 ${BOLD}Live Snapshot:${RESET}    ${CYAN}http://localhost:${DASHBOARD_PORT}/api/v1/cameras/${CAMERA_ID}/snapshot${RESET}"
    echo -e "• 🔌 ${BOLD}REST API:${RESET}         ${CYAN}http://localhost:${DASHBOARD_PORT}/api/soc/overview${RESET}"
    echo -e "• ⚡ ${BOLD}WebSocket:${RESET}        ${CYAN}ws://localhost:${DASHBOARD_PORT}/ws/live-stream${RESET}"
    echo -e "${BOLD}${GREEN}======================================================================${RESET}"
    echo -e "💡 ${YELLOW}Nhấn Ctrl+C trong terminal bất kỳ lúc nào để dừng toàn bộ hệ thống.${RESET}\n"
}

case "${MODE}" in
    dashboard)
        start_backend
        print_banner
        echo -e "${GREEN}Đang duy trì máy chủ Backend... Nhấn Ctrl+C để thoát.${RESET}"
        wait "${BACKEND_PID}"
        ;;

    ai)
        start_backend
        start_ai_server
        print_banner
        echo -e "${GREEN}Đang duy trì AI Server & Backend... Nhấn Ctrl+C để thoát.${RESET}"
        wait "${AI_SERVER_PID}"
        ;;

    direct)
        start_backend
        print_banner
        # Đẩy stream trực tiếp từ client vào Backend
        start_camera_client "http://127.0.0.1:${DASHBOARD_PORT}"
        ;;

    client)
        start_camera_client "http://127.0.0.1:${DASHBOARD_PORT}"
        ;;

    all|*)
        start_backend
        if [[ "${NO_AI}" == "false" ]]; then
            start_ai_server
        fi
        print_banner

        if [[ "${NO_CLIENT}" == "true" ]]; then
            echo -e "${GREEN}Đang duy trì các dịch vụ nền... Nhấn Ctrl+C để thoát.${RESET}"
            wait
        else
            # Khởi động client đẩy về server
            start_camera_client "http://127.0.0.1:${DASHBOARD_PORT}"
        fi
        ;;
esac
