import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';

/**
 * INITIAL STANDBY STATES — ZERO FAKE DATA
 * Dashboard strictly displays data received from the server and stored in Cloudflare KV.
 */

export const MOCK_OVERVIEW: ISocOverview = {
  threatLevel: 'LOW',
  threatScore: 0,
  status: 'SAFE',
  timestampUtc: new Date().toISOString(),
  metrics: {
    latencyMs: 0,
    downloadMbps: 0,
    uploadMbps: 0,
    activeNodes: 0,
    camerasOnline: 0,
    camerasTotal: 0,
    packetLossPercent: 0,
    openThreats: 0,
    criticalThreats: 0,
    nvrStoragePercent: 0,
    poeLoadWatts: 0
  }
};

export const MOCK_CAMERAS: ICameraDevice[] = [];

export const MOCK_INCIDENTS: IIncidentItem[] = [];
