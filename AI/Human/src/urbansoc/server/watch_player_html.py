"""Single-file self-contained modern HTML5/CSS/JavaScript Watch Player template.

Provides a dedicated responsive in-browser live streaming viewer for Edge Camera streams
with live telemetry, threat level display, fullscreen mode, and instant snapshots.
"""

WATCH_PLAYER_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Urban Safety AI-SOC — Trực Tiếp Camera</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📹</text></svg>">
  <style>
    :root {
      --bg: #030712;
      --card-bg: #0f172a;
      --border: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent-red: #ef4444;
      --accent-green: #10b981;
      --accent-cyan: #06b6d4;
      --accent-yellow: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }
    header {
      background: rgba(15, 23, 42, 0.95);
      border-bottom: 1px solid var(--border);
      padding: 12px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      backdrop-filter: blur(8px);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .live-dot {
      width: 10px;
      height: 10px;
      background: var(--accent-red);
      border-radius: 50%;
      animation: pulse 1.5s infinite;
      box-shadow: 0 0 8px rgba(239, 68, 68, 0.8);
    }
    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
      100% { opacity: 1; transform: scale(1); }
    }
    .brand-text {
      font-weight: 800;
      font-size: 15px;
      letter-spacing: 0.5px;
    }
    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .btn {
      background: #1e293b;
      color: var(--text);
      border: 1px solid #334155;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn:hover {
      background: #334155;
      border-color: #475569;
    }
    .btn-primary {
      background: #0284c7;
      border-color: #38bdf8;
    }
    .btn-primary:hover {
      background: #0369a1;
    }
    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 16px;
      max-width: 1280px;
      width: 100%;
      margin: 0 auto;
    }
    .player-card {
      width: 100%;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
    }
    .video-viewport {
      position: relative;
      background: #000;
      width: 100%;
      aspect-ratio: 16/9;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .video-viewport img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .hud-overlay {
      position: absolute;
      top: 12px;
      left: 12px;
      right: 12px;
      display: flex;
      justify-content: space-between;
      pointer-events: none;
    }
    .hud-tag {
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(6px);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .threat-tag {
      background: rgba(16, 185, 129, 0.2);
      border-color: rgba(16, 185, 129, 0.5);
      color: var(--accent-green);
    }
    .threat-tag.MEDIUM {
      background: rgba(245, 158, 11, 0.2);
      border-color: rgba(245, 158, 11, 0.5);
      color: var(--accent-yellow);
    }
    .threat-tag.HIGH, .threat-tag.CRITICAL {
      background: rgba(239, 68, 68, 0.2);
      border-color: rgba(239, 68, 68, 0.5);
      color: var(--accent-red);
      animation: pulse 1s infinite;
    }
    .controls-bar {
      padding: 12px 16px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      background: #0b1120;
      border-top: 1px solid var(--border);
    }
    .telemetry {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 12px;
      color: var(--text-muted);
    }
    .telemetry strong {
      color: var(--text);
    }
    .telemetry span {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .action-group {
      display: flex;
      gap: 8px;
    }
    footer {
      text-align: center;
      padding: 12px;
      font-size: 11px;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
    }
    @media (max-width: 640px) {
      header { padding: 10px 14px; }
      .brand-text { font-size: 13px; }
      .btn { padding: 5px 8px; font-size: 11px; }
      .controls-bar { flex-direction: column; align-items: flex-start; }
      .action-group { width: 100%; justify-content: flex-end; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="live-dot"></div>
      <div class="brand-text">URBAN SAFETY AI-SOC <span style="color: var(--accent-cyan); font-weight: 500;">| LIVE STREAM</span></div>
    </div>
    <div class="header-actions">
      <a href="/dashboard" class="btn" title="Chuyển đến SOC Dashboard tổng">📊 Dashboard</a>
      <button class="btn btn-primary" onclick="toggleFullscreen()">⛶ Toàn màn hình</button>
    </div>
  </header>

  <main>
    <div class="player-card" id="playerCard">
      <div class="video-viewport" id="viewport">
        <img id="liveStream" src="/stream.mjpg?fps=15" alt="Đang kết nối camera stream..." decoding="async">
        <div class="hud-overlay">
          <div class="hud-tag" id="camTag">
            <span>📹</span>
            <span id="camIdText">CAMERA CLIENT</span>
          </div>
          <div class="hud-tag threat-tag" id="threatTag">
            <span>🛡️</span>
            <span id="threatText">THREAT: LOW</span>
          </div>
        </div>
      </div>

      <div class="controls-bar">
        <div class="telemetry">
          <span>📡 Trạng thái: <strong id="streamStatus" style="color: var(--accent-green);">TRỰC TIẾP</strong></span>
          <span>⚡ FPS: <strong id="fpsVal">--</strong></span>
          <span>👥 Đối tượng: <strong id="humanCount">0</strong></span>
          <span>🕒 Thời gian: <strong id="clockText">--:--:--</strong></span>
        </div>
        <div class="action-group">
          <button class="btn" onclick="captureSnapshot()">📸 Chụp ảnh</button>
          <button class="btn" onclick="reloadStream()">🔄 Tải lại</button>
        </div>
      </div>
    </div>
  </main>

  <footer>
    Hệ thống Giám sát An ninh Đô thị Thông minh — Urban Safety AI-SOC Live Gateway
  </footer>

  <script>
    const streamImg = document.getElementById('liveStream');
    const camIdText = document.getElementById('camIdText');
    const threatTag = document.getElementById('threatTag');
    const threatText = document.getElementById('threatText');
    const fpsVal = document.getElementById('fpsVal');
    const humanCount = document.getElementById('humanCount');
    const clockText = document.getElementById('clockText');
    const streamStatus = document.getElementById('streamStatus');

    function updateClock() {
      const now = new Date();
      clockText.textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    async function pollState() {
      try {
        const resp = await fetch('/api/v1/dashboard/state');
        if (resp.ok) {
          const data = await resp.json();
          if (data.cameras && data.cameras.length > 0) {
            const cam = data.cameras[0];
            camIdText.textContent = `${cam.camera_id} (${cam.name || 'Client'})`;
            fpsVal.textContent = cam.measured_fps ? cam.measured_fps.toFixed(1) : '--';
          }
          if (data.latest_incident) {
            const thr = (data.latest_incident.threat_level || 'LOW').toUpperCase();
            threatText.textContent = `THREAT: ${thr}`;
            threatTag.className = `hud-tag threat-tag ${thr}`;
            if (data.latest_incident.human_count !== undefined) {
              humanCount.textContent = data.latest_incident.human_count;
            }
          }
          streamStatus.textContent = 'TRỰC TIẾP';
          streamStatus.style.color = '#10b981';
        }
      } catch (e) {
        streamStatus.textContent = 'MẤT KẾT NỐI';
        streamStatus.style.color = '#ef4444';
      }
    }
    setInterval(pollState, 1500);
    pollState();

    // FPS mục tiêu cho stream MJPEG: 15 FPS đủ mượt và tiết kiệm băng thông qua tunnel.
    const STREAM_FPS = 15;
    let reconnectTimer = null;

    function reloadStream() {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      streamImg.src = `/stream.mjpg?fps=${STREAM_FPS}&t=${Date.now()}`;
    }

    streamImg.onerror = function() {
      streamStatus.textContent = 'ĐANG THỬ LẠI...';
      streamStatus.style.color = '#f59e0b';
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(reloadStream, 1500);
    };

    streamImg.onload = function() {
      streamStatus.textContent = 'TRỰC TIẾP';
      streamStatus.style.color = 'var(--accent-green)';
    };

    // Watchdog: nếu camera không gửi frame mới (tunnel rớt / stream đứng) thì tự nối lại.
    let stalledPolls = 0;
    setInterval(async () => {
      if (document.hidden) return;
      try {
        const resp = await fetch('/api/v1/dashboard/state');
        if (!resp.ok) return;
        const data = await resp.json();
        const cam = (data.cameras && data.cameras[0]) || null;
        const fps = cam && cam.measured_fps ? cam.measured_fps : 0;
        stalledPolls = fps > 0.05 ? 0 : stalledPolls + 1;
        if (stalledPolls >= 6) {
          stalledPolls = 0;
          streamImg.src = `/stream.mjpg?fps=${STREAM_FPS}&t=${Date.now()}`;
        }
      } catch (e) {
        /* bỏ qua, onerror sẽ xử lý */
      }
    }, 2000);

    function captureSnapshot() {
      const a = document.createElement('a');
      a.href = '/snapshot.jpg?t=' + Date.now();
      a.download = `snapshot_${Date.now()}.jpg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }

    function toggleFullscreen() {
      const elem = document.getElementById('viewport');
      if (!document.fullscreenElement) {
        if (elem.requestFullscreen) {
          elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
          elem.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        }
      }
    }
  </script>
</body>
</html>
"""
