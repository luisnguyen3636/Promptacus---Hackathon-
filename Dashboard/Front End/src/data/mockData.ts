import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';

export const MOCK_OVERVIEW: ISocOverview = {
  threatLevel: "LOW",
  threatScore: 0,
  status: "SAFE",
  timestampUtc: new Date().toISOString(),
  metrics: {
    latencyMs: 35,
    downloadMbps: 9744.0,
    uploadMbps: 4824.2,
    activeNodes: 43,
    camerasOnline: 4,
    camerasTotal: 4,
    packetLossPercent: 0.00,
    openThreats: 0,
    criticalThreats: 0,
    nvrStoragePercent: 78,
    poeLoadWatts: 410
  }
};

export const MOCK_CAMERAS: ICameraDevice[] = [
  {
    id: "cam_01",
    name: "Server Room",
    ip: "192.168.1.101",
    fps: 30,
    bitrateKbps: 1250,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_01/stream",
    snapshotUrl: "/api/v1/cameras/cam_01/snapshot",
    ptzEnabled: true,
    aiAlert: null,
    boundingBoxes: []
  },
  {
    id: "cam_02",
    name: "Main Gate",
    ip: "192.168.1.102",
    fps: 30,
    bitrateKbps: 1480,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_02/stream",
    snapshotUrl: "/api/v1/cameras/cam_02/snapshot",
    ptzEnabled: true,
    aiAlert: null,
    boundingBoxes: []
  },
  {
    id: "cam_03",
    name: "Corridor Central",
    ip: "192.168.1.103",
    fps: 30,
    bitrateKbps: 980,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_03/stream",
    snapshotUrl: "/api/v1/cameras/cam_03/snapshot",
    ptzEnabled: true,
    aiAlert: null,
    boundingBoxes: []
  },
  {
    id: "cam_04",
    name: "Perimeter Fence",
    ip: "192.168.1.104",
    fps: 30,
    bitrateKbps: 1120,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_04/stream",
    snapshotUrl: "/api/v1/cameras/cam_04/snapshot",
    ptzEnabled: true,
    aiAlert: null,
    boundingBoxes: []
  }
];

export const MOCK_INCIDENTS: IIncidentItem[] = [];

export const MOCK_TRAFFIC_SERIES = {
  labels: ["16:36", "16:37", "16:38", "16:39", "16:40", "16:41", "16:42", "16:43", "16:44", "16:45", "16:46", "16:47"],
  ingress: [8850, 9120, 9400, 9250, 9600, 9380, 9710, 9590, 9820, 9680, 9720, 9744.0],
  egress:  [4350, 4480, 4620, 4510, 4780, 4650, 4810, 4740, 4890, 4790, 4815, 4822.2]
};
