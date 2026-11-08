#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: ALL-IN-ONE MASTER STARTUP SCRIPT
# ==============================================================================
# Khởi chạy toàn bộ hệ sinh thái giám sát an ninh AI-SOC chỉ bằng 1 lệnh:
#
#   QUAN TRỌNG: Tunnel công khai CHỈ do CAMERA CLIENT tạo để stream video.
#               Server KHÔNG tạo tunnel.
#
#   1. Khởi động TẤT CẢ (Server nội bộ + Camera Client + Public Tunnel):
#      ./start.sh
#      ./start.sh --url https://target-webhook-server.com
#
#   2. Khởi động Server nội bộ (KHÔNG tunnel):
#      ./start.sh server
#      ./start.sh server 7777
#      ./start.sh server 7777 --url https://target-webhook-server.com
#
#   3. Khởi động Camera Client + tạo Public Tunnel để stream video từ camera:
#      ./start.sh client
#      ./start.sh client --camera 0 --camera-id LAPTOP_01
#      ./start.sh client --server-url https://xxxx.trycloudflare.com
#
#   4. Lấy URL HLS video công khai (VLC / trình duyệt):
#      ./start.sh hls
#
#   5. Lấy lại Domain / URL Tunnel mới nhất:
#      ./start.sh url
#
#   6. Chạy bộ kiểm thử tự động (Test Suite):
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
# 2b. Quản lý Public Tunnel dùng chung (Cloudflare + fallback localhost.run)
# ------------------------------------------------------------------------------
# Cloudflare quick tunnel thường xuyên bị giới hạn tốc độ (HTTP 429) hoặc timeout.
# Trước đây script chỉ thử Cloudflare 1 lần rồi im lặng -> người dùng KHÔNG thấy URL.
# Bộ hàm dưới đây: thử Cloudflare nhiều lần -> fallback localhost.run (SSH) ->
# dùng lại URL cũ còn sống -> tự động thử lại ở nền và IN URL thật rõ ràng.
TUNNEL_URL_FILE="${SCRIPT_DIR}/latest_tunnel_url.txt"
TUNNEL_RUNTIME_FILE="/tmp/soc_public_url.txt"
TUNNEL_CF_ATTEMPTS="${TUNNEL_CF_ATTEMPTS:-2}"
TUNNEL_CF_WAIT_SECONDS="${TUNNEL_CF_WAIT_SECONDS:-18}"
TUNNEL_LHR_WAIT_SECONDS="${TUNNEL_LHR_WAIT_SECONDS:-25}"

PUBLIC_URL=""
TUNNEL_PID=""
TUNNEL_PROVIDER=""

extract_cloudflare_url() {
    [[ -f "${1:-}" ]] || return 0
    grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$1" 2>/dev/null | head -n 1 || true
}

extract_localhost_run_url() {
    [[ -f "${1:-}" ]] || return 0
    grep -oE "https://[a-zA-Z0-9]+\.lhr\.life" "$1" 2>/dev/null | head -n 1 || true
}

# Khởi chạy Cloudflare quick tunnel, tự thử lại khi bị 429/timeout.
# Cập nhật globals: TUNNEL_PID, PUBLIC_URL, TUNNEL_PROVIDER
start_cloudflare_tunnel() {
    local local_url="$1"
    local logfile="$2"
    local bin attempt=1 url="" verdict err waited backoff

    TUNNEL_PID=""
    PUBLIC_URL=""
    TUNNEL_PROVIDER=""

    bin="$(ensure_cloudflared || true)"
    if [[ -z "${bin}" || ! -x "${bin}" ]]; then
        echo "⚠️  Không tìm thấy binary cloudflared (bỏ qua Cloudflare Tunnel)." >&2
        return 1
    fi

    while [[ ${attempt} -le ${TUNNEL_CF_ATTEMPTS} ]]; do
        echo "🌐 [Cloudflare ${attempt}/${TUNNEL_CF_ATTEMPTS}] Đang xin quick tunnel cho ${local_url} ..."
        rm -f "${logfile}"
        "${bin}" tunnel --url "${local_url}" --no-autoupdate > "${logfile}" 2>&1 &
        TUNNEL_PID=$!

        url=""
        waited=0
        while [[ ${waited} -lt $((TUNNEL_CF_WAIT_SECONDS * 2)) ]]; do
            url="$(extract_cloudflare_url "${logfile}")"
            if [[ -n "${url}" ]]; then
                break
            fi
            if grep -qE "quick tunnel provisioning failed|failed to request quick Tunnel" "${logfile}" 2>/dev/null; then
                break
            fi
            sleep 0.5
            waited=$((waited + 1))
        done

        if [[ -n "${url}" ]]; then
            PUBLIC_URL="${url}"
            TUNNEL_PROVIDER="cloudflare"
            echo "✅ Cloudflare Tunnel đã cấp URL: ${PUBLIC_URL}" >&2
            return 0
        fi

        err="$(grep -oE "quick tunnel provisioning failed with status [0-9]+" "${logfile}" 2>/dev/null | tail -n 1 || true)"
        if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
            kill -SIGTERM "${TUNNEL_PID}" 2>/dev/null || true
        fi
        TUNNEL_PID=""
        echo "⚠️  Cloudflare chưa cấp được tunnel${err:+ (${err})}." >&2

        attempt=$((attempt + 1))
        if [[ ${attempt} -le ${TUNNEL_CF_ATTEMPTS} ]]; then
            backoff=$((attempt * 3))
            echo "⏳ Thử lại Cloudflare sau ${backoff}s ..." >&2
            sleep "${backoff}"
        fi
    done

    echo "❌ Cloudflare quick tunnel thất bại sau ${TUNNEL_CF_ATTEMPTS} lần thử." >&2
    return 1
}

# Fallback: SSH reverse tunnel qua localhost.run (HTTPS, không bị rate limit 429).
start_localhost_run_tunnel() {
    local local_port="$1"
    local logfile="$2"
    local url="" waited=0

    TUNNEL_PID=""
    PUBLIC_URL=""
    TUNNEL_PROVIDER=""

    if ! command -v ssh &>/dev/null; then
        echo "⚠️  Không có ssh trên máy (bỏ qua fallback localhost.run)." >&2
        return 1
    fi

    echo "🌐 [Fallback] Đang tạo HTTPS tunnel qua localhost.run (SSH, cổng ${local_port}) ..."
    rm -f "${logfile}"
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=15 \
        -o ServerAliveCountMax=3 \
        -o TCPKeepAlive=yes \
        -o Compression=no \
        -o ExitOnForwardFailure=yes \
        -o LogLevel=ERROR \
        -T -R "80:127.0.0.1:${local_port}" nokey@localhost.run > "${logfile}" 2>&1 &
    TUNNEL_PID=$!

    while [[ ${waited} -lt $((TUNNEL_LHR_WAIT_SECONDS * 2)) ]]; do
        url="$(extract_localhost_run_url "${logfile}")"
        if [[ -n "${url}" ]]; then
            break
        fi
        sleep 0.5
        waited=$((waited + 1))
    done

    if [[ -n "${url}" ]]; then
        PUBLIC_URL="${url}"
        TUNNEL_PROVIDER="localhost.run"
        echo "✅ localhost.run Tunnel đã cấp URL: ${PUBLIC_URL}" >&2
        return 0
    fi

    echo "❌ localhost.run không cấp được URL công khai." >&2
    if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
        kill -SIGTERM "${TUNNEL_PID}" 2>/dev/null || true
    fi
    TUNNEL_PID=""
    return 1
}

# Wrapper: Cloudflare -> localhost.run
start_public_tunnel() {
    local local_url="$1"
    local tag="${2:-tunnel}"
    local port

    port="$(printf '%s' "${local_url}" | sed -E 's#^.*:([0-9]+).*$#\1#')"
    [[ "${port}" =~ ^[0-9]+$ ]] || port=8000

    PUBLIC_URL=""
    TUNNEL_PID=""
    TUNNEL_PROVIDER=""

    if start_cloudflare_tunnel "${local_url}" "/tmp/soc_tunnel_${tag}.log"; then
        return 0
    fi

    echo "🔁 Chuyển sang phương án dự phòng localhost.run để vẫn có URL công khai ..."
    if start_localhost_run_tunnel "${port}" "/tmp/soc_tunnel_${tag}_lhr.log"; then
        return 0
    fi
    return 1
}

# Kiểm tra URL tunnel có truy cập được không (tránh hiển thị URL đã chết).
probe_public_url() {
    local url="${1:-}"
    local code="" path
    [[ -n "${url}" ]] || return 1
    command -v curl &>/dev/null || return 0
    for path in "/api/v1/cameras" "/watch" "/dashboard"; do
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "${url}${path}" 2>/dev/null || true)"
        case "${code}" in
            2*|3*|4*) return 0 ;;
        esac
    done
    return 1
}

load_cached_tunnel_url() {
    local f url
    for f in "${TUNNEL_URL_FILE}" "${TUNNEL_RUNTIME_FILE}" "${SCRIPT_DIR}/output/public_url.txt"; do
        [[ -s "${f}" ]] || continue
        url="$(head -n 1 "${f}" | tr -d '[:space:]')"
        if [[ -n "${url}" ]]; then
            printf '%s' "${url}"
            return 0
        fi
    done
    return 1
}

save_tunnel_url() {
    local url="$1"
    [[ -n "${url}" ]] || return 1
    printf '%s\n' "${url}" > "${TUNNEL_RUNTIME_FILE}"
    printf '%s\n' "${url}" > "${TUNNEL_URL_FILE}"
    if [[ -f "${SCRIPT_DIR}/.env" ]]; then
        if grep -q '^PUBLIC_STREAM_URL=' "${SCRIPT_DIR}/.env" 2>/dev/null; then
            sed -i "s|^PUBLIC_STREAM_URL=.*|PUBLIC_STREAM_URL=${url}|" "${SCRIPT_DIR}/.env"
        else
            printf 'PUBLIC_STREAM_URL=%s\n' "${url}" >> "${SCRIPT_DIR}/.env"
        fi
    fi
    export PUBLIC_STREAM_URL="${url}"
}

print_tunnel_banner() {
    local url="$1"
    local provider="${2:-public}"
    local healthy="${3:-unknown}"

    echo "======================================================================"
    echo "🎬 PUBLIC HLS VIDEO TUNNEL (${provider}): ${url}"
    echo "======================================================================"
    echo "• ▶️  XEM VIDEO trên trình duyệt:  ${url}/watch"
    echo "• 🎞️  HLS Playlist (.m3u8 - VLC):  ${url}/live.m3u8"
    echo "• 📹 MJPEG Stream (fallback):      ${url}/stream.mjpg"
    echo "• 📸 Snapshot tức thì:             ${url}/snapshot.jpg"
    echo "----------------------------------------------------------------------"
    echo "• 🩺 Trạng thái truy cập:          ${healthy}"
    echo "• 💾 URL đã lưu tại:               ${TUNNEL_URL_FILE}"
    echo "• 💡 Lấy lại URL HLS:              ./start.sh hls"
    echo "----------------------------------------------------------------------"
    echo "ℹ️  SOC Dashboard (KHÔNG phải video): ${url}/dashboard"
    echo "======================================================================"
}

# Thử lại tunnel ở nền khi cả 2 nhà cung cấp đều thất bại, để người dùng
# vẫn nhận được URL ngay khi Cloudflare/localhost.run sẵn sàng trở lại.
start_background_tunnel_retry() {
    local local_url="$1"
    local tag="$2"
    local rounds="${3:-4}"
    local pid_file="/tmp/soc_tunnel_watcher.pid"

    (
        for round in $(seq 1 "${rounds}"); do
            sleep 20
            if start_public_tunnel "${local_url}" "${tag}_retry_${round}"; then
                save_tunnel_url "${PUBLIC_URL}"
                printf '\n'
                print_tunnel_banner "${PUBLIC_URL}" "${TUNNEL_PROVIDER}" "Đã kết nối (thử lại nền lần ${round})"
                if [[ -n "${TUNNEL_PID}" ]]; then
                    printf '%s\n' "${TUNNEL_PID}" > "/tmp/soc_tunnel_extra.pid"
                fi
                return 0
            fi
        done
        echo "⚠️  Vẫn chưa tạo được tunnel sau ${rounds} lần thử lại nền." >&2
        echo "   Xem log: /tmp/soc_tunnel_${tag}_retry_*.log" >&2
    ) &
    printf '%s\n' "$!" > "${pid_file}"
}

stop_managed_tunnels() {
    local pid_file pid
    for pid_file in "${TUNNEL_PID:-}" "$(cat /tmp/soc_tunnel_watcher.pid 2>/dev/null || true)" "$(cat /tmp/soc_tunnel_extra.pid 2>/dev/null || true)"; do
        [[ -n "${pid_file}" ]] || continue
        if kill -0 "${pid_file}" 2>/dev/null; then
            kill -SIGTERM "${pid_file}" 2>/dev/null || true
        fi
    done
    rm -f /tmp/soc_tunnel_watcher.pid /tmp/soc_tunnel_extra.pid
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
        echo "   ./start.sh --url https://urbanstrike.tech/api/incident"
        echo ""
        echo "2. Lấy nhanh URL HLS video đang stream qua tunnel (dùng cho VLC/trình duyệt):"
        echo "   ./start.sh hls"
        echo ""
        echo "3. Lấy lại Domain / URL Tunnel mới nhất đang chạy:"
        echo "   ./start.sh url"
        echo ""
        echo "4. Khởi động Server nội bộ (KHÔNG tạo tunnel):"
        echo "   ./start.sh server"
        echo "   ./start.sh server 8000"
        echo ""
        echo "5. Khởi động Camera Client (bên DUY NHẤT tạo Public Tunnel stream video):"
        echo "   ./start.sh client"
        echo "   ./start.sh client --camera 0 --camera-id LAPTOP_01"
        echo ""
        echo "6. Chạy bộ kiểm thử tự động (Test Suite):"
        echo "   ./start.sh test"
        echo "   ./start.sh test unit"
        echo "======================================================================"
        exit 0
        ;;

    # --------------------------------------------------------------------------
    # LẤY DOMAIN TUNNEL MỚI NHẤT ĐANG HOẠT ĐỘNG
    # --------------------------------------------------------------------------
    url|get-url|domain)
        CACHED_URL="$(load_cached_tunnel_url || true)"
        if [[ -z "${CACHED_URL}" ]]; then
            SERVER_URL_RESP=$(curl -s --max-time 1.5 "http://127.0.0.1:8000/tunnel" 2>/dev/null || true)
            if [[ "${SERVER_URL_RESP}" =~ ^https:// ]]; then
                CACHED_URL="${SERVER_URL_RESP}"
            fi
        fi
        if [[ -z "${CACHED_URL}" ]]; then
            echo "❌ Chưa có tunnel nào đang hoạt động. Khởi động bằng: ./start.sh client" >&2
            exit 1
        fi
        echo "${CACHED_URL}"
        if probe_public_url "${CACHED_URL}"; then
            echo "✅ Tunnel đang hoạt động." >&2
        else
            echo "⚠️  URL này hiện KHÔNG truy cập được (tunnel có thể đã tắt). Tạo tunnel mới: ./start.sh client" >&2
        fi
        exit 0
        ;;

    # --------------------------------------------------------------------------
    # LẤY URL STREAM VIDEO HLS QUA TUNNEL (dùng cho VLC / trình duyệt / OBS)
    # --------------------------------------------------------------------------
    hls|stream|video)
        CACHED_URL="$(load_cached_tunnel_url || true)"
        if [[ -z "${CACHED_URL}" ]]; then
            SERVER_URL_RESP=$(curl -s --max-time 1.5 "http://127.0.0.1:8000/tunnel" 2>/dev/null || true)
            if [[ "${SERVER_URL_RESP}" =~ ^https:// ]]; then
                CACHED_URL="${SERVER_URL_RESP}"
            fi
        fi
        if [[ -z "${CACHED_URL}" ]]; then
            echo "❌ Chưa có tunnel để stream video. Khởi động: ./start.sh client" >&2
            exit 1
        fi
        echo "======================================================================"
        echo "🎬 PUBLIC HLS VIDEO STREAM"
        echo "======================================================================"
        echo "• ▶️  Trình duyệt (player):   ${CACHED_URL}/watch"
        echo "• 🎞️  HLS (.m3u8 cho VLC):    ${CACHED_URL}/live.m3u8"
        echo "• 📹 MJPEG stream:            ${CACHED_URL}/stream.mjpg"
        echo "======================================================================"
        echo "${CACHED_URL}/live.m3u8"
        exit 0
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 1: Khởi động Central Server (KHÔNG tạo tunnel - tunnel chỉ do client)
    # --------------------------------------------------------------------------
    server)
        shift
        SERVER_ARGS=()
        SERVER_PORT="7777"

        while [[ $# -gt 0 ]]; do
            case "$1" in
                --tunnel|-t)
                    echo "ℹ️  Bỏ qua --tunnel: tunnel công khai chỉ do CAMERA CLIENT tạo (./start.sh client)."
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

        echo "======================================================================"
        echo "🚀 Khởi động Urban Safety Central Inference Server (Cổng ${SERVER_PORT})"
        echo "🐍 Python: $PYTHON_BIN"
        echo "📁 Thư mục: $SCRIPT_DIR"
        echo "ℹ️  Server KHÔNG tạo tunnel. Video được stream công khai qua CAMERA CLIENT:"
        echo "    ./start.sh client      # client tự tạo URL HLS để xem video"
        echo "======================================================================"
        exec "$PYTHON_BIN" "$SCRIPT_DIR/server.py" ${SERVER_ARGS[@]+"${SERVER_ARGS[@]}"}
        ;;

    # --------------------------------------------------------------------------
    # Tunnel độc lập đã bị loại bỏ: chỉ CAMERA CLIENT được tạo tunnel
    # --------------------------------------------------------------------------
    tunnel)
        echo "❌ Chế độ 'tunnel' độc lập đã bị loại bỏ." >&2
        echo "   Tunnel công khai chỉ do CAMERA CLIENT tạo để stream video từ camera:" >&2
        echo "      ./start.sh client" >&2
        echo "   Lấy URL HLS đang chạy:" >&2
        echo "      ./start.sh hls" >&2
        exit 1
        ;;

    # --------------------------------------------------------------------------
    # CHẾ ĐỘ 2: Khởi động Camera Client kèm Tự động kích hoạt Public Tunneling
    # --------------------------------------------------------------------------
    client|camera|edge)
        shift
        CLIENT_ARGS=()
        WANT_TUNNEL=true

        # Tách các cờ do start.sh quản lý, phần còn lại chuyển nguyên vẹn cho client.py
        for arg in "$@"; do
            case "${arg}" in
                --no-tunnel) WANT_TUNNEL=false ;;
                --tunnel)    WANT_TUNNEL=true ;;
            esac
            CLIENT_ARGS+=("${arg}")
        done

        # Đọc biến PORT từ .env nếu có
        ENV_PORT=""
        if [[ -f "${SCRIPT_DIR}/.env" ]]; then
            ENV_PORT="$(grep -E '^PORT=[0-9]+' "${SCRIPT_DIR}/.env" | tail -n 1 | cut -d'=' -f2 || true)"
        fi

        # Xác định Server Port từ tham số --server-url hoặc cấu hình (mặc định 8000)
        SERVER_PORT="${ENV_PORT:-${PORT:-8000}}"
        CUSTOM_SERVER_URL=""
        for i in "${!CLIENT_ARGS[@]}"; do
            if [[ "${CLIENT_ARGS[$i]}" == "--server-url" && $((i + 1)) -lt ${#CLIENT_ARGS[@]} ]]; then
                CUSTOM_SERVER_URL="${CLIENT_ARGS[$((i + 1))]}"
                if [[ -n "${CUSTOM_SERVER_URL}" ]] && [[ "${CUSTOM_SERVER_URL}" =~ :([0-9]+) ]]; then
                    SERVER_PORT="${BASH_REMATCH[1]}"
                fi
            fi
        done

        # Server nằm ở máy khác -> không tạo tunnel cho localhost
        IS_REMOTE_SERVER=false
        if [[ -n "${CUSTOM_SERVER_URL}" ]] && [[ ! "${CUSTOM_SERVER_URL}" =~ (localhost|127\.0\.0\.1) ]]; then
            IS_REMOTE_SERVER=true
        fi

        SERVER_LOCAL_URL="http://127.0.0.1:${SERVER_PORT}"
        TARGET_SERVER_URL="${CUSTOM_SERVER_URL:-${SERVER_LOCAL_URL}}"

        echo "======================================================================"
        echo "📹 Khởi động Edge Camera Client + Public Tunnel tự động"
        echo "🐍 Python: $PYTHON_BIN"
        echo "🔌 Server mục tiêu: ${TARGET_SERVER_URL}"
        echo "🌐 Tạo tunnel công khai: $([[ "${WANT_TUNNEL}" == "true" && "${IS_REMOTE_SERVER}" == "false" ]] && echo "CÓ" || echo "KHÔNG")"
        echo "======================================================================"

        AUTO_SERVER_PID=""
        TUNNEL_PID=""

        cleanup_client_all() {
            echo ""
            echo "🛑 Đang dọn dẹp và dừng các tiến trình liên quan..."
            if [[ -n "${TUNNEL_PID:-}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
                echo "• Dừng Public Tunnel (PID: ${TUNNEL_PID})..."
                kill -SIGTERM "${TUNNEL_PID}" 2>/dev/null || true
            fi
            stop_managed_tunnels
            if [[ -n "${AUTO_SERVER_PID:-}" ]] && kill -0 "${AUTO_SERVER_PID}" 2>/dev/null; then
                echo "• Dừng Auto-started Server (PID: ${AUTO_SERVER_PID})..."
                kill -SIGINT "${AUTO_SERVER_PID}" 2>/dev/null || true
            fi
            # Server do chế độ ./start.sh (all) khởi chạy trước khi bàn giao cho client
            if [[ -n "${SOC_PARENT_SERVER_PID:-}" ]] && kill -0 "${SOC_PARENT_SERVER_PID}" 2>/dev/null; then
                echo "• Dừng Central Server (PID: ${SOC_PARENT_SERVER_PID})..."
                kill -SIGINT "${SOC_PARENT_SERVER_PID}" 2>/dev/null || true
            fi
            exit 0
        }
        trap cleanup_client_all SIGINT SIGTERM EXIT

        # 1. Kiểm tra xem Server đã chạy sẵn trên cổng SERVER_PORT chưa (chỉ với server nội bộ)
        SERVER_IS_RUNNING=false
        if [[ "${IS_REMOTE_SERVER}" == "true" ]]; then
            echo "ℹ️  Server đang ở máy khác (${CUSTOM_SERVER_URL}); bỏ qua kiểm tra/tự khởi chạy server nội bộ."
            SERVER_IS_RUNNING=true
        elif command -v curl &>/dev/null && curl -s --max-time 1.5 "${SERVER_LOCAL_URL}/api/v1/cameras" >/dev/null 2>&1; then
            SERVER_IS_RUNNING=true
        fi

        if [[ "${IS_REMOTE_SERVER}" == "false" && "${SERVER_IS_RUNNING}" == "false" ]]; then
            echo "🚀 Chưa phát hiện AI-SOC Server tại ${SERVER_LOCAL_URL}. Tự động khởi chạy Server trong nền..."
            "${PYTHON_BIN}" server.py "${SERVER_PORT}" \
                --weights yolo/yolo11n-pose.pt \
                --webhook-cooldown 0.5 \
                --max-rpm 120 \
                --no-tunnel \
                --output-dir output > /tmp/soc_server_client_mode.log 2>&1 &
            AUTO_SERVER_PID=$!
            echo "⏳ Đang đợi Server sẵn sàng (PID: ${AUTO_SERVER_PID})..."

            for i in {1..30}; do
                if curl -s --max-time 1 "${SERVER_LOCAL_URL}/api/v1/cameras" >/dev/null 2>&1; then
                    SERVER_IS_RUNNING=true
                    echo "✅ AI-SOC Inference Server đã sẵn sàng tiếp nhận luồng video."
                    break
                fi
                sleep 0.4
            done
            if [[ "${SERVER_IS_RUNNING}" == "false" ]]; then
                echo "⚠️ Cảnh báo: Server khởi động chậm hoặc có lỗi, vui lòng kiểm tra /tmp/soc_server_client_mode.log"
            fi
        elif [[ "${IS_REMOTE_SERVER}" == "false" ]]; then
            echo "✅ Phát hiện AI-SOC Server đang chạy sẵn trên cổng ${SERVER_PORT}."
        fi

        # 2. Khởi tạo Public Tunnel (Cloudflare -> localhost.run).
        # KHÔNG xoá URL cũ trước khi có URL mới, để người dùng không bị "mất URL".
        OLD_URL="$(load_cached_tunnel_url || true)"
        PUBLIC_URL=""
        TUNNEL_PID=""

        if [[ "${WANT_TUNNEL}" == "true" && "${IS_REMOTE_SERVER}" == "true" ]]; then
            case "${CUSTOM_SERVER_URL}" in
                https://*)
                    PUBLIC_URL="${CUSTOM_SERVER_URL}"
                    echo "ℹ️  Dùng luôn URL public của server từ xa: ${PUBLIC_URL}"
                    ;;
                *)
                    echo "ℹ️  Server từ xa không phải HTTPS nên không có public URL tunnel."
                    ;;
            esac
        elif [[ "${WANT_TUNNEL}" == "true" ]]; then
            # Dọn tunnel cũ cùng cổng (nếu có) để tránh trùng lặp
            pkill -f "cloudflared tunnel.*127.0.0.1:${SERVER_PORT}" 2>/dev/null || true

            if start_public_tunnel "${SERVER_LOCAL_URL}" "client"; then
                if probe_public_url "${PUBLIC_URL}"; then
                    HEALTH="✅ Đã kiểm tra, truy cập được"
                else
                    HEALTH="⏳ Vừa tạo, DNS có thể cần vài giây"
                fi
                save_tunnel_url "${PUBLIC_URL}"
                print_tunnel_banner "${PUBLIC_URL}" "${TUNNEL_PROVIDER}" "${HEALTH}"
            else
                echo "======================================================================"
                echo "⚠️  KHÔNG tạo được tunnel công khai mới (Cloudflare + localhost.run đều lỗi)."
                if [[ -n "${OLD_URL}" ]]; then
                    if probe_public_url "${OLD_URL}"; then
                        PUBLIC_URL="${OLD_URL}"
                        echo "♻️  Dùng lại URL cũ vẫn còn hoạt động: ${PUBLIC_URL}"
                        print_tunnel_banner "${PUBLIC_URL}" "cache" "✅ Đã kiểm tra, truy cập được"
                    else
                        echo "• URL cũ (có thể đã chết): ${OLD_URL}"
                    fi
                fi
                echo "• Log Cloudflare: /tmp/soc_tunnel_client.log"
                echo "• Log fallback:   /tmp/soc_tunnel_client_lhr.log"
                echo "• Client vẫn khởi động bình thường, chỉ thiếu URL công khai."
                echo "======================================================================"
                start_background_tunnel_retry "${SERVER_LOCAL_URL}" "client" 4
                echo "🔄 Đã bật tiến trình THỬ LẠI TUNNEL Ở NỀN (tối đa 4 lần). URL sẽ tự in ra ngay khi có."
            fi
        else
            echo "ℹ️  Đã tắt tạo tunnel (--no-tunnel). Chỉ dùng server nội bộ: ${SERVER_LOCAL_URL}"
        fi

        # 3. Khởi động Camera Client
        if [[ -z "${CUSTOM_SERVER_URL}" ]]; then
            CLIENT_ARGS+=("--server-url" "${SERVER_LOCAL_URL}")
        fi
        # Tránh khởi tạo 2 tunnel trùng lặp vì start.sh đã quản lý tunnel
        CLIENT_ARGS+=("--no-tunnel")

        # Đảm bảo client.py hiển thị đúng public URL (kể cả provider fallback)
        if [[ -n "${PUBLIC_URL}" ]]; then
            export PUBLIC_STREAM_URL="${PUBLIC_URL}"
        fi

        echo "📹 Đang khởi động Camera Client ..."
        echo "💡 Nhấn 'q' trên cửa sổ camera hoặc Ctrl+C để dừng toàn bộ."
        echo ""
        "$PYTHON_BIN" "$SCRIPT_DIR/client.py" ${CLIENT_ARGS[@]+"${CLIENT_ARGS[@]}"}
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

        SERVER_PORT="${PORT:-7777}"
        SERVER_URL="http://127.0.0.1:${SERVER_PORT}"
        SERVER_PID=""

        cleanup() {
            echo ""
            echo "🛑 Đang dọn dẹp và dừng các dịch vụ AI-SOC..."
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
        echo "ℹ️  Tunnel công khai do CAMERA CLIENT tạo (server không tạo tunnel)."
        echo "======================================================================"

        # 4.1 Khởi động Central Server nếu chưa chạy (luôn --no-tunnel)
        if curl -s -f -m 1 "${SERVER_URL}/api/v1/cameras" &>/dev/null; then
            echo "✅ Central Inference Server đã chạy sẵn trên cổng ${SERVER_PORT}."
            SERVER_PID=""
        else
            echo "🚀 [1/2] Đang khởi động Central Inference Server trên cổng ${SERVER_PORT}..."
            SERVER_CMD=("${PYTHON_BIN}" server.py "${SERVER_PORT}" --no-tunnel)
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

        # 4.2 In thông tin điều khiển hệ thống
        LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")"
        echo "======================================================================"
        echo "✨ HỆ THỐNG URBAN SAFETY AI-SOC ĐÃ KHỞI CHẠY!"
        echo "======================================================================"
        echo "• 📊 SOC Web Dashboard:   ${SERVER_URL}/dashboard"
        echo "• 📹 Local MJPEG Stream:  ${SERVER_URL}/stream.mjpg"
        echo "• 📺 Local HLS Stream:    ${SERVER_URL}/live.m3u8"
        echo "• 📡 LAN Access URL:      http://${LOCAL_IP}:${SERVER_PORT}/dashboard"
        echo "• 🌍 Public HLS URL:      do CAMERA CLIENT tạo và in ra ngay sau đây"
        echo "======================================================================"

        # 4.3 Bàn giao cho chế độ client (client là bên DUY NHẤT tạo tunnel)
        echo "📹 [2/2] Đang kết nối Camera Client + tạo public tunnel ..."
        echo "💡 Mẹo: Nhấn phím 'q' trên cửa sổ camera hoặc Ctrl+C trong terminal để dừng."
        echo ""

        export SOC_PARENT_SERVER_PID="${SERVER_PID}"
        exec "${BASH_SOURCE[0]}" client --server-url "${SERVER_URL}" ${REMAINING_ARGS[@]+"${REMAINING_ARGS[@]}"}
        ;;
esac
