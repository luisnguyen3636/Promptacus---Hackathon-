"""Single-file self-contained modern HTML5/CSS/JavaScript SOC Dashboard template."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>URBAN SAFETY AI-SOC — TỔNG HÀNH DINH GIÁM SÁT AN NINH THÔNG MINH</title>
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
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(8px);
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon { font-size: 24px; }
    .brand-title { font-size: 18px; font-weight: 700; letter-spacing: 0.5px; }
    .brand-subtitle { font-size: 11px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; }
    .header-status { display: flex; gap: 16px; align-items: center; }
    .status-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 9999px;
      font-size: 12px; font-weight: 600;
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
      padding: 20px;
      display: grid;
      grid-template-columns: 340px 1fr 380px;
      gap: 20px;
      flex: 1;
    }
    @media (max-width: 1280px) {
      main { grid-template-columns: 1fr; }
    }
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .panel-title {
      font-size: 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--accent-cyan);
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
    }

    /* Left Panel: Camera Feeds */
    .camera-list { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; max-height: calc(100vh - 180px); }
    .cam-card {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .cam-card:hover, .cam-card.active { border-color: var(--accent-cyan); box-shadow: 0 0 12px rgba(6, 182, 212, 0.25); }
    .cam-preview-box {
      width: 100%; height: 160px; background: #000;
      position: relative; overflow: hidden;
    }
    .cam-preview-img { width: 100%; height: 100%; object-fit: cover; }
    .cam-overlay-tag {
      position: absolute; top: 8px; left: 8px;
      background: rgba(0,0,0,0.7); padding: 2px 6px;
      border-radius: 4px; font-size: 11px; font-weight: 600;
    }
    .cam-info-bar { padding: 8px 10px; display: flex; justify-content: space-between; align-items: center; }
    .cam-name { font-size: 12px; font-weight: 600; }
    .cam-fps { font-size: 11px; color: var(--text-muted); }

    /* Center Panel: AI Reasoning & HITL */
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
      position: absolute; top: 12px; left: 12px; right: 12px;
      display: flex; justify-content: space-between; align-items: flex-start;
      pointer-events: none;
    }
    .threat-banner {
      background: rgba(15, 23, 42, 0.85);
      border: 2px solid var(--accent-green);
      backdrop-filter: blur(6px);
      padding: 8px 14px; border-radius: 8px;
      display: flex; flex-direction: column; gap: 4px;
    }
    .threat-banner.CRITICAL { border-color: var(--accent-red); background: rgba(239, 68, 68, 0.2); }
    .threat-banner.HIGH { border-color: var(--accent-yellow); background: rgba(245, 158, 11, 0.2); }
    .threat-banner.MEDIUM { border-color: var(--accent-cyan); }
    .threat-title { font-size: 12px; color: var(--text-muted); text-transform: uppercase; }
    .threat-val { font-size: 20px; font-weight: 800; }

    /* 5-Gate Audit Grid */
    .gate-grid {
      display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
    }
    @media (max-width: 900px) { .gate-grid { grid-template-columns: repeat(2, 1fr); } }
    .gate-card {
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 6px; padding: 8px;
      text-align: center;
    }
    .gate-card.passed { border-color: var(--accent-green); background: rgba(16, 185, 129, 0.1); }
    .gate-card.rejected { border-color: var(--accent-red); background: rgba(239, 68, 68, 0.1); }
    .gate-num { font-size: 10px; font-weight: 700; color: var(--text-muted); }
    .gate-status { font-size: 12px; font-weight: 800; margin-top: 2px; }
    .gate-desc { font-size: 10px; color: var(--text-muted); margin-top: 4px; line-height: 1.2; }

    /* Blind Spot Widget */
    .blind-spot-card {
      background: rgba(139, 92, 246, 0.08);
      border: 1px solid rgba(139, 92, 246, 0.3);
      border-radius: 8px; padding: 12px;
      display: flex; flex-direction: column; gap: 8px;
    }
    .bs-header { display: flex; justify-content: space-between; align-items: center; }
    .bs-title { font-size: 12px; font-weight: 700; color: var(--accent-purple); }
    .bs-preds { display: flex; flex-direction: column; gap: 6px; margin-top: 4px; }
    .pred-item {
      background: rgba(15, 23, 42, 0.6);
      border-left: 3px solid var(--accent-purple);
      padding: 6px 10px; border-radius: 4px;
      font-size: 12px; display: flex; justify-content: space-between;
    }

    /* HITL Action Controls */
    .hitl-section {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 8px; padding: 12px;
      display: flex; flex-direction: column; gap: 10px;
    }
    .hitl-status-row { display: flex; justify-content: space-between; align-items: center; }
    .hitl-state-badge {
      font-size: 12px; font-weight: 700; padding: 4px 8px; border-radius: 4px;
      background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow);
    }
    .btn-group { display: flex; gap: 8px; }
    .btn {
      flex: 1; padding: 10px; border-radius: 6px; border: none;
      font-size: 12px; font-weight: 700; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 6px;
      transition: all 0.2s;
    }
    .btn-confirm { background: var(--accent-red); color: #fff; }
    .btn-confirm:hover { background: #dc2626; box-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }
    .btn-downgrade { background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); border: 1px solid var(--accent-yellow); }
    .btn-downgrade:hover { background: rgba(245, 158, 11, 0.3); }
    .btn-dismiss { background: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
    .btn-dismiss:hover { background: rgba(16, 185, 129, 0.3); }

    /* Right Panel: Forensic Audit Logs */
    .log-stream {
      background: #030712;
      border: 1px solid var(--card-border);
      border-radius: 6px; padding: 10px;
      font-family: monospace; font-size: 11px;
      height: 380px; overflow-y: auto;
      display: flex; flex-direction: column; gap: 8px;
    }
    .log-entry { border-bottom: 1px dashed #1e293b; padding-bottom: 6px; }
    .log-time { color: var(--text-muted); }
    .log-action { color: var(--accent-cyan); font-weight: 700; }
    .log-hash { color: #64748b; font-size: 10px; word-break: break-all; margin-top: 2px; }

    /* Evidence Keeper Widget */
    .evidence-widget {
      background: rgba(6, 182, 212, 0.08);
      border: 1px solid rgba(6, 182, 212, 0.3);
      border-radius: 8px; padding: 12px;
      display: flex; flex-direction: column; gap: 8px;
    }
    .evidence-row { display: flex; justify-content: space-between; font-size: 12px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-icon">🛡️</span>
      <div>
        <div class="brand-title">URBAN SAFETY AI-SOC COMMAND CENTER</div>
        <div class="brand-subtitle">Nền Tảng Giám Sát & Điều Phối An Ninh Đô Thị Đa Camera</div>
      </div>
    </div>
    <div class="header-status">
      <span id="hitl-guard-badge" class="status-badge">
        <span class="pulse-dot"></span> HITL OPERATOR ACTIVE
      </span>
      <span id="evidence-chain-badge" class="status-badge" style="color: var(--accent-cyan); border-color: rgba(6,182,212,0.3); background: rgba(6,182,212,0.1);">
        🔒 MERKLE CHAIN VERIFIED
      </span>
      <div id="clock" style="font-family: monospace; font-size: 13px; font-weight: 600;">--:--:--</div>
    </div>
  </header>

  <main>
    <!-- LEFT: Camera List -->
    <section class="panel">
      <div class="panel-title">📹 Mạng Lưới Camera Đích Danh (<span id="cam-count">0</span>)</div>
      <div class="camera-list" id="camera-list">
        <div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 20px;">
          Đang dò tìm camera kết nối...
        </div>
      </div>
    </section>

    <!-- CENTER: Active Live Stream & AI Inference Reasoning -->
    <section class="panel" style="gap: 16px;">
      <div class="panel-title">
        <span>👁️ Luồng Video & Suy Luận AI Thời Gian Thực</span>
        <span id="active-cam-title" style="margin-left: auto; color: var(--text-muted); font-size: 12px;">CAM_01</span>
      </div>

      <div class="active-stream-container">
        <img id="main-stream" class="active-stream-img" src="/stream.mjpg" alt="Live Camera Feed">
        <div class="stream-overlay">
          <div class="threat-banner" id="threat-banner">
            <span class="threat-title">Mức Độ Đe Dọa</span>
            <span class="threat-val" id="threat-val">LOW</span>
          </div>
          <div style="background: rgba(0,0,0,0.7); padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">
            Điểm Rủi Ro: <span id="threat-score" style="color: var(--accent-cyan); font-weight: 800;">0.0</span> / 100
          </div>
        </div>
      </div>

      <!-- 5-Gate Falsification Matrix -->
      <div>
        <div style="font-size: 12px; font-weight: 700; margin-bottom: 6px; color: var(--text-muted);">
          BỘ LỌC KIỂM ĐỊNH PHÁP Y 5 CỔNG (5-GATE FALSIFICATION PROTOCOL)
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
            <div class="gate-desc" id="gate-2-desc">Conf cổ tay >= 0.60</div>
          </div>
          <div class="gate-card passed" id="gate-3">
            <div class="gate-num">CỔNG 3</div>
            <div class="gate-status">ĐỐI ỨNG 2 CHIỀU</div>
            <div class="gate-desc" id="gate-3-desc">Xác nhận phản ứng</div>
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

      <!-- Blind Spot Prediction Widget -->
      <div class="blind-spot-card">
        <div class="bs-header">
          <span class="bs-title">🔮 DỰ BÁO ĐÓN LÕNG VÙNG MÙ (BLIND-SPOT TRAJECTORY)</span>
          <span id="bs-zone" style="font-size: 11px; background: rgba(139,92,246,0.2); padding: 2px 6px; border-radius: 4px;">Zone: BZ_01</span>
        </div>
        <div style="font-size: 12px; color: var(--text-muted);">
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

      <!-- Operational HITL Controls -->
      <div class="hitl-section">
        <div class="hitl-status-row">
          <span style="font-size: 12px; font-weight: 700;">CHỐT CHẶN VẬN HÀNH VIÊN (CD-04 OPERATIONAL HITL)</span>
          <span class="hitl-state-badge" id="incident-state">AWAITING_OPERATOR_VERIFICATION</span>
        </div>
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

    <!-- RIGHT: Cryptographic Evidence Keeping & Forensic Logs -->
    <section class="panel">
      <div class="panel-title">🔒 Lưu Giữ Bằng Chứng & Kiểm Toán Pháp Y</div>

      <!-- Evidence Keeper Widget -->
      <div class="evidence-widget">
        <div style="font-size: 12px; font-weight: 700; color: var(--accent-cyan);">
          EVIDENCE INTEGRITY KEEPER (SHA-256 / HMAC)
        </div>
        <div class="evidence-row">
          <span style="color: var(--text-muted);">Mã Sự Cố Hiện Tại:</span>
          <b id="ev-event-id" style="font-family: monospace;">EVT_STANDBY</b>
        </div>
        <div class="evidence-row">
          <span style="color: var(--text-muted);">Keyframe SHA-256:</span>
          <span id="ev-sha256" style="font-family: monospace; font-size: 10px; color: #64748b;">Waiting...</span>
        </div>
        <div class="evidence-row">
          <span style="color: var(--text-muted);">Merkle Chain Hash:</span>
          <span id="ev-chain-hash" style="font-family: monospace; font-size: 10px; color: var(--accent-purple);">Waiting...</span>
        </div>
        <button class="btn" style="background: rgba(6,182,212,0.2); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); margin-top: 4px;" onclick="verifyLatestEvidence()">
          🔍 Kiểm Chứng Toàn Vẹn Mật Mã
        </button>
      </div>

      <!-- Live Event / Log Stream -->
      <div class="panel-title" style="margin-top: 10px;">📜 Nhật Ký Suy Luận Thời Gian Thực</div>
      <div class="log-stream" id="log-stream">
        <div class="log-entry">
          <span class="log-time">[BOOT]</span> Hệ thống AI-SOC khởi động thành công. Sẵn sàng tiếp nhận luồng camera.
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

    // Fetch camera list and state periodically
    async function updateDashboardState() {
      try {
        const resp = await fetch('/api/v1/dashboard/state');
        if (!resp.ok) return;
        const data = await resp.json();

        // Update Camera Count & List
        const cameras = data.cameras || [];
        document.getElementById('cam-count').innerText = cameras.length;
        renderCameraList(cameras);

        // Update Active Incident Telemetry if available
        if (data.latest_incident) {
          renderIncident(data.latest_incident);
        }

        // Update Log stream
        if (data.recent_logs) {
          renderLogs(data.recent_logs);
        }
      } catch (e) {
        console.debug('Dashboard sync error:', e);
      }
    }

    function renderCameraList(cameras) {
      const listEl = document.getElementById('camera-list');
      if (!cameras.length) {
        listEl.innerHTML = '<div style="color: #64748b; font-size: 12px; text-align: center; padding: 20px;">Chưa có client kết nối. Chạy: python client.py --camera-id CAM_01</div>';
        return;
      }
      listEl.innerHTML = cameras.map(c => `
        <div class="cam-card ${c.camera_id === activeCameraId ? 'active' : ''}" onclick="selectCamera('${c.camera_id}')">
          <div class="cam-preview-box">
            <img class="cam-preview-img" src="/api/v1/cameras/${c.camera_id}/snapshot?t=${Date.now()}" onerror="this.src='/static/cam_placeholder.png'" alt="${c.name}">
            <span class="cam-overlay-tag">${c.camera_id}</span>
          </div>
          <div class="cam-info-bar">
            <span class="cam-name">${c.name}</span>
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

      const banner = document.getElementById('threat-banner');
      banner.className = `threat-banner ${threat}`;
      document.getElementById('threat-val').innerText = threat;
      document.getElementById('threat-score').innerText = (score > 1.0 ? score : score * 100).toFixed(1);

      // Audit Gates
      const audit = inc.anti_false_positive_audit || {};
      updateGateCard('gate-1', audit.gate_1_ground_plane_depth, 'Độ sâu 3D');
      updateGateCard('gate-2', audit.gate_2_pose_jerk_filter, 'Khớp xương/Jerk');
      updateGateCard('gate-3', audit.gate_3_action_reaction_coupling, 'Đối ứng nạn nhân');
      updateGateCard('gate-4', audit.gate_4_posture_and_context, 'Tư thế/Bối cảnh');
      updateGateCard('gate-5', audit.gate_5_adversarial_benign_hypothesis, 'Giả thuyết vô tội');

      // Blind Spot
      const bs = inc.multi_camera_blind_spot_reasoning || {};
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
      const dir = inc.operator_dashboard_directives || {};
      if (dir.suggested_operator_focus) {
        document.getElementById('operator-focus').innerText = `👉 ${dir.suggested_operator_focus}`;
      }

      // Evidence fields
      if (inc.event_id) document.getElementById('ev-event-id').innerText = inc.event_id;
      if (inc.frame_sha256) document.getElementById('ev-sha256').innerText = inc.frame_sha256.substring(0, 24) + '...';
      if (inc.chain_hash) document.getElementById('ev-chain-hash').innerText = inc.chain_hash.substring(0, 24) + '...';
    }

    function updateGateCard(id, gateData, label) {
      const el = document.getElementById(id);
      if (!gateData) return;
      const status = (gateData.status || 'PASSED').toUpperCase();
      el.className = `gate-card ${status === 'REJECTED' ? 'rejected' : 'passed'}`;
      const descEl = document.getElementById(`${id}-desc`);
      if (descEl && gateData.detail) {
        descEl.innerText = gateData.detail.length > 32 ? gateData.detail.substring(0, 30) + '...' : gateData.detail;
      }
    }

    function renderLogs(logs) {
      const stream = document.getElementById('log-stream');
      stream.innerHTML = logs.map(l => `
        <div class="log-entry">
          <span class="log-time">[${l.time || ''}]</span>
          <span class="log-action">${l.camera_id || ''} - ${l.action || 'AI_INFERENCE'}</span>
          <div style="color: #cbd5e1; margin-top: 2px;">${l.summary || l.message || ''}</div>
          ${l.chain_hash ? `<div class="log-hash">Chain: ${l.chain_hash}</div>` : ''}
        </div>
      `).join('');
    }

    async function operatorAction(actionType) {
      try {
        const payload = {
          action: actionType,
          camera_id: activeCameraId,
          event_id: latestEventId,
          operator_id: "OPERATOR_CHIEF_01",
          timestamp: new Date().toISOString()
        };
        const resp = await fetch('/api/v1/operator/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        alert(`Đã ghi nhận quyết định Vận hành viên: [${actionType}]\\n${res.message || 'Thành công'}`);
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
          alert(`✅ XÁC THỰC BẰNG CHỨNG HỢP LỆ (INTEGRITY PASS)!\\nSHA-256: ${res.frame_sha256}\\nMerkle Chain Hash: ${res.chain_hash}\\n${res.integrity_message}`);
        } else {
          alert(`❌ PHÁT HIỆN BẰNG CHỨNG BỊ CAN THIỆP HOẶC THIẾU!\\n${res.integrity_message}`);
        }
      } catch (e) {
        alert('Lỗi kiểm tra toàn vẹn bằng chứng: ' + e);
      }
    }

    // Connect SSE for near real-time updates
    if (window.EventSource) {
      const sse = new EventSource('/api/v1/dashboard/events');
      sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'incident') {
            renderIncident(data.payload);
          } else if (data.type === 'state_update') {
            updateDashboardState();
          }
        } catch (e) {}
      };
      sse.onerror = () => { sse.close(); };
    }

    // Initial load and periodic fallback polling
    updateDashboardState();
    setInterval(updateDashboardState, 2000);
  </script>
</body>
</html>
"""
