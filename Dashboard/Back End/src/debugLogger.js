/**
 * SOC Backend Unified Debug & Audit Logger
 * Standardized logging with file sinks and console formatting
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const LOG_DIR = path.resolve(__dirname, '../../../output/logs');
try {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
} catch {
  // Ignore
}

const BACKEND_LOG_FILE = path.join(LOG_DIR, 'soc_backend_debug.log');

function getTimestamp() {
  return new Date().toISOString();
}

function writeToFile(line) {
  try {
    fs.appendFileSync(BACKEND_LOG_FILE, line + '\n', 'utf8');
  } catch {
    // Ignore write failure in emergency
  }
}

export const socDebugLogger = {
  debug(module, message, extra = null) {
    const ts = getTimestamp();
    const extraStr = extra ? ` | ${JSON.stringify(extra)}` : '';
    const line = `[${ts}] [DEBUG] [${module}] ${message}${extraStr}`;
    writeToFile(line);
    console.log(`\x1b[36m[${ts}] [DEBUG] [${module}]\x1b[0m ${message}`);
  },

  info(module, message, extra = null) {
    const ts = getTimestamp();
    const extraStr = extra ? ` | ${JSON.stringify(extra)}` : '';
    const line = `[${ts}] [INFO ] [${module}] ${message}${extraStr}`;
    writeToFile(line);
    console.log(`\x1b[32m[${ts}] [INFO ] [${module}]\x1b[0m ${message}`);
  },

  warn(module, message, extra = null) {
    const ts = getTimestamp();
    const extraStr = extra ? ` | ${JSON.stringify(extra)}` : '';
    const line = `[${ts}] [WARN ] [${module}] ${message}${extraStr}`;
    writeToFile(line);
    console.warn(`\x1b[33m[${ts}] [WARN ] [${module}]\x1b[0m ${message}`);
  },

  error(module, message, extra = null) {
    const ts = getTimestamp();
    const extraStr = extra ? ` | ${JSON.stringify(extra)}` : '';
    const line = `[${ts}] [ERROR] [${module}] ${message}${extraStr}`;
    writeToFile(line);
    console.error(`\x1b[31m[${ts}] [ERROR] [${module}]\x1b[0m ${message}`);
  },

  logCameraStream(cameraId, fps, bytesReceived) {
    this.debug('CAMERA_STREAM', `Stream frame ingested for ${cameraId}: ${bytesReceived} bytes, FPS: ${fps}`);
  },

  logWantedAction(action, wantedId, operatorId, details = null) {
    this.info('WANTED_REGISTRY', `Operator ${operatorId} performed ${action} on Wanted ID: ${wantedId}`, details);
  },

  logBlindSpotHandover(sourceCam, destCam, zoneId, simScore) {
    this.info('BLIND_SPOT', `Blind spot tracking link: ${sourceCam} -> [${zoneId}] -> ${destCam} (ReID Sim: ${(simScore * 100).toFixed(1)}%)`);
  },
};
