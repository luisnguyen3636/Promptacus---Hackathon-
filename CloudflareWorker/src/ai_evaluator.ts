/**
 * Workers AI Forensic Evaluator Module.
 * Executes structured analysis via Cloudflare Workers AI LLMs.
 * Evaluates severity on a 1-10 scale, calculates false-positive probability,
 * extracts subject traits, weapon indicators, and tactical recommendations.
 */

import { Env, EvaluationRequestPayload, AIEvaluationOutput } from "./types";

export class WorkersAIEvaluator {
  private env: Env;

  constructor(env: Env) {
    this.env = env;
  }

  public async evaluate(payload: EvaluationRequestPayload): Promise<AIEvaluationOutput> {
    const model = this.env.DEFAULT_AI_MODEL || "@cf/meta/llama-3.2-11b-vision-instruct";

    const systemPrompt = `You are a certified SOC Forensic AI Investigator operating in an Urban Safety Security Operations Center.
Your task is to analyze the computer vision telemetry from surveillance cameras and perform an authoritative evaluation.
You must return ONLY a single valid JSON object strictly adhering to the schema below without any conversational text or markdown codeblocks:
{
  "severity_score_10": <number between 1.0 and 10.0, step 0.1>,
  "false_positive_probability": <number between 0.00 and 1.00>,
  "is_false_positive": <boolean: true if false_positive_probability >= 0.70, else false>,
  "threat_verdict": <"CONFIRMED_THREAT" | "BENIGN_ACTIVITY" | "SUSPICIOUS_MONITOR" | "CRITICAL_EMERGENCY">,
  "subject_features": {
    "posture_assessment": <string describing physical stance and aggression>,
    "suspicious_concealment": <boolean>,
    "movement_intent": <string describing motion direction and intent>,
    "estimated_threat_actor_count": <integer>
  },
  "weapons_identified": {
    "has_weapon_indicator": <boolean>,
    "weapon_type": <"NONE" | "BLUNT_OBJECT" | "EDGED_WEAPON" | "CONCEALED_FIREARM" | "IMPROVISED_WEAPON">,
    "weapon_confidence": <number between 0.0 and 1.0>,
    "description": <string>
  },
  "victim_assessment": {
    "has_victim_present": <boolean>,
    "victim_track_id": <optional number>,
    "victim_condition": <"NONE" | "UNDER_ATTACK" | "FALLEN_UNRESPONSIVE" | "FLEEING_INJURED">,
    "bystander_count": <integer>
  },
  "dispatch_recommendation": {
    "priority": <"ROUTINE" | "URGENT" | "IMMEDIATE_RESPONSE" | "DISMISS">,
    "recommended_units": <array of strings: "POLICE" | "AMBULANCE" | "FIRE_RESCUE" | "SECURITY_GUARD">,
    "action_notes": <string tactical directive for operator>
  },
  "investigation_summary": <string forensic reasoning and evidence summary>
}`;

    const userPrompt = `INCIDENT TELEMETRY PAYLOAD:
- Camera ID: ${payload.camera_id} (${payload.location_name})
- GPS Coordinates: Latitude ${payload.latitude}, Longitude ${payload.longitude}
- Timestamp: ${payload.timestamp}
- Detected Behavior: ${payload.engine_behavior} (Category: ${payload.engine_category})
- Local Threat Level: ${payload.engine_threat_level} (Score: ${payload.engine_threat_score})
- Subject Track ID: #${payload.primary_subject_id} (Interacting with: ${payload.interacting_subject_ids?.join(", ") || "None"})
- Biomechanical Telemetry:
  * Torso Spine Angle: ${payload.telemetry.spine_angle_deg}° from vertical
  * Body Aspect Ratio (H/W): ${payload.telemetry.aspect_ratio}
  * Normalized Movement Speed: ${payload.telemetry.velocity_norm} body-heights/sec
  * Wrist Kinetic Energy: ${payload.telemetry.wrist_kinetic_energy} px²/s²
  * Subject Dwell Time: ${payload.telemetry.dwell_time_seconds}s (State Dwell: ${payload.telemetry.state_dwell_seconds}s)
- Engine Diagnostic Reasoning: "${payload.diagnostic_reasoning}"

Carefully analyze whether this kinematic pattern represents genuine violent crime, medical emergency, or benign false alarms (e.g. martial arts training, greeting gestures, tying shoelaces, hurried walking). Return the required JSON.`;

    try {
      if (!this.env.AI) {
        console.warn("[WorkersAIEvaluator] env.AI binding not available. Running fallback evaluator.");
        return this.fallbackEvaluate(payload);
      }

      const response: any = await this.env.AI.run(model, {
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.1,
        max_tokens: 1024
      });

      const responseText = response?.response || response?.content || JSON.stringify(response);
      return this.parseAndValidateResponse(responseText, payload);
    } catch (error) {
      console.error("[WorkersAIEvaluator] Workers AI invocation error:", error);
      // Fallback resilience
      return this.fallbackEvaluate(payload);
    }
  }

  private parseAndValidateResponse(text: string, payload: EvaluationRequestPayload): AIEvaluationOutput {
    try {
      // Find JSON block if surrounded by markdown codeblocks or leading prose
      let cleaned = text.trim();
      const jsonStart = cleaned.indexOf("{");
      const jsonEnd = cleaned.lastIndexOf("}");
      if (jsonStart !== -1 && jsonEnd !== -1) {
        cleaned = cleaned.substring(jsonStart, jsonEnd + 1);
      }

      const parsed = JSON.parse(cleaned);

      // Validate and clamp severity_score_10
      let score10 = Number(parsed.severity_score_10);
      if (isNaN(score10) || score10 < 1.0) score10 = 1.0;
      if (score10 > 10.0) score10 = 10.0;
      score10 = Math.round(score10 * 10) / 10;

      // Validate false_positive_probability
      let fpProb = Number(parsed.false_positive_probability);
      if (isNaN(fpProb) || fpProb < 0.0) fpProb = 0.0;
      if (fpProb > 1.0) fpProb = 1.0;

      return {
        severity_score_10: score10,
        false_positive_probability: Math.round(fpProb * 100) / 100,
        is_false_positive: Boolean(parsed.is_false_positive ?? (fpProb >= 0.70)),
        threat_verdict: parsed.threat_verdict || (score10 >= 8.5 ? "CRITICAL_EMERGENCY" : "CONFIRMED_THREAT"),
        subject_features: {
          posture_assessment: parsed.subject_features?.posture_assessment || "Observed physical posture",
          suspicious_concealment: Boolean(parsed.subject_features?.suspicious_concealment),
          movement_intent: parsed.subject_features?.movement_intent || "Active presence",
          estimated_threat_actor_count: Math.max(1, Number(parsed.subject_features?.estimated_threat_actor_count || 1))
        },
        weapons_identified: {
          has_weapon_indicator: Boolean(parsed.weapons_identified?.has_weapon_indicator),
          weapon_type: parsed.weapons_identified?.weapon_type || "NONE",
          weapon_confidence: Number(parsed.weapons_identified?.weapon_confidence || 0.0),
          description: parsed.weapons_identified?.description || "No overt weapon confirmed"
        },
        victim_assessment: {
          has_victim_present: Boolean(parsed.victim_assessment?.has_victim_present),
          victim_track_id: parsed.victim_assessment?.victim_track_id,
          victim_condition: parsed.victim_assessment?.victim_condition || "NONE",
          bystander_count: Math.max(0, Number(parsed.victim_assessment?.bystander_count || 0))
        },
        dispatch_recommendation: {
          priority: parsed.dispatch_recommendation?.priority || (score10 >= 8.0 ? "IMMEDIATE_RESPONSE" : "ROUTINE"),
          recommended_units: parsed.dispatch_recommendation?.recommended_units || ["SECURITY_GUARD"],
          action_notes: parsed.dispatch_recommendation?.action_notes || "Maintain camera tracking"
        },
        investigation_summary: parsed.investigation_summary || "Automated Workers AI forensic assessment."
      };
    } catch (e) {
      console.warn("[WorkersAIEvaluator] JSON parse failed, falling back to heuristic evaluation:", e);
      return this.fallbackEvaluate(payload);
    }
  }

  public fallbackEvaluate(payload: EvaluationRequestPayload): AIEvaluationOutput {
    // Biomechanical forensic fallback calculation
    const isFight = payload.engine_behavior.includes("FIGHT") || payload.engine_behavior.includes("GRAPPLE");
    const isFall = payload.engine_behavior.includes("FALLEN");
    const isFlee = payload.engine_behavior.includes("FLEE") || payload.engine_behavior.includes("RUN");
    const isLoiter = payload.engine_behavior.includes("LOITER");
    const isConceal = payload.engine_behavior.includes("CONCEAL");

    let score10 = 2.0;
    let fpProb = 0.20;
    let verdict: "CONFIRMED_THREAT" | "BENIGN_ACTIVITY" | "SUSPICIOUS_MONITOR" | "CRITICAL_EMERGENCY" = "BENIGN_ACTIVITY";
    let priority: "ROUTINE" | "URGENT" | "IMMEDIATE_RESPONSE" | "DISMISS" = "ROUTINE";
    let units: ("POLICE" | "AMBULANCE" | "FIRE_RESCUE" | "SECURITY_GUARD")[] = ["SECURITY_GUARD"];
    let weaponType: "NONE" | "BLUNT_OBJECT" | "EDGED_WEAPON" | "CONCEALED_FIREARM" | "IMPROVISED_WEAPON" = "NONE";

    if (isFight) {
      score10 = Math.min(10.0, 8.5 + (payload.telemetry.wrist_kinetic_energy > 1400 ? 1.0 : 0.5));
      fpProb = 0.08;
      verdict = "CRITICAL_EMERGENCY";
      priority = "IMMEDIATE_RESPONSE";
      units = ["POLICE", "SECURITY_GUARD"];
    } else if (isFall) {
      score10 = 9.2;
      fpProb = 0.05;
      verdict = "CRITICAL_EMERGENCY";
      priority = "IMMEDIATE_RESPONSE";
      units = ["AMBULANCE", "SECURITY_GUARD"];
    } else if (isFlee) {
      score10 = 7.5;
      fpProb = 0.35;
      verdict = "CONFIRMED_THREAT";
      priority = "URGENT";
      units = ["SECURITY_GUARD", "POLICE"];
    } else if (isConceal) {
      score10 = 7.8;
      fpProb = 0.25;
      verdict = "SUSPICIOUS_MONITOR";
      priority = "URGENT";
      weaponType = "CONCEALED_FIREARM";
      units = ["POLICE", "SECURITY_GUARD"];
    } else if (isLoiter) {
      score10 = payload.telemetry.dwell_time_seconds > 20 ? 6.5 : 4.5;
      fpProb = 0.45;
      verdict = "SUSPICIOUS_MONITOR";
      priority = "ROUTINE";
      units = ["SECURITY_GUARD"];
    }

    return {
      severity_score_10: Math.round(score10 * 10) / 10,
      false_positive_probability: fpProb,
      is_false_positive: fpProb >= 0.70,
      threat_verdict: verdict,
      subject_features: {
        posture_assessment: isFight ? "Aggressive physical engagement" : (isFall ? "Horizontal body collapse" : "Mobile subject"),
        suspicious_concealment: isConceal,
        movement_intent: isFlee ? "Rapid fleeing" : "Local area navigation",
        estimated_threat_actor_count: payload.interacting_subject_ids?.length ? payload.interacting_subject_ids.length + 1 : 1
      },
      weapons_identified: {
        has_weapon_indicator: isConceal,
        weapon_type: weaponType,
        weapon_confidence: isConceal ? 0.70 : 0.0,
        description: isConceal ? "Hand concealed behind waistband" : "No overt weapon confirmed"
      },
      victim_assessment: {
        has_victim_present: isFall || isFight,
        victim_track_id: isFall ? payload.primary_subject_id : undefined,
        victim_condition: isFall ? "FALLEN_UNRESPONSIVE" : (isFight ? "UNDER_ATTACK" : "NONE"),
        bystander_count: 0
      },
      dispatch_recommendation: {
        priority: priority,
        recommended_units: units,
        action_notes: `Operator verification required for ${payload.engine_behavior}`
      },
      investigation_summary: `Biomechanical assessment confirmed ${payload.engine_behavior} with ${payload.engine_threat_level} severity.`
    };
  }
}
