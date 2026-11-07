# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## MỞ RỘNG GIÁM SÁT ĐA PHƯƠNG THỨC NGHE - NHÌN & PHÁT HIỆN TIẾNG LA HÉT (ACOUSTIC DISTRESS DETECTION & MULTIMODAL FUSION)
**Mã kế hoạch:** `PLAN-URBANSOC-AUDIO-03`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-AUDIO-03`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** Chờ phê duyệt từ Principal Architect / Lead Developer

---

## 1. DANH SÁCH FILE CẦN TẠO MỚI & CẬP NHẬT

### 1.1. Các File Tạo Mới
1. **`src/urbansoc/domain/audio_models.py`:**
   - Định nghĩa `AudioThreatType` (NONE, SCREAM, GUNSHOT, AGGRESSIVE_SHOUT, DISTRESS_CRY, GLASS_BREAK).
   - Định nghĩa `AudioAnalysisResult` (dataclass lưu trữ kết quả phân tích âm thanh, chỉ số RMS, Centroid, ZCR, SBER, waveform).
   - Định nghĩa `MultimodalThreatResult` (dataclass lưu trữ kết quả sau khi hợp nhất Nghe-Nhìn).
2. **`src/urbansoc/audio/__init__.py`:**
   - Export các class công khai: `AudioCaptureBackend`, `AcousticThreatDetector`, `MultimodalThreatFuser`.
3. **`src/urbansoc/audio/microphone.py`:**
   - Thu nhận âm thanh bất đồng bộ, non-blocking trong background thread:
     - Tự động phát hiện backend: ALSA `arecord` subprocess trực tiếp (native Linux) $\to$ `sounddevice` (nếu PortAudio có sẵn) $\to$ `WAVFileReader` $\to$ `SyntheticAudioStream` (cho test) $\to$ `SilentAudioFallback`.
     - Vòng đệm 5 giây (`AudioRollingBuffer`) để lưu bằng chứng âm thanh kèm video clip khi có sự cố.
     - Cam kết 0% nguy cơ crash nếu không có micro vật lý.
4. **`src/urbansoc/audio/scream_detector.py`:**
   - Bộ xử lý tín hiệu số âm thanh (DSP & Feature Extraction) dùng `numpy` & `scipy`:
     - Phân tích STFT / FFT 4096 điểm tại 16 kHz.
     - Tính toán RMS Decibel, Adaptive Ambient Floor (EMA), Spectral Centroid, Scream Band Energy Ratio (1.5k - 4.5k Hz), Zero-Crossing Rate.
     - Bộ phân loại: `SCREAM`, `GUNSHOT`, `AGGRESSIVE_SHOUT`, `GLASS_BREAK` kèm bộ lọc khử báo động giả (thời lượng $\ge 250\text{ms}$, loại trừ tiếng còi xe và tiếng đập bàn ngắn).
5. **`src/urbansoc/audio/fusion.py`:**
   - Động cơ hợp nhất Nghe - Nhìn (Multimodal Threat Fuser):
     - Ma trận hợp nhất 10 quy tắc `MM-01` đến `MM-10`.
     - Fast-track leo thang đe dọa tức thì lên `CRITICAL` khi tư thế hiểm họa gặp tiếng hét hoặc tiếng súng.
     - Hỗ trợ `OFF_SCREEN_ACOUSTIC_DISTRESS` khi video chưa thấy người nhưng micro nghe tiếng thét.
6. **`tests/test_audio.py`:**
   - Bộ test tự động kiểm thử toàn diện:
     - Tạo sóng âm thanh nhân tạo (Synthetic Sine Waves): Tần số tiếng hét 2500 Hz vs Tiếng nói thường 400 Hz vs Tiếng ồn trắng vs Khoảng lặng.
     - Kiểm thử `AcousticThreatDetector` nhận diện chính xác tiếng hét và loại bỏ tiếng nói thường.
     - Kiểm thử `AudioCaptureBackend` fallback mượt mà khi không có micro.
     - Kiểm thử `MultimodalThreatFuser` leo thang điểm đe dọa chính xác theo ma trận `MM-01` - `MM-10`.

### 1.2. Các File Cần Sửa Đổi
1. **`src/urbansoc/domain/__init__.py`:**
   - Export các schema âm thanh mới từ `audio_models.py`.
2. **`src/urbansoc/render/hud.py`:**
   - Bổ sung thanh hiển thị âm lượng thời gian thực (Audio VU Meter dạng thanh decibel đồ họa trực quan).
   - Bổ sung nhãn cảnh báo âm thanh nguy hiểm nhấp nháy: `[ AUDIO: SCREAM DETECTED ]` hoặc `[ AUDIO: GUNSHOT DETECTED ]`.
3. **`src/urbansoc/apps/live.py`:**
   - Khởi tạo `AudioCaptureBackend`, `AcousticThreatDetector`, và `MultimodalThreatFuser`.
   - Kết hợp kết quả mỗi frame video với frame âm thanh tương ứng.
   - Ghi nhận vào file audit log kép (cả JSONL và Human-readable).
4. **`src/urbansoc/cli.py`:**
   - Thêm các tham số CLI:
     - `--audio / --no-audio`: Bật/tắt chế độ lắng nghe âm thanh (mặc định: bật với auto-fallback).
     - `--audio-source`: Cho phép chọn `auto`, `arecord`, `mock`, hoặc đường dẫn tới file `.wav`.
     - `--scream-sensitivity`: Độ nhạy phát hiện tiếng hét (0.1 - 1.0, mặc định: 0.85).
5. **`main.py`:**
   - Bảo đảm duy trì cơ chế chạy 1 file duy nhất `python3 main.py` mượt mà.

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION PLAN)

### 2.1. Kiểm thử Đơn vị & Tích hợp Tự động (`pytest`)
- Chạy toàn bộ test suite bằng lệnh:
  ```bash
  /home/test/Hackathon-Test-/.venv/bin/pytest -v tests/test_audio.py
  /home/test/Hackathon-Test-/.venv/bin/pytest -v
  ```
- Tiêu chí: **100% tests Passed** (Cả 33 bài test cũ và toàn bộ các bài test audio mới).

### 2.2. Kiểm thử Kịch bản Âm thanh Nghiệp vụ
1. **Âm thanh Tiếng thét Cầu cứu (Synthetic Scream: 2500 Hz + RMS cao + ZCR cao):**
   - Kết quả: `event_type == AudioThreatType.SCREAM`, `threat_score >= 0.85`.
2. **Âm thanh Tiếng nói chuyện Thông thường (Speech: 300 - 800 Hz):**
   - Kết quả: `event_type == AudioThreatType.NONE`, không kích hoạt cảnh báo nguy hiểm.
3. **Âm thanh Tiếng súng Nổ / Xung kích cực đại (Gunshot impulse):**
   - Kết quả: `event_type == AudioThreatType.GUNSHOT`, `threat_score >= 0.95`.
4. **Hợp nhất Nghe - Nhìn:**
   - Test kết hợp `FIGHTING` + `SCREAM` $\to$ Threat Score = `1.00`, Level = `CRITICAL`.
   - Test kết hợp `HANDS_UP` + `SCREAM` $\to$ Threat Score = `0.99`, Level = `CRITICAL`.
   - Test `NORMAL` + `SCREAM` $\to$ Threat Score = `0.78`, Level = `HIGH` (Off-screen distress).

### 2.3. Kiểm thử Khả năng Chống Sập & Khởi chạy CLI
- Chạy `python3 main.py --help` xác nhận các cờ âm thanh mới `--audio`, `--audio-source`, `--scream-sensitivity`.
- Chạy thử nghiệm live/mock stream với `--audio` và xác nhận chương trình khởi chạy, phân tích và kết thúc sạch sẽ (clean exit).

---

[WAITING FOR PLAN APPROVAL]
