/**
 * Cloudflare D1 Database Access Module for Urban Safety AI-SOC.
 * Manages SQL transactions, incident indexing, filtering, and immutable audit logs.
 */

import type { Env, IncidentRecord, OperatorVerifyRequest } from "./types.ts";

export class D1IncidentVault {
  private db: D1Database;

  constructor(env: Env) {
    this.db = env.DB;
  }

  public async insertIncident(incident: IncidentRecord): Promise<void> {
    const query = `
      INSERT INTO incidents (
        id, timestamp, camera_id, location_name, latitude, longitude,
        engine_behavior, engine_threat_score, ai_severity_score_10,
        false_positive_prob, is_false_positive, threat_verdict,
        subject_features, weapons_identified, victim_assessment,
        dispatch_recommendation, investigation_summary,
        evidence_clip_url, snapshot_url, operator_status
      ) VALUES (
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?,
        ?, ?,
        ?, ?, ?
      )
    `;

    await this.db
      .prepare(query)
      .bind(
        incident.id,
        incident.timestamp,
        incident.camera_id,
        incident.location_name,
        incident.latitude,
        incident.longitude,
        incident.engine_behavior,
        incident.engine_threat_score,
        incident.ai_severity_score_10,
        incident.false_positive_prob,
        incident.is_false_positive,
        incident.threat_verdict,
        incident.subject_features,
        incident.weapons_identified,
        incident.victim_assessment,
        incident.dispatch_recommendation,
        incident.investigation_summary,
        incident.evidence_clip_url || null,
        incident.snapshot_url || null,
        incident.operator_status
      )
      .run();

    await this.logAudit(incident.id, "INGESTED_AND_EVALUATED", "WORKERS_AI", {
      severity_score_10: incident.ai_severity_score_10,
      threat_verdict: incident.threat_verdict
    });
  }

  public async getIncidents(options: {
    camera_id?: string;
    operator_status?: string;
    min_severity?: number;
    limit?: number;
    offset?: number;
  }): Promise<IncidentRecord[]> {
    let sql = `SELECT * FROM incidents WHERE 1=1`;
    const params: any[] = [];

    if (options.camera_id) {
      sql += ` AND camera_id = ?`;
      params.push(options.camera_id);
    }

    if (options.operator_status) {
      sql += ` AND operator_status = ?`;
      params.push(options.operator_status);
    }

    if (options.min_severity !== undefined) {
      sql += ` AND ai_severity_score_10 >= ?`;
      params.push(options.min_severity);
    }

    sql += ` ORDER BY timestamp DESC LIMIT ? OFFSET ?`;
    params.push(options.limit || 20);
    params.push(options.offset || 0);

    const stmt = this.db.prepare(sql).bind(...params);
    const { results } = await stmt.all<IncidentRecord>();
    return results || [];
  }

  public async getIncidentById(id: string): Promise<IncidentRecord | null> {
    const query = `SELECT * FROM incidents WHERE id = ? LIMIT 1`;
    const result = await this.db.prepare(query).bind(id).first<IncidentRecord>();
    return result || null;
  }

  public async updateOperatorVerification(
    id: string,
    req: OperatorVerifyRequest
  ): Promise<IncidentRecord | null> {
    const nowIso = new Date().toISOString();
    let newStatus: "OPERATOR_CONFIRMED" | "DISMISSED_FALSE_POSITIVE" | "AWAITING_OPERATOR_VERIFICATION";

    if (req.action === "CONFIRM_AND_DISPATCH") {
      newStatus = "OPERATOR_CONFIRMED";
    } else if (req.action === "DISMISS_FALSE_POSITIVE") {
      newStatus = "DISMISSED_FALSE_POSITIVE";
    } else {
      newStatus = "AWAITING_OPERATOR_VERIFICATION";
    }

    const updateSql = `
      UPDATE incidents
      SET operator_status = ?,
          operator_id = ?,
          verified_at = ?,
          operator_notes = ?
      WHERE id = ?
    `;

    await this.db
      .prepare(updateSql)
      .bind(newStatus, req.operator_id, nowIso, req.operator_notes || null, id)
      .run();

    await this.logAudit(id, req.action, `OPERATOR:${req.operator_id}`, {
      status: newStatus,
      notes: req.operator_notes
    });

    return this.getIncidentById(id);
  }

  public async logAudit(incidentId: string, action: string, actor: string, details?: any): Promise<void> {
    try {
      const sql = `INSERT INTO audit_logs (incident_id, action, actor, details) VALUES (?, ?, ?, ?)`;
      await this.db
        .prepare(sql)
        .bind(incidentId, action, actor, details ? JSON.stringify(details) : null)
        .run();
    } catch (e) {
      console.warn("[D1IncidentVault] Audit log write warning:", e);
    }
  }
}
