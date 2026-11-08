/**
 * Multi-Camera Blind-Spot Reasoning & Cross-Camera Re-ID Manager
 * Tracks suspect trajectories across camera blind spots (>= 2 cameras) based on visual evidence
 */

import { socDebugLogger } from './debugLogger.js';

// Pre-configured active multi-camera blind-spot tracking sessions
let activeSessions = [
  {
    sessionId: "BS-SES-2026-01",
    status: "ACTIVE_TRACKING",
    sourceCameraId: "CAM_01",
    sourceCameraName: "Cổng Chính Chu Văn An",
    sourceKeyframeUrl: "/api/incidents/INC-2026-0842/snapshot",
    sourceExitTime: new Date(Date.now() - 120000).toISOString(),
    exitGate: "CỔNG_ĐÔNG_HẺM_12",
    blindSpotZone: "BS_ZONE_01 (Hẻm 12 Chu Văn An - 85m)",
    blindSpotDescription: "Hẻm cụt không có camera che khuất giữa Chu Văn An và Đinh Bộ Lĩnh",
    targetCandidates: [
      {
        targetCameraId: "CAM_02",
        targetCameraName: "Hành Lang Đinh Bộ Lĩnh",
        distanceMeters: 85,
        estimatedTransitSec: 18.5,
        softmaxProbability: 0.82,
        arrivalWindow: "15s - 25s",
      },
      {
        targetCameraId: "CAM_03",
        targetCameraName: "Bến Xe Miền Đông",
        distanceMeters: 240,
        estimatedTransitSec: 52.0,
        softmaxProbability: 0.18,
        arrivalWindow: "45s - 65s",
      }
    ],
    destinationCameraId: "CAM_02",
    destinationCameraName: "Hành Lang Đinh Bộ Lĩnh",
    destinationKeyframeUrl: "/api/incidents/INC-2026-0842/snapshot",
    destinationEntryTime: new Date(Date.now() - 100000).toISOString(),
    actualTransitSec: 20.0,
    reidSimilarityScore: 0.914,
    clothingMatch: {
      upperBody: "Áo khoác gió đen có mũ trùm (Tương đồng 94%)",
      lowerBody: "Quần jean xước màu tối (Tương đồng 89%)",
      accessories: "Nón bảo hiểm đỏ, giày thể thao trắng",
    },
    hiddenActionPredictions: ["EVIDENCE_DUMPING", "WEAPON_STASHING", "FOOT_PURSUIT_SPRINT"],
    operatorVerification: "CONFIRMED",
    verifiedBy: "OP-VN-SOC-804",
    verifiedAt: new Date(Date.now() - 90000).toISOString(),
  },
  {
    sessionId: "BS-SES-2026-02",
    status: "AWAITING_VERIFICATION",
    sourceCameraId: "CAM_02",
    sourceCameraName: "Hành Lang Đinh Bộ Lĩnh",
    sourceKeyframeUrl: "/api/incidents/INC-2026-0842/snapshot",
    sourceExitTime: new Date(Date.now() - 45000).toISOString(),
    exitGate: "LỐI_THOÁT_PHÍA_TÂY",
    blindSpotZone: "BS_ZONE_02 (Đường nội bộ Bãi đỗ xe)",
    blindSpotDescription: "Vùng khuất tán cây dọc đường nội bộ sang Ngã Ba Bến Xe",
    targetCandidates: [
      {
        targetCameraId: "CAM_03",
        targetCameraName: "Ngã Ba Bến Xe Miền Đông",
        distanceMeters: 130,
        estimatedTransitSec: 26.0,
        softmaxProbability: 0.76,
        arrivalWindow: "22s - 32s",
      },
      {
        targetCameraId: "CAM_04",
        targetCameraName: "Cổng Phụ Tầm Vu",
        distanceMeters: 190,
        estimatedTransitSec: 40.0,
        softmaxProbability: 0.24,
        arrivalWindow: "35s - 50s",
      }
    ],
    destinationCameraId: "CAM_03",
    destinationCameraName: "Ngã Ba Bến Xe Miền Đông",
    destinationKeyframeUrl: "/api/incidents/INC-2026-0842/snapshot",
    destinationEntryTime: new Date(Date.now() - 18000).toISOString(),
    actualTransitSec: 27.0,
    reidSimilarityScore: 0.887,
    clothingMatch: {
      upperBody: "Áo thun xám thể thao (Tương đồng 91%)",
      lowerBody: "Quần đen (Tương đồng 86%)",
      accessories: "Nón kết đen",
    },
    hiddenActionPredictions: ["CLOTHING_CHANGE", "FLEEING"],
    operatorVerification: "AWAITING_CONFIRMATION",
    verifiedBy: null,
    verifiedAt: null,
  }
];

export function getBlindSpotSessions() {
  return activeSessions;
}

export function getBlindSpotSessionById(sessionId) {
  return activeSessions.find(s => s.sessionId === sessionId) || null;
}

export function correlateCrossCameraSuspect(payload) {
  const {
    sourceCameraId,
    destinationCameraId,
    sourceKeyframeUrl,
    destinationKeyframeUrl,
    blindSpotZone,
    transitTimeSec,
  } = payload;

  const sessionId = `BS-SES-${Date.now()}`;
  // Simulated multimodal visual match score
  const simScore = 0.85 + Math.random() * 0.12;

  const newSession = {
    sessionId,
    status: "AWAITING_VERIFICATION",
    sourceCameraId: sourceCameraId || "CAM_01",
    sourceCameraName: `Camera ${sourceCameraId || 'CAM_01'}`,
    sourceKeyframeUrl: sourceKeyframeUrl || "/api/incidents/INC-2026-0842/snapshot",
    sourceExitTime: new Date(Date.now() - (transitTimeSec || 25) * 1000).toISOString(),
    exitGate: "PERIMETER_GATE",
    blindSpotZone: blindSpotZone || "BS_CORRIDOR_ZONE",
    blindSpotDescription: "Hành lang khuất tầm nhìn liên kết giữa 2 camera",
    targetCandidates: [
      {
        targetCameraId: destinationCameraId || "CAM_02",
        targetCameraName: `Camera ${destinationCameraId || 'CAM_02'}`,
        distanceMeters: 100,
        estimatedTransitSec: transitTimeSec || 25,
        softmaxProbability: 0.88,
        arrivalWindow: "20s - 30s",
      }
    ],
    destinationCameraId: destinationCameraId || "CAM_02",
    destinationCameraName: `Camera ${destinationCameraId || 'CAM_02'}`,
    destinationKeyframeUrl: destinationKeyframeUrl || "/api/incidents/INC-2026-0842/snapshot",
    destinationEntryTime: new Date().toISOString(),
    actualTransitSec: transitTimeSec || 25,
    reidSimilarityScore: parseFloat(simScore.toFixed(3)),
    clothingMatch: {
      upperBody: "So khớp màu áo & form dáng: 92%",
      lowerBody: "So khớp quần & giày: 88%",
      accessories: "Đặc điểm nhận diện tương đồng",
    },
    hiddenActionPredictions: ["FLEEING", "EVIDENCE_DUMPING"],
    operatorVerification: "AWAITING_CONFIRMATION",
    verifiedBy: null,
    verifiedAt: null,
  };

  activeSessions.unshift(newSession);
  if (activeSessions.length > 50) activeSessions.pop();

  socDebugLogger.logBlindSpotHandover(
    newSession.sourceCameraId,
    newSession.destinationCameraId,
    newSession.blindSpotZone,
    newSession.reidSimilarityScore
  );

  return newSession;
}

export function verifyBlindSpotLink(sessionId, decision, operatorId = "OP-VN-SOC-804") {
  const session = activeSessions.find(s => s.sessionId === sessionId);
  if (!session) return null;

  session.operatorVerification = decision === 'CONFIRM' ? 'CONFIRMED' : 'REJECTED';
  session.verifiedBy = operatorId;
  session.verifiedAt = new Date().toISOString();
  session.status = decision === 'CONFIRM' ? 'LINK_VERIFIED' : 'FALSE_MATCH';

  socDebugLogger.info('BLIND_SPOT', `Operator ${operatorId} verified session ${sessionId}: ${session.operatorVerification}`);
  return session;
}
