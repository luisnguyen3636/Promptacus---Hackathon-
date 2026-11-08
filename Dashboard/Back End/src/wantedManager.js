/**
 * Wanted Criminals Registry & Evidence Stamping Manager
 * Law enforcement wanted database with forensic proof stamping and audit ledger
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';
import { socDebugLogger } from './debugLogger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REGISTRY_FILE = path.resolve(__dirname, '../../../output/wanted_registry.json');

// Initial realistic seed records for urban surveillance
const INITIAL_WANTED_PERSONS = [
  {
    id: "WNT-2026-001",
    name: "Trần Văn Hùng",
    alias: "Hùng Báo",
    threatLevel: "CRITICAL",
    status: "RED_ALERT",
    charges: ["Cướp giật tài sản", "Tàng trữ vũ khí thô sơ nguy hiểm"],
    identificationFeatures: {
      height: "1m74",
      build: "Gầy, dáng cao",
      clothing: "Áo khoác gió đen có mũ trùm, quần jean xước",
      distinguishingMarks: "Vết sẹo dài 3cm ở đuôi mắt phải, hình xăm bọ cạp cổ tay trái"
    },
    avatarUrl: "/assets/wanted_01.jpg",
    lastSeenCameraId: "CAM_01",
    lastSeenLocation: "Cổng Chính Chu Văn An",
    lastSeenTimestamp: new Date(Date.now() - 3600000).toISOString(),
    evidenceStamps: [
      {
        stampId: "STAMP-20261108-01",
        incidentId: "INC-2026-0842",
        evidenceType: "KEYFRAME_SNAPSHOT",
        evidenceUrl: "/api/incidents/INC-2026-0842/snapshot",
        sha256Hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        stampedBy: "OP-VN-SOC-804",
        stampedAt: new Date(Date.now() - 3500000).toISOString(),
        notes: "Ảnh trích xuất từ camera phát hiện đối tượng áp sát giật túi xách nạn nhân"
      }
    ],
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "WNT-2026-002",
    name: "Nguyễn Minh Đức",
    alias: "Đức Đen",
    threatLevel: "HIGH",
    status: "WANTED",
    charges: ["Cố ý gây thương tích", "Gây rối trật tự công cộng"],
    identificationFeatures: {
      height: "1m68",
      build: "Đậm người, tóc húi cua",
      clothing: "Áo thun xám, nón kết đen in logo chữ trắng",
      distinguishingMarks: "Nốt ruồi lớn dưới cằm, sẹo bỏng mu bàn tay phải"
    },
    avatarUrl: "/assets/wanted_02.jpg",
    lastSeenCameraId: "CAM_02",
    lastSeenLocation: "Hành lang Đinh Bộ Lĩnh",
    lastSeenTimestamp: new Date(Date.now() - 7200000).toISOString(),
    evidenceStamps: [],
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "WNT-2026-003",
    name: "Lê Hoàng Phúc",
    alias: "Phúc Râu",
    threatLevel: "HIGH",
    status: "MONITORING",
    charges: ["Trộm cắp tài sản đột nhập", "Hủy hoại tài sản công cộng"],
    identificationFeatures: {
      height: "1m70",
      build: "Trung bình",
      clothing: "Áo sơ mi ca-rô xanh đen, đeo ba lô xám",
      distinguishingMarks: "Hình xăm rồng kín bắp tay phải"
    },
    avatarUrl: "/assets/wanted_03.jpg",
    lastSeenCameraId: "CAM_03",
    lastSeenLocation: "Ngã Ba Bến Xe Miền Đông",
    lastSeenTimestamp: new Date(Date.now() - 14400000).toISOString(),
    evidenceStamps: [],
    createdAt: new Date(Date.now() - 86400000 * 10).toISOString(),
    updatedAt: new Date().toISOString(),
  }
];

let wantedCache = null;

function loadRegistry() {
  if (wantedCache) return wantedCache;
  try {
    if (fs.existsSync(REGISTRY_FILE)) {
      const data = fs.readFileSync(REGISTRY_FILE, 'utf8');
      wantedCache = JSON.parse(data);
      return wantedCache;
    }
  } catch (err) {
    socDebugLogger.warn('WANTED_REGISTRY', `Could not read ${REGISTRY_FILE}, creating initial registry: ${err.message}`);
  }

  wantedCache = [...INITIAL_WANTED_PERSONS];
  saveRegistry();
  return wantedCache;
}

function saveRegistry() {
  try {
    const dir = path.dirname(REGISTRY_FILE);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(REGISTRY_FILE, JSON.stringify(wantedCache, null, 2), 'utf8');
  } catch (err) {
    socDebugLogger.error('WANTED_REGISTRY', `Failed writing registry file: ${err.message}`);
  }
}

export function getWantedList() {
  return loadRegistry();
}

export function getWantedPersonById(id) {
  const list = loadRegistry();
  return list.find(p => p.id === id) || null;
}

export function createWantedPerson(payload) {
  const list = loadRegistry();
  const newId = payload.id || `WNT-2026-${String(list.length + 1).padStart(3, '0')}`;
  
  const newPerson = {
    id: newId,
    name: payload.name || "Chưa rõ danh tính",
    alias: payload.alias || "",
    threatLevel: payload.threatLevel || "HIGH",
    status: payload.status || "WANTED",
    charges: Array.isArray(payload.charges) ? payload.charges : [payload.charges || "Hành vi nghi vấn nguy hiểm"],
    identificationFeatures: payload.identificationFeatures || {
      height: payload.height || "Chưa rõ",
      build: payload.build || "Chưa rõ",
      clothing: payload.clothing || "Chưa rõ",
      distinguishingMarks: payload.distinguishingMarks || "Không có",
    },
    avatarUrl: payload.avatarUrl || "/assets/wanted_placeholder.jpg",
    lastSeenCameraId: payload.lastSeenCameraId || "CAM_01",
    lastSeenLocation: payload.lastSeenLocation || "Khu vực Giám sát",
    lastSeenTimestamp: new Date().toISOString(),
    evidenceStamps: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  list.unshift(newPerson);
  saveRegistry();
  socDebugLogger.logWantedAction('CREATE', newId, 'OP-ADMIN', { name: newPerson.name });
  return newPerson;
}

export function updateWantedPerson(id, updates) {
  const list = loadRegistry();
  const idx = list.findIndex(p => p.id === id);
  if (idx === -1) return null;

  const current = list[idx];
  const updated = {
    ...current,
    ...updates,
    id: current.id, // Immutable ID
    updatedAt: new Date().toISOString(),
  };

  list[idx] = updated;
  saveRegistry();
  socDebugLogger.logWantedAction('UPDATE', id, updates.operatorId || 'OP-ADMIN', updates);
  return updated;
}

export function deleteWantedPerson(id) {
  const list = loadRegistry();
  const idx = list.findIndex(p => p.id === id);
  if (idx === -1) return false;

  list.splice(idx, 1);
  saveRegistry();
  socDebugLogger.logWantedAction('DELETE', id, 'OP-ADMIN');
  return true;
}

export function stampEvidenceToWanted(wantedId, evidenceData) {
  const list = loadRegistry();
  const person = list.find(p => p.id === wantedId);
  if (!person) return null;

  const stampId = `STAMP-${Date.now()}`;
  const sha256 = evidenceData.sha256Hash || crypto.createHash('sha256').update(JSON.stringify(evidenceData)).digest('hex');

  const stamp = {
    stampId,
    incidentId: evidenceData.incidentId || `INC-${Date.now()}`,
    evidenceType: evidenceData.evidenceType || "KEYFRAME_SNAPSHOT",
    evidenceUrl: evidenceData.evidenceUrl || "",
    sha256Hash: sha256,
    stampedBy: evidenceData.stampedBy || "OP-VN-SOC-804",
    stampedAt: new Date().toISOString(),
    notes: evidenceData.notes || "Bằng chứng pháp y đóng dấu trực tiếp từ SOC AI Stream",
  };

  if (!Array.isArray(person.evidenceStamps)) {
    person.evidenceStamps = [];
  }

  person.evidenceStamps.unshift(stamp);
  person.updatedAt = new Date().toISOString();
  saveRegistry();

  socDebugLogger.logWantedAction('STAMP_EVIDENCE', wantedId, stamp.stampedBy, { stampId, sha256 });
  return { person, stamp };
}
