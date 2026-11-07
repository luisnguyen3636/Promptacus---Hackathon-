#!/usr/bin/env bash
# ==============================================================================
# URBAN SAFETY AI-SOC: RULE & SYSTEM TEST SCRIPT
# ==============================================================================
# Hướng dẫn sử dụng:
#   ./run_test.sh              # Chạy toàn bộ test tự động kiểm tra Rule & Rate Limiter
#   ./run_test.sh live         # Khởi động cả Server & Client với Webcam của bạn để test trực tiếp
#   ./run_test.sh test-weapon  # Giả lập hành vi WEAPON_THREAT để kiểm tra cảnh báo
#   ./run_test.sh test-fallen  # Giả lập hành vi FALLEN để kiểm tra cảnh báo
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# Tìm môi trường Python phù hợp
if [ -f "/home/test/Hackathon-Test-/.venv/bin/python" ]; then
    PYTHON_BIN="/home/test/Hackathon-Test-/.venv/bin/python"
    PYTEST_BIN="/home/test/Hackathon-Test-/.venv/bin/pytest"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$DIR/.venv/bin/python"
    PYTEST_BIN="$DIR/.venv/bin/pytest"
else
    PYTHON_BIN="python3"
    PYTEST_BIN="pytest"
fi

MODE="${1:-unit}"

echo "=============================================================================="
echo "🛡️  URBAN SAFETY AI-SOC - KIỂM THỬ HÀNH VI VÀ RATE LIMITER"
echo "=============================================================================="
echo "• Môi trường: $PYTHON_BIN"
echo "• Chế độ:     $MODE"
echo "=============================================================================="

case "$MODE" in
    unit|"")
        echo -e "\n📋 [1/2] Đang chạy kiểm thử tự động Rule & Rate Limiter..."
        "$PYTEST_BIN" tests/test_rate_limit_and_rules.py -v

        echo -e "\n📋 [2/2] Đang chạy kiểm thử toàn bộ hệ thống..."
        "$PYTEST_BIN" tests/test_rules.py tests/test_multicam.py -v
        echo -e "\n✅ Toàn bộ kiểm thử đã VƯỢT QUA thành công 100%!"
        ;;

    live)
        echo -e "\n🚀 Khởi chạy hệ thống LIVE (Server + Client Webcam)..."
        echo -e "💡 Ngồi thẳng làm việc trước webcam để xác nhận KHÔNG CÒN BỊ FALLEN."
        echo -e "💡 Thử giơ 2 tay lên cao (HANDS_UP) hoặc duỗi thẳng tay ngắm bắn (WEAPON_THREAT)."
        echo -e "💡 Nhấn [q] trên cửa sổ camera để thoát.\n"
        "$PYTHON_BIN" run_system.py
        ;;

    test-weapon)
        echo -e "\n🎯 Khởi chạy giả lập hành vi WEAPON_THREAT..."
        "$PYTHON_BIN" run_system.py --test-action WEAPON_THREAT
        ;;

    test-fallen)
        echo -e "\n🚨 Khởi chạy giả lập hành vi FALLEN..."
        "$PYTHON_BIN" run_system.py --test-action FALLEN
        ;;

    test-knife)
        echo -e "\n🔪 Khởi chạy giả lập hành vi KNIFE_THREAT (Vật nhọn / Dao)..."
        "$PYTHON_BIN" run_system.py --test-action KNIFE_THREAT
        ;;

    post|test-endpoint)
        echo -e "\n🌐 Gửi test POST request trực tiếp tới Endpoint Sự Cố (UrbanStrike)..."
        "$PYTHON_BIN" scripts/test_post_endpoint.py
        ;;

    *)
        echo "Lựa chọn không hợp lệ: $MODE"
        echo "Sử dụng: ./run_test.sh [unit | live | test-weapon | test-fallen | test-knife | post]"
        exit 1
        ;;
esac
