-- =============================================================================
-- Cloudflare D1 SQL Schema: Urban Safety AI-SOC Incident & Audit Vault
-- =============================================================================

-- Table: incidents
-- Stores AI-evaluated incident records with rich forensic metadata & HITL state
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,                       -- UUID: INC_YYYYMMDD_HHMMSS_XXXXXX
    timestamp TEXT NOT NULL,                   -- ISO-8601: YYYY-MM-DDTHH:MM:SS.mmmZ
    camera_id TEXT NOT NULL,                   -- cam_01, cam_gate_a,...
    location_name TEXT NOT NULL,               -- e.g. "Khu vực Cổng A - ĐH SGU"
    latitude REAL NOT NULL,                    -- GPS Latitude
    longitude REAL NOT NULL,                   -- GPS Longitude
    engine_behavior TEXT NOT NULL,             -- Detected behavior from local Engine
    engine_threat_score REAL NOT NULL,         -- Threat score 0.00 to 1.00 from local Engine
    ai_severity_score_10 REAL NOT NULL,        -- Evaluated severity on 10-point scale (1.0 - 10.0)
    false_positive_prob REAL NOT NULL,         -- False positive probability (0.00 - 1.00)
    is_false_positive INTEGER NOT NULL,        -- 0 = False, 1 = True
    threat_verdict TEXT NOT NULL,              -- CONFIRMED_THREAT, CRITICAL_EMERGENCY, etc.
    subject_features TEXT NOT NULL,            -- JSON: posture, build, concealment, intent
    weapons_identified TEXT NOT NULL,          -- JSON: weapon type, confidence, description
    victim_assessment TEXT NOT NULL,           -- JSON: victim condition, bystander count
    dispatch_recommendation TEXT NOT NULL,     -- JSON: priority, units (POLICE/AMBULANCE/...), notes
    investigation_summary TEXT NOT NULL,       -- Forensic investigation reasoning text
    evidence_clip_url TEXT,                    -- URL to evidence MP4 clip in R2/Storage
    snapshot_url TEXT,                         -- URL to annotated snapshot in R2/Storage
    operator_status TEXT NOT NULL DEFAULT 'AWAITING_OPERATOR_VERIFICATION', -- Operational HITL gate
    operator_id TEXT,                          -- Human operator ID who verified
    verified_at TEXT,                          -- Verification ISO timestamp
    operator_notes TEXT,                       -- Notes entered by Human Operator
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(operator_status);
CREATE INDEX IF NOT EXISTS idx_incidents_camera ON incidents(camera_id);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(ai_severity_score_10 DESC);

-- Table: audit_logs
-- Immutable SOC audit log recording all system events and operator decisions
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    action TEXT NOT NULL,                      -- INGESTED | AI_EVALUATED | OPERATOR_CONFIRMED | DISMISSED
    actor TEXT NOT NULL,                       -- SYSTEM | WORKERS_AI | OPERATOR:<id>
    details TEXT,                              -- JSON formatted metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_logs(incident_id);
