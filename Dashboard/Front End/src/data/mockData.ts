import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';

export const MOCK_OVERVIEW: ISocOverview = {
  threatLevel: "LOW",
  threatScore: 12,
  status: "SAFE",
  timestampUtc: "Mar 23, 2026 · 16:47:26 UTC",
  metrics: {
    latencyMs: 42,
    downloadMbps: 9744.0,
    uploadMbps: 4824.2,
    activeNodes: 43,
    camerasOnline: 40,
    camerasTotal: 43,
    packetLossPercent: 0.00,
    openThreats: 4,
    criticalThreats: 1,
    nvrStoragePercent: 82,
    poeLoadWatts: 410
  }
};

export const MOCK_CAMERAS: ICameraDevice[] = [
  {
    id: "cam_01",
    name: "Server Room",
    ip: "163.16.8.259",
    fps: 30,
    bitrateKbps: 37,
    status: "ONLINE",
    streamUrl: "",
    ptzEnabled: true,
    boundingBoxes: [
      {
        id: "box_01",
        label: "PERSON 98%",
        subLabel: "INTRUSION",
        severity: "CRITICAL",
        x: 0.35,
        y: 0.22,
        w: 0.22,
        h: 0.65
      }
    ]
  },
  {
    id: "cam_02",
    name: "Main Gate",
    ip: "185.220.161.45",
    fps: 30,
    bitrateKbps: 47,
    status: "ONLINE",
    streamUrl: "",
    ptzEnabled: true,
    boundingBoxes: [
      {
        id: "box_02",
        label: "VEHICLE 94%",
        subLabel: "MONITORED",
        severity: "NORMAL",
        x: 0.15,
        y: 0.40,
        w: 0.35,
        h: 0.45
      }
    ]
  },
  {
    id: "cam_03",
    name: "Server Room",
    ip: "192.168.16.121",
    fps: 30,
    bitrateKbps: 35,
    status: "ONLINE",
    streamUrl: "",
    ptzEnabled: true,
    boundingBoxes: []
  },
  {
    id: "cam_04",
    name: "Main Gate",
    ip: "185.220.161.45",
    fps: 30,
    bitrateKbps: 37,
    status: "ONLINE",
    streamUrl: "",
    ptzEnabled: true,
    boundingBoxes: [
      {
        id: "box_04",
        label: "PERSON 91%",
        subLabel: "LOITERING",
        severity: "HIGH",
        x: 0.55,
        y: 0.28,
        w: 0.18,
        h: 0.58
      }
    ]
  }
];

export const MOCK_INCIDENTS: IIncidentItem[] = [
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
    playbackUrl: "mock://recordings/inc_902_rolling_buffer.mp4",
    status: "PENDING_VERIFICATION",
    vlmAnalysis: "VLM Phân tích: Đối tượng mang balo sẫm màu, che mặt, lảng vảng 45s tại hành lang phòng máy chủ (Zone B) trước khi tiếp cận cửa tủ rack và có hành vi cạy khóa trái phép lúc 16:12:00 UTC."
  }
];

export const MOCK_TRAFFIC_SERIES = {
  labels: ["16:36", "16:37", "16:38", "16:39", "16:40", "16:41", "16:42", "16:43", "16:44", "16:45", "16:46", "16:47"],
  ingress: [8850, 9120, 9400, 9250, 9600, 9380, 9710, 9590, 9820, 9680, 9720, 9744.0],
  egress:  [4350, 4480, 4620, 4510, 4780, 4650, 4810, 4740, 4890, 4790, 4815, 4822.2]
};
