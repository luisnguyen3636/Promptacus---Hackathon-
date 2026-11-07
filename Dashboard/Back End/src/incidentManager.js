/**
 * CYBERGUARD AI · SOC v2.1 — INCIDENT & EVIDENCE ROLLING BUFFER MANAGER
 */

let incidents = [
  {
    id: "inc_901",
    title: "Port Scan Detected",
    subTitle: "NETWORK / SYN Flood Signature",
    sourceIp: "45.33.32.256",
    category: "NETWORK",
    severity: "MEDIUM",
    timestamp: "16:07",
    cameraId: null,
    cameraSnapshots: null,
    playbackUrl: null,
    status: "PENDING_VERIFICATION",
    vlmAnalysis: "Phát hiện lưu lượng quét cổng TCP (Ports 22, 80, 443, 8080) tần suất 140 pkts/sec từ dải IP ngoài."
  },
  {
    id: "inc_902",
    title: "Server Room Intrusion",
    subTitle: "PHYSICAL_CAMERA / Zone B Restricted",
    sourceIp: "185.220.161.45",
    category: "PHYSICAL_CAMERA",
    severity: "HIGH",
    timestamp: "16:12",
    cameraId: "cam_01",
    cameraSnapshots: {
      preEventSnapshotUrl: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='56' height='32' viewBox='0 0 56 32'><rect width='56' height='32' fill='%230A0E14'/><text x='28' y='18' fill='%2364748B' font-size='7' font-family='monospace' text-anchor='middle'>PRE-16:11</text></svg>",
      eventPeakSnapshotUrl: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='56' height='32' viewBox='0 0 56 32'><rect width='56' height='32' fill='%230A0E14'/><rect x='16' y='6' width='22' height='22' fill='none' stroke='%23EF4444' stroke-width='1.5'/><text x='28' y='18' fill='%23EF4444' font-size='6' font-family='monospace' font-weight='bold' text-anchor='middle'>INTRUDER</text></svg>"
    },
    playbackUrl: "/evidence/inc_902_buffer.mp4",
    status: "PENDING_VERIFICATION",
    vlmAnalysis: "VLM Phân tích: Đối tượng mang balo sẫm màu, che mặt, lảng vảng 45s tại hành lang phòng máy chủ (Zone B) trước khi tiếp cận cửa tủ rack và có hành vi cạy khóa trái phép lúc 16:12:00 UTC."
  }
];

export function getRecentIncidents() {
  return incidents;
}

export function getIncidentPlayback(id) {
  const inc = incidents.find(i => i.id === id);
  if (!inc) return null;

  return {
    incidentId: inc.id,
    title: inc.title,
    cameraId: inc.cameraId,
    timestamp: inc.timestamp,
    bufferRange: {
      preEventSeconds: 10,
      postEventSeconds: 10,
      totalDurationSeconds: 20
    },
    vlmReasoning: inc.vlmAnalysis,
    visualEvidence: {
      preEventSnapshot: inc.cameraSnapshots?.preEventSnapshotUrl || null,
      eventPeakSnapshot: inc.cameraSnapshots?.eventPeakSnapshotUrl || null,
      streamPlaybackUrl: inc.playbackUrl || null
    },
    status: inc.status
  };
}

export function updateIncidentStatus(id, newStatus) {
  const inc = incidents.find(i => i.id === id);
  if (inc) {
    inc.status = newStatus;
  }
  return inc;
}
