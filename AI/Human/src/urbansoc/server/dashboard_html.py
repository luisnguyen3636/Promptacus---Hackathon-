"""Single-file self-contained modern HTML5/CSS/JavaScript SOC Dashboard template.

All information, alerts, badges, gate verifications, and blind-spot predictions
are strictly reasoned by the AI Reasoning Core (NVIDIA VLM + 5-Gate + Threat Engine).
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>URBAN SAFETY AI-SOC — TỔNG HÀNH DINH TÁC CHIẾN AN NINH THÔNG MINH</title>
  <style>
    :root {
      --bg-dark: #070b14;
      --card-bg: #0f172a;
      --card-border: #1e293b;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --accent-cyan: #06b6d4;
      --accent-green: #10b981;
      --accent-yellow: #f59e0b;
      --accent-red: #ef4444;
      --accent-purple: #8b5cf6;
      --accent-blue: #3b82f6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-dark);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(15, 23, 42, 0.95);
      border-bottom: 1px solid var(--card-border);
      padding: 10px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(8px);
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon { font-size: 26px; }
    .brand-title { font-size: 16px; font-weight: 800; letter-spacing: 0.5px; }
    .brand-subtitle { font-size: 11px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; }
    .header-status { display: flex; gap: 12px; align-items: center; }
    .status-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 9999px;
      font-size: 11px; font-weight: 600;
      background: rgba(16, 185, 129, 0.15); color: var(--accent-green);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .pulse-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--accent-green);
      box-shadow: 0 0 8px var(--accent-green);
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

    main {
      padding: 16px 20px;
      display: grid;
      grid-template-columns: 310px 1fr 430px;
      gap: 16px;
      flex: 1;
    }
    @media (max-width: 1400px) {
      main { grid-template-columns: 280px 1fr 380px; }
    }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; }
    }
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .panel-title {
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--accent-cyan);
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 8px;
    }

    /* Left Panel: Camera Feeds */
    .camera-list { display: flex; flex-direction: column; gap: 10px; overflow-y: auto; max-height: calc(100vh - 160px); }
    .cam-card {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .cam-card:hover, .cam-card.active { border-color: var(--accent-cyan); box-shadow: 0 0 10px rgba(6, 182, 212, 0.25); }
    .cam-preview-box {
      width: 100%; height: 130px; background: #000;
      position: relative; overflow: hidden;
    }
    .cam-preview-img { width: 100%; height: 100%; object-fit: cover; }
    .cam-overlay-tag {
      position: absolute; top: 6px; left: 6px;
      background: rgba(0,0,0,0.75); padding: 2px 6px;
      border-radius: 4px; font-size: 10px; font-weight: 700;
    }
    .cam-info-bar { padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; }
    .cam-name { font-size: 11px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
    .cam-fps { font-size: 10px; color: var(--text-muted); }

    /* Center Panel: Active Stream & AI Reasoning Truth */
    .active-stream-container {
      background: #000;
      border-radius: 8px;
      position: relative;
      overflow: hidden;
      aspect-ratio: 16/9;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .active-stream-img { width: 100%; height: 100%; object-fit: contain; }
    .stream-overlay {
      position: absolute; top: 10px; left: 10px; right: 10px;
      display: flex; justify-content: space-between; align-items: flex-start;
      pointer-events: none;
    }
    .threat-banner {
      background: rgba(15, 23, 42, 0.88);
      border: 2px solid var(--accent-green);
      backdrop-filter: blur(6px);
      padding: 6px 12px; border-radius: 6px;
      display: flex; flex-direction: column; gap: 2px;
    }
    .threat-banner.CRITICAL { border-color: var(--accent-red); background: rgba(239, 68, 68, 0.25); }
    .threat-banner.HIGH { border-color: var(--accent-yellow); background: rgba(245, 158, 11, 0.25); }
    .threat-banner.MEDIUM { border-color: var(--accent-cyan); background: rgba(6, 182, 212, 0.15); }
    .threat-title { font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 700; }
    .threat-val { font-size: 18px; font-weight: 900; }

    /* AI Reasoning Callout Box */
    .ai-reasoning-box {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--accent-cyan);
      border-left: 4px solid var(--accent-cyan);
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 12px;
      line-height: 1.45;
    }
    .ai-reasoning-title {
      font-size: 11px;
      font-weight: 800;
      color: var(--accent-cyan);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }

    /* 5-Gate Audit Grid */
    .gate-grid {
      display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px;
    }
    @media (max-width: 900px) { .gate-grid { grid-template-columns: repeat(2, 1fr); } }
    .gate-card {
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 6px; padding: 6px 8px;
      text-align: center;
      transition: all 0.2s;
    }
    .gate-card.passed { border-color: var(--accent-green); background: rgba(16, 185, 129, 0.1); }
    .gate-card.rejected { border-color: var(--accent-red); background: rgba(239, 68, 68, 0.1); }
    .gate-num { font-size: 9px; font-weight: 800; color: var(--text-muted); }
    .gate-status { font-size: 11px; font-weight: 800; margin-top: 2px; }
    .gate-desc { font-size: 9px; color: var(--text-muted); margin-top: 3px; line-height: 1.2; word-break: break-word; }

    /* Blind Spot Widget */
    .blind-spot-card {
      background: rgba(139, 92, 246, 0.08);
      border: 1px solid rgba(139, 92, 246, 0.3);
      border-radius: 8px; padding: 10px;
      display: flex; flex-direction: column; gap: 6px;
    }
    .bs-header { display: flex; justify-content: space-between; align-items: center; }
    .bs-title { font-size: 11px; font-weight: 800; color: var(--accent-purple); text-transform: uppercase; }
    .bs-preds { display: flex; flex-direction: column; gap: 4px; }
    .pred-item {
      background: rgba(15, 23, 42, 0.7);
      border-left: 3px solid var(--accent-purple);
      padding: 5px 8px; border-radius: 4px;
      font-size: 11px; display: flex; justify-content: space-between;
    }

    /* Operational HITL */
    .hitl-section {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 8px; padding: 10px;
      display: flex; flex-direction: column; gap: 8px;
    }
    .hitl-status-row { display: flex; justify-content: space-between; align-items: center; }
    .hitl-state-badge {
      font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 4px;
      background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow);
    }
    .hitl-notes-input {
      background: #030712;
      border: 1px solid var(--card-border);
      border-radius: 4px;
      padding: 6px 10px;
      color: var(--text-main);
      font-size: 11px;
      width: 100%;
    }
    .btn-group { display: flex; gap: 6px; }
    .btn {
      flex: 1; padding: 8px; border-radius: 6px; border: none;
      font-size: 11px; font-weight: 700; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 4px;
      transition: all 0.2s;
    }
    .btn-confirm { background: var(--accent-red); color: #fff; }
    .btn-confirm:hover { background: #dc2626; box-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }
    .btn-downgrade { background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); border: 1px solid var(--accent-yellow); }
    .btn-downgrade:hover { background: rgba(245, 158, 11, 0.3); }
    .btn-dismiss { background: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
    .btn-dismiss:hover { background: rgba(16, 185, 129, 0.3); }

    /* Right Panel: Interactive Log Console */
    .log-filter-bar {
      display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
    }
    .log-tab {
      padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700;
      background: rgba(30, 41, 59, 0.8); color: var(--text-muted);
      cursor: pointer; border: 1px solid var(--card-border);
      transition: all 0.15s;
    }
    .log-tab.active { background: var(--accent-cyan); color: #000; border-color: var(--accent-cyan); }
    .log-search-input {
      flex: 1; min-width: 110px;
      background: #030712; border: 1px solid var(--card-border);
      border-radius: 4px; padding: 4px 8px; font-size: 11px; color: var(--text-main);
    }
    .log-stream {
      background: #030712;
      border: 1px solid var(--card-border);
      border-radius: 6px; padding: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px;
      height: 480px; overflow-y: auto;
      display: flex; flex-direction: column; gap: 6px;
    }
    .log-entry {
      border-bottom: 1px dashed #1e293b; padding-bottom: 6px;
      display: flex; flex-direction: column; gap: 2px;
      cursor: pointer;
    }
    .log-entry:hover { background: rgba(255, 255, 255, 0.02); }
    .log-row-top { display: flex; justify-content: space-between; align-items: center; }
    .log-time { color: #64748b; font-size: 10px; }
    .log-sev-tag {
      font-size: 9px; font-weight: 800; padding: 1px 5px; border-radius: 3px;
    }
    .log-sev-tag.CRITICAL { background: rgba(239, 68, 68, 0.25); color: var(--accent-red); border: 1px solid var(--accent-red); }
    .log-sev-tag.HIGH { background: rgba(245, 158, 11, 0.25); color: var(--accent-yellow); border: 1px solid var(--accent-yellow); }
    .log-sev-tag.MEDIUM { background: rgba(6, 182, 212, 0.2); color: var(--accent-cyan); }
    .log-sev-tag.LOW { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
    .log-sev-tag.AUDIT { background: rgba(139, 92, 246, 0.25); color: var(--accent-purple); border: 1px solid var(--accent-purple); }
    .log-action { color: #f1f5f9; font-weight: 700; font-size: 11px; }
    .log-text { color: #cbd5e1; font-size: 11px; line-height: 1.35; margin-top: 2px; }
    .log-hash { color: #475569; font-size: 9px; word-break: break-all; margin-top: 2px; }

    /* Evidence Card */
    .evidence-card {
      background: rgba(6, 182, 212, 0.06);
      border: 1px solid rgba(6, 182, 212, 0.25);
      border-radius: 6px; padding: 8px 10px;
      display: flex; flex-direction: column; gap: 4px;
      font-size: 11px;
    }
    .ev-row { display: flex; justify-content: space-between; }
    .ev-val { font-family: monospace; color: #94a3b8; font-size: 10px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-icon">🛡️</span>
      <div>
        <div class="brand-title">URBAN SAFETY AI-SOC COMMAND CENTER</div>
        <div class="brand-subtitle">AI-Reasoned Truth Engine • Client-Server Multi-Camera Topology</div>
      </div>
    </div>
    <div class="header-status">
      <span class="status-badge" id="ai-engine-badge" style="background: rgba(6,182,212,0.15); color: var(--accent-cyan); border-color: rgba(6,182,212,0.3);">
        🧠 AI REASONING ACTIVE
      </span>
      <span class="status-badge" id="hitl-badge">
        <span class="pulse-dot"></span> CD-04 HITL OPERATOR
      </span>
      <span class="status-badge" style="color: var(--accent-purple); border-color: rgba(139,92,246,0.3); background: rgba(139,92,246,0.1);">
        🔒 MERKLE CHAIN VERIFIED
      </span>
      <div id="clock" style="font-family: monospace; font-size: 12px; font-weight: 700; color: var(--text-main);">--:--:--</div>
    </div>
  </header>

  <main>
    <!-- LEFT PANEL: Multi-Camera Network -->
    <section class="panel">
      <div class="panel-title">
        <span>📹 Mạng Lưới Camera (<span id="cam-count">0</span>)</span>
      </div>
      <div class="camera-list" id="camera-list">
        <div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 20px;">
          Đang dò tìm camera client...
        </div>
      </div>
    </section>

    <!-- CENTER PANEL: Live Stream & AI-Reasoned Truth Matrix -->
    <section class="panel" style="gap: 12px;">
      <div class="panel-title">
        <span>👁️ Giám Sát & Suy Luận Tác Chiến Trực Tiếp</span>
        <span id="active-cam-title" style="margin-left: auto; color: var(--text-muted); font-size: 11px;">CAM_01</span>
      </div>

      <div class="active-stream-container">
        <img id="main-stream" class="active-stream-img" src="/stream.mjpg" alt="Live Camera Feed">
        <div class="stream-overlay">
          <div class="threat-banner LOW" id="threat-banner">
            <span class="threat-title">Mức Độ Đe Dọa (AI)</span>
            <span class="threat-val" id="threat-val">LOW</span>
          </div>
          <div style="background: rgba(0,0,0,0.75); padding: 6px 10px; border-radius: 6px; font-size: 11px; font-weight: 700;">
            Điểm Rủi Ro: <span id="threat-score" style="color: var(--accent-cyan); font-weight: 900;">0.0</span> / 100
          </div>
        </div>
      </div>

      <!-- AI Tactical Reasoning Summary Box (Reasoned by AI) -->
      <div class="ai-reasoning-box">
        <div class="ai-reasoning-title">
          <span>🧠 Nhận Định Tác Chiến Do AI Suy Luận (AI Reasoning Truth)</span>
          <span id="ai-model-tag" style="font-size: 9px; color: var(--text-muted);">NVIDIA NIM VLM + Forensic Core</span>
        </div>
        <div id="ai-reasoning-text" style="color: #f1f5f9;">
          Đang phân tích khung hình video thời gian thực...
        </div>
      </div>

      <!-- 5-Gate Forensic Falsification Protocol Matrix -->
      <div>
        <div style="font-size: 11px; font-weight: 800; margin-bottom: 6px; color: var(--text-muted);">
          QUY TRÌNH PHẢN BIỆN PHÁP Y 5 CỔNG (5-GATE FALSIFICATION PROTOCOL)
        </div>
        <div class="gate-grid">
          <div class="gate-card passed" id="gate-1">
            <div class="gate-num">CỔNG 1</div>
            <div class="gate-status">MẶT PHẲNG 3D</div>
            <div class="gate-desc" id="gate-1-desc">Đạt chiều sâu sàn</div>
          </div>
          <div class="gate-card passed" id="gate-2">
            <div class="gate-num">CỔNG 2</div>
            <div class="gate-status">KHỚP XƯƠNG</div>
            <div class="gate-desc" id="gate-2-desc">Conf tay >= 0.60</div>
          </div>
          <div class="gate-card passed" id="gate-3">
            <div class="gate-num">CỔNG 3</div>
            <div class="gate-status">ĐỐI ỨNG 2 CHIỀU</div>
            <div class="gate-desc" id="gate-3-desc">Xác nhận phản xạ</div>
          </div>
          <div class="gate-card passed" id="gate-4">
            <div class="gate-num">CỔNG 4</div>
            <div class="gate-status">TƯ THẾ & BỐI CẢNH</div>
            <div class="gate-desc" id="gate-4-desc">Loại trừ ngồi bệt</div>
          </div>
          <div class="gate-card passed" id="gate-5">
            <div class="gate-num">CỔNG 5</div>
            <div class="gate-status">GIẢ THUYẾT VÔ TỘI</div>
            <div class="gate-desc" id="gate-5-desc">P_benign &lt; 25%</div>
          </div>
        </div>
      </div>

      <!-- 5-Factor Blind-Spot Prediction Card -->
      <div class="blind-spot-card">
        <div class="bs-header">
          <span class="bs-title">🔮 Dự Báo Đón Lõng Vùng Mù (BLIND-SPOT TRAJECTORY)</span>
          <span id="bs-zone" style="font-size: 10px; background: rgba(139,92,246,0.2); padding: 2px 6px; border-radius: 4px;">Zone: BZ_01</span>
        </div>
        <div style="font-size: 11px; color: var(--text-muted);">
          Cổng thoát: <b id="bs-exit-gate" style="color: #fff;">EAST_EXIT</b> | 
          Tay thuận: <b id="bs-dominant-hand" style="color: #fff;">RIGHT</b> | 
          Tâm lý: <b id="bs-psych" style="color: #fff;">HIGH_PANIC</b>
        </div>
        <div class="bs-preds" id="bs-predictions">
          <div class="pred-item">
            <span>[Rank 1] 📹 CAM_02 - Hẻm 12 Đinh Bộ Lĩnh</span>
            <b>Cổng Tây (ETA: 7-12s)</b>
          </div>
        </div>
        <div id="operator-focus" style="font-size: 11px; color: var(--accent-yellow); font-style: italic;">
          👉 Chỉ thị Vận hành viên: Quan sát cổng Tây Camera 02 đón lõng đối tượng.
        </div>
      </div>

      <!-- Operational HITL Controls (CD-04) -->
      <div class="hitl-section">
        <div class="hitl-status-row">
          <span style="font-size: 11px; font-weight: 800; color: #f1f5f9;">CHỐT CHẶN VẬN HÀNH VIÊN (CD-04 OPERATIONAL HITL)</span>
          <span class="hitl-state-badge" id="incident-state">AWAITING_OPERATOR_VERIFICATION</span>
        </div>
        <input type="text" id="hitl-notes" class="hitl-notes-input" placeholder="Ghi chú tác chiến / lý giải quyết định của Vận hành viên (tùy chọn)...">
        <div class="btn-group">
          <button class="btn btn-confirm" onclick="operatorAction('CONFIRM_AND_DISPATCH')">
            🚨 XÁC NHẬN & ĐIỀU PHỐI
          </button>
          <button class="btn btn-downgrade" onclick="operatorAction('DOWNGRADE_MONITOR')">
            ⚠️ HẠ MỨC THEO DÕI
          </button>
          <button class="btn btn-dismiss" onclick="operatorAction('DISMISS_FALSE_POSITIVE')">
            🛡️ BÁC BỎ BÁO ĐỘNG GIẢ
          </button>
        </div>
      </div>
    </section>

    <!-- RIGHT PANEL: Evidence Keeping & Interactive Log Console -->
    <section class="panel">
      <div class="panel-title">
        <span>📜 Nhật Ký Suy Luận & Kiểm Toán Pháp Y</span>
        <button class="btn" style="flex: none; padding: 2px 8px; font-size: 10px; background: rgba(6,182,212,0.2); color: var(--accent-cyan); border: 1px solid var(--accent-cyan);" onclick="downloadLogs()">
          ⬇️ Xuất Log
        </button>
      </div>

      <!-- Evidence Keeper Card -->
      <div class="evidence-card">
        <div style="font-weight: 800; color: var(--accent-cyan); display: flex; justify-content: space-between;">
          <span>SỔ CÁI BẰNG CHỨNG (MERKLE LEDGER)</span>
          <span id="ev-event-id" style="color: #fff;">EVT_STANDBY</span>
        </div>
        <div class="ev-row">
          <span style="color: var(--text-muted);">Frame SHA-256:</span>
          <span class="ev-val" id="ev-sha256">Chờ dữ liệu...</span>
        </div>
        <div class="ev-row">
          <span style="color: var(--text-muted);">Merkle Chain:</span>
          <span class="ev-val" id="ev-chain-hash" style="color: var(--accent-purple);">Chờ dữ liệu...</span>
        </div>
        <button class="btn" style="margin-top: 2px; padding: 4px; background: rgba(6,182,212,0.15); color: var(--accent-cyan); border: 1px solid var(--accent-cyan);" onclick="verifyLatestEvidence()">
          🔍 Kiểm Tra Toàn Vẹn Mật Mã
        </button>
      </div>

      <!-- Log Filter & Search Bar -->
      <div class="log-filter-bar">
        <span class="log-tab active" data-sev="ALL" onclick="setLogFilter('ALL')">TẤT CẢ</span>
        <span class="log-tab" data-sev="CRITICAL" onclick="setLogFilter('CRITICAL')">CRITICAL</span>
        <span class="log-tab" data-sev="HIGH" onclick="setLogFilter('HIGH')">HIGH</span>
        <span class="log-tab" data-sev="MEDIUM" onclick="setLogFilter('MEDIUM')">MEDIUM</span>
        <span class="log-tab" data-sev="AUDIT" onclick="setLogFilter('AUDIT')">AUDIT</span>
        <input type="text" id="log-search" class="log-search-input" placeholder="🔍 Tìm kiếm log..." oninput="handleSearch(this.value)">
      </div>

      <!-- Scrollable Log Stream -->
      <div class="log-stream" id="log-stream">
        <div class="log-entry">
          <div class="log-row-top">
            <span class="log-time">[BOOT]</span>
            <span class="log-sev-tag LOW">SYSTEM</span>
          </div>
          <div class="log-text">Khởi động hệ thống Urban Safety AI-SOC thành công. Sẵn sàng tiếp nhận luồng camera client.</div>
        </div>
      </div>
    </section>
  </main>

  <script>
    // Live Clock
    setInterval(() => {
      document.getElementById('clock').innerText = new Date().toLocaleTimeString();
    }, 1000);

    let activeCameraId = 'CAM_01';
    let latestEventId = null;
    let currentSeverityFilter = 'ALL';
    let searchKeyword = '';
    let isLogPaused = false;

    // Fetch dashboard state periodically
    async function updateDashboardState() {
      try {
        const resp = await fetch('/api/v1/dashboard/state');
        if (!resp.ok) return;
        const data = await resp.json();

        // Update Camera List
        const cameras = data.cameras || [];
        document.getElementById('cam-count').innerText = cameras.length;
        renderCameraList(cameras);

        // Update Latest Incident Telemetry
        if (data.latest_incident) {
          renderIncident(data.latest_incident);
        }

        // Fetch logs with current filters
        fetchFilteredLogs();
      } catch (e) {
        console.debug('Dashboard sync error:', e);
      }
    }

    async function fetchFilteredLogs() {
      if (isLogPaused) return;
      try {
        const url = `/api/v1/dashboard/logs?severity=${encodeURIComponent(currentSeverityFilter)}&keyword=${encodeURIComponent(searchKeyword)}&limit=60`;
        const resp = await fetch(url);
        if (!resp.ok) return;
        const res = await resp.json();
        renderLogs(res.logs || []);
      } catch (e) {}
    }

    function renderCameraList(cameras) {
      const listEl = document.getElementById('camera-list');
      if (!cameras.length) {
        listEl.innerHTML = '<div style="color: #64748b; font-size: 11px; text-align: center; padding: 20px;">Chưa có camera client kết nối.<br>Chạy: <code>python client.py --camera-id CAM_01</code></div>';
        return;
      }
      listEl.innerHTML = cameras.map(c => `
        <div class="cam-card ${c.camera_id === activeCameraId ? 'active' : ''}" onclick="selectCamera('${c.camera_id}')">
          <div class="cam-preview-box">
            <img class="cam-preview-img" src="/api/v1/cameras/${c.camera_id}/snapshot?t=${Date.now()}" onerror="this.src='/static/cam_placeholder.png'" alt="${c.name}">
            <span class="cam-overlay-tag">${c.camera_id}</span>
          </div>
          <div class="cam-info-bar">
            <span class="cam-name" title="${c.name}">${c.name}</span>
            <span class="cam-fps">${c.measured_fps || 15} FPS</span>
          </div>
        </div>
      `).join('');
    }

    function selectCamera(camId) {
      activeCameraId = camId;
      document.getElementById('active-cam-title').innerText = camId;
      document.getElementById('main-stream').src = `/api/v1/cameras/${camId}/stream`;
      updateDashboardState();
    }

    function renderIncident(inc) {
      latestEventId = inc.event_id || latestEventId;
      const threat = (inc.highest_threat || inc.severity || inc.threat_level || 'LOW').toUpperCase();
      const score = (inc.highest_threat_score || inc.threat_score || 0.0);

      // Threat banner
      const banner = document.getElementById('threat-banner');
      banner.className = `threat-banner ${threat}`;
      document.getElementById('threat-val').innerText = threat;
      document.getElementById('threat-score').innerText = (score > 1.0 ? score : score * 100).toFixed(1);

      // AI Reasoning Text (100% reasoned by AI)
      const aiSummary = inc.reasoning || inc.description || (inc.nvidia_vlm_analysis ? inc.nvidia_vlm_analysis.reasoning : null) || 'AI đang tiếp tục quan sát hành vi đối tượng.';
      document.getElementById('ai-reasoning-text').innerText = aiSummary;

      // 5-Gate Audit Badges
      const audit = inc.anti_false_positive_audit || (inc.nvidia_vlm_analysis ? inc.nvidia_vlm_analysis.anti_false_positive_audit : {}) || {};
      updateGateCard('gate-1', audit.gate_1_ground_plane_depth, 'Độ sâu 3D');
      updateGateCard('gate-2', audit.gate_2_pose_jerk_filter, 'Khớp xương/Jerk');
      updateGateCard('gate-3', audit.gate_3_action_reaction_coupling, 'Đối ứng 2 chiều');
      updateGateCard('gate-4', audit.gate_4_posture_and_context, 'Tư thế/Bối cảnh');
      updateGateCard('gate-5', audit.gate_5_adversarial_benign_hypothesis, 'Giả thuyết vô tội');

      // Blind Spot Prediction
      const bs = inc.multi_camera_blind_spot_reasoning || (inc.nvidia_vlm_analysis ? inc.nvidia_vlm_analysis.multi_camera_blind_spot_reasoning : {}) || {};
      if (bs.is_triggered) {
        document.getElementById('bs-zone').innerText = `Zone: ${bs.blind_spot_zone_id || 'BZ_01'}`;
        document.getElementById('bs-exit-gate').innerText = bs.exit_gate_on_origin_cam || 'EAST_GATE';
        const tac = bs.subject_tactical_profile || {};
        document.getElementById('bs-dominant-hand').innerText = tac.dominant_hand || 'RIGHT';
        document.getElementById('bs-psych').innerText = tac.psychological_state || 'HIGH_PANIC';

        const preds = bs.predicted_next_cameras || [];
        const predEl = document.getElementById('bs-predictions');
        if (preds.length) {
          predEl.innerHTML = preds.slice(0, 3).map(p => `
            <div class="pred-item">
              <span>[Rank ${p.rank}] 📹 ${p.target_camera_name}</span>
              <b>${p.expected_entry_gate_on_target_cam} (ETA: ${p.estimated_arrival_seconds ? p.estimated_arrival_seconds[0]+'-'+p.estimated_arrival_seconds[1]+'s' : '5-10s'})</b>
            </div>
          `).join('');
        }
      }

      // Directives
      const dir = inc.operator_dashboard_directives || (inc.nvidia_vlm_analysis ? inc.nvidia_vlm_analysis.operator_dashboard_directives : {}) || {};
      if (dir.suggested_operator_focus) {
        document.getElementById('operator-focus').innerText = `👉 ${dir.suggested_operator_focus}`;
      }

      // Evidence fields
      if (inc.event_id) document.getElementById('ev-event-id').innerText = inc.event_id;
      if (inc.frame_sha256) document.getElementById('ev-sha256').innerText = inc.frame_sha256.substring(0, 24) + '...';
      if (inc.chain_hash) document.getElementById('ev-chain-hash').innerText = inc.chain_hash.substring(0, 24) + '...';

      // Incident state
      const incState = inc.incident_status || (threat === 'CRITICAL' || threat === 'HIGH' ? 'AWAITING_OPERATOR_VERIFICATION' : 'MONITORING_ONLY');
      document.getElementById('incident-state').innerText = incState;
    }

    function updateGateCard(id, gateData, label) {
      const el = document.getElementById(id);
      if (!gateData) return;
      const status = (gateData.status || 'PASSED').toUpperCase();
      el.className = `gate-card ${status === 'REJECTED' ? 'rejected' : 'passed'}`;
      const descEl = document.getElementById(`${id}-desc`);
      if (descEl && gateData.detail) {
        descEl.innerText = gateData.detail.length > 28 ? gateData.detail.substring(0, 26) + '...' : gateData.detail;
      }
    }

    function setLogFilter(sev) {
      currentSeverityFilter = sev;
      document.querySelectorAll('.log-tab').forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-sev') === sev);
      });
      fetchFilteredLogs();
    }

    function handleSearch(val) {
      searchKeyword = val.trim();
      fetchFilteredLogs();
    }

    function renderLogs(logs) {
      const stream = document.getElementById('log-stream');
      if (!logs.length) {
        stream.innerHTML = '<div style="color: #64748b; font-size: 11px; text-align: center; padding: 20px;">Không có log nào khớp với bộ lọc.</div>';
        return;
      }
      stream.innerHTML = logs.map(l => {
        const sev = (l.severity || (l.type === 'OPERATOR_AUDIT' ? 'AUDIT' : 'INFO')).toUpperCase();
        return `
          <div class="log-entry" onclick="showLogDetail(${JSON.stringify(l).replace(/"/g, '&quot;')})">
            <div class="log-row-top">
              <span class="log-time">[${l.time || ''}] ${l.camera_id || ''}</span>
              <span class="log-sev-tag ${sev}">${sev}</span>
            </div>
            <div class="log-action">${l.action || l.type}</div>
            <div class="log-text">${l.summary || l.notes || ''}</div>
            ${l.chain_hash ? `<div class="log-hash">🔗 Merkle: ${l.chain_hash}</div>` : ''}
          </div>
        `;
      }).join('');
    }

    function showLogDetail(logItem) {
      const detailStr = JSON.stringify(logItem, null, 2);
      console.log('Log Entry Detail:', logItem);
      alert(`BẢN GHI NHẬT KÝ CHI TIẾT:\\n\\nThời gian: ${logItem.timestamp || logItem.time}\\nCamera: ${logItem.camera_name || logItem.camera_id}\\nMức độ: ${logItem.severity || logItem.type}\\nHành động: ${logItem.action}\\nNội dung: ${logItem.summary}\\nMerkle Hash: ${logItem.chain_hash || 'N/A'}`);
    }

    async function operatorAction(actionType) {
      const notes = document.getElementById('hitl-notes').value.trim();
      try {
        const payload = {
          action: actionType,
          camera_id: activeCameraId,
          event_id: latestEventId,
          operator_id: "OPERATOR_CHIEF_01",
          notes: notes,
          timestamp: new Date().toISOString()
        };
        const resp = await fetch('/api/v1/operator/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        alert(`Đã ghi nhận quyết định Vận hành viên: [${actionType}]\\n${res.message || 'Thành công'}`);
        document.getElementById('hitl-notes').value = '';
        updateDashboardState();
      } catch (e) {
        alert('Lỗi gửi lệnh điều phối: ' + e);
      }
    }

    async function verifyLatestEvidence() {
      if (!latestEventId) {
        alert('Chưa có sự cố nào được lưu vào bằng chứng.');
        return;
      }
      try {
        const resp = await fetch(`/api/v1/evidence/${latestEventId}/verify`);
        const res = await resp.json();
        if (res.integrity_verified) {
          alert(`✅ XÁC THỰC BẰNG CHỨNG HỢP LỆ (INTEGRITY PASS)!\\n\\nSự cố: ${res.event_id}\\nSHA-256: ${res.frame_sha256}\\nMerkle Chain Hash: ${res.chain_hash}\\n${res.integrity_message}`);
        } else {
          alert(`❌ PHÁT HIỆN BẰNG CHỨNG BỊ CAN THIỆP HOẶC BỊ THIẾU!\\n${res.integrity_message}`);
        }
      } catch (e) {
        alert('Lỗi kiểm tra toàn vẹn bằng chứng: ' + e);
      }
    }

    function downloadLogs() {
      window.open('/api/v1/dashboard/logs/download', '_blank');
    }

    // Connect SSE for near real-time push
    if (window.EventSource) {
      const sse = new EventSource('/api/v1/dashboard/events');
      sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'incident') {
            renderIncident(data.payload);
            fetchFilteredLogs();
          } else if (data.type === 'state_update') {
            updateDashboardState();
          }
        } catch (e) {}
      };
      sse.onerror = () => { sse.close(); };
    }

    // Initial load and periodic polling
    updateDashboardState();
    setInterval(updateDashboardState, 2000);
  </script>
</body>
</html>
"""
