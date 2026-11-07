import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';

/**
 * INITIAL STANDBY STATES — ZERO FAKE DATA
 * Clean, live-ready telemetry states for real AI detection ingestion.
 */

export const MOCK_OVERVIEW: ISocOverview = {
  threatLevel: "LOW",
  threatScore: 0,
  status: "SAFE",
  timestampUtc: new Date().toUTCString(),
  metrics: {
    latencyMs: 15,
    downloadMbps: 9744.0,
    uploadMbps: 4824.2,
    activeNodes: 1,
    camerasOnline: 0,
    camerasTotal: 0,
    packetLossPercent: 0.00,
    openThreats: 0,
    criticalThreats: 0,
    nvrStoragePercent: 82,
    poeLoadWatts: 410
  }
};

export const MOCK_CAMERAS: ICameraDevice[] = [
  {
    id: "LAPTOP_01",
    name: "LAPTOP_01 - Live Surveillance Stream",
    ip: "127.0.0.1",
    fps: 30,
    bitrateKbps: 2048,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/LAPTOP_01/stream",
    directStreamUrl: "https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes: []
  }
];

export const MOCK_INCIDENTS: IIncidentItem[] = [];

export const MOCK_TRAFFIC_SERIES = {
  labels: ["16:42", "16:43", "16:44", "16:45", "16:46", "16:47"],
  ingress: [9250, 9380, 9590, 9680, 9720, 9744.0],
  egress:  [4510, 4650, 4740, 4790, 4815, 4822.2]
};
