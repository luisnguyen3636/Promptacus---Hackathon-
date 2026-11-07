"""
Threat Marking Engine for Urban Safety AI-SOC.
Central orchestrator uniting:
1. Rule Registry (Rule evaluation)
2. Dynamic Threat Scorer (Temporal scoring St)
3. Hysteresis Debounce State Machine (Anti-flapping & Mark confirmation)
4. Formal SOC Audit & Alert Packaging
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01 and standard.md.
"""

import time
import os
import json
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from Engine.threat_models import (
    ThreatLevel,
    BehaviorType,
    BehaviorCategory,
    SubjectKinematicsSnapshot,
    SubjectThreatMark,
    SOCEngineOutput,
    RuleEvaluationResult
)
from Engine.scoring import DynamicThreatScorer
from Engine.state_machine import HysteresisDebounceStateMachine
from Rule.registry import RuleRegistry


class ThreatMarkingEngine:
    """
    Core Threat Marking & Dynamic Threat Scoring Engine.
    Processes frame-by-frame kinematics, assigns debounced Threat Marks,
    and formats standardized output for Dashboard and Operational HITL.
    """

    def __init__(
        self,
        history_window_size: int = 30,
        enter_debounce_frames: int = 8,
        exit_debounce_frames: int = 12,
        fast_track_critical_frames: int = 5,
        output_dir: str = "output"
    ) -> None:
        self.history_window_size = history_window_size
        self.output_dir = output_dir

        self.registry = RuleRegistry(register_defaults=True)
        self.scorer = DynamicThreatScorer()
        self.state_machine = HysteresisDebounceStateMachine(
            enter_debounce_frames=enter_debounce_frames,
            exit_debounce_frames=exit_debounce_frames,
            fast_track_critical_frames=fast_track_critical_frames
        )

        # track_id -> deque of recent snapshots
        self.history_buffers: Dict[int, deque] = {}
        # track_id -> previous frame computed score
        self.prev_scores: Dict[int, float] = {}

        # Recent alerts buffer (5 most recent alert strings)
        self.recent_alerts: deque = deque(maxlen=5)

    def process_frame(
        self,
        frame_index: int,
        subjects: List[SubjectKinematicsSnapshot],
        timestamp: Optional[float] = None
    ) -> SOCEngineOutput:
        """
        Processes a set of tracked human subjects detected in a video frame.

        Args:
            frame_index: Sequential index of current frame.
            subjects: List of instantaneous subject kinematics snapshots.
            timestamp: Epoch timestamp (defaults to current time if None).

        Returns:
            SOCEngineOutput with verified threat marks, active alerts, and metadata.
        """
        curr_time = time.time() if timestamp is None else timestamp
        now_iso = datetime.fromtimestamp(curr_time).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        all_subjects_map = {s.track_id: s for s in subjects}
        threat_marks: List[SubjectThreatMark] = []
        audit_events: List[Dict[str, Any]] = []

        # Update history buffers
        for sub in subjects:
            tid = sub.track_id
            if tid not in self.history_buffers:
                self.history_buffers[tid] = deque(maxlen=self.history_window_size)
            self.history_buffers[tid].append(sub)

        # 1. First Pass: Evaluate rules for all subjects
        subject_evals: Dict[int, List[RuleEvaluationResult]] = {}
        for sub in subjects:
            tid = sub.track_id
            history_list = list(self.history_buffers[tid])
            matched = self.registry.evaluate_all(sub, history_list, all_subjects_map)
            subject_evals[tid] = matched

        # 2. Second Pass: Dynamic Scoring & Debounced State Machine
        for sub in subjects:
            tid = sub.track_id
            matched_rules = subject_evals.get(tid, [])
            prev_s = self.prev_scores.get(tid, self.scorer.baseline_score)

            # Check if interacting with any hostile partner
            has_hostile_interaction = False
            interacting_partners: List[int] = []
            for r in matched_rules:
                if r.interacting_with_track_ids:
                    interacting_partners.extend(r.interacting_with_track_ids)
            interacting_partners = list(set(interacting_partners))

            if interacting_partners:
                for pid in interacting_partners:
                    if pid in subject_evals and any(pr.base_threat_score >= 0.60 for pr in subject_evals[pid]):
                        has_hostile_interaction = True
                        break

            # Find state dwell time from current state machine
            current_dwell = 0.0
            if tid in self.state_machine._tracks_state:
                current_dwell = curr_time - self.state_machine._tracks_state[tid].get("confirmed_since", curr_time)

            # Compute dynamic score
            raw_score = self.scorer.compute_score(
                prev_score=prev_s,
                matched_evaluations=matched_rules,
                state_dwell_seconds=current_dwell,
                has_hostile_interaction=has_hostile_interaction
            )
            self.prev_scores[tid] = raw_score

            # Determine dominant candidate behavior & category
            if matched_rules:
                best_rule = max(matched_rules, key=lambda r: (r.base_threat_score, r.confidence))
                raw_behavior = best_rule.behavior_type
                raw_category = best_rule.category
                candidate_severity = max(raw_score, best_rule.base_threat_score * best_rule.confidence)
                raw_level = self.scorer.map_score_to_threat_level(candidate_severity)
                summary_reason = best_rule.reasoning
            else:
                raw_behavior = BehaviorType.NORMAL
                raw_category = BehaviorCategory.BENIGN
                raw_level = ThreatLevel.LOW
                summary_reason = "Standard upright gait / benign presence"

            # 3. Apply Hysteresis Debounce State Machine (Anti-Flapping)
            (
                confirmed_level,
                confirmed_score,
                confirmed_behavior,
                confirmed_category,
                state_dwell,
                is_escalated
            ) = self.state_machine.update_track_state(
                track_id=tid,
                raw_threat_level=raw_level,
                raw_score=raw_score,
                raw_behavior=raw_behavior,
                raw_category=raw_category,
                timestamp=curr_time
            )

            # Requires operator verification gate
            requires_hitl = confirmed_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)

            # Diagnostic summary
            mark_color = self.scorer.get_threat_color(confirmed_level)
            diag_str = (
                f"ID #{tid}: {confirmed_behavior.value} [{confirmed_level.value} {confirmed_score*100:.0f}%] "
                f"| Dwell: {state_dwell:.1f}s | {summary_reason}"
            )

            mark = SubjectThreatMark(
                track_id=tid,
                threat_level=confirmed_level,
                threat_score=round(confirmed_score, 2),
                confirmed_behavior=confirmed_behavior,
                behavior_category=confirmed_category,
                dwell_time_seconds=round(sub.dwell_time_seconds, 1),
                state_dwell_seconds=round(state_dwell, 1),
                is_escalated=is_escalated,
                requires_operator_attention=requires_hitl,
                interacting_partners=interacting_partners,
                diagnostic_summary=diag_str,
                color_hex=mark_color
            )
            threat_marks.append(mark)

            # Audit event log generation upon escalation or critical mark
            if is_escalated or confirmed_level == ThreatLevel.CRITICAL:
                audit_rec = {
                    "event_id": f"EVT_{datetime.fromtimestamp(curr_time).strftime('%Y%m%d_%H%M%S')}_{tid}",
                    "timestamp": now_iso,
                    "frame_index": frame_index,
                    "track_id": tid,
                    "threat_level": confirmed_level.value,
                    "behavior": confirmed_behavior.value,
                    "category": confirmed_category.value,
                    "score": round(confirmed_score, 2),
                    "is_escalated": is_escalated,
                    "reasoning": summary_reason
                }
                audit_events.append(audit_rec)

                # Push to recent alert ticker
                ticker_badge = f"[{datetime.fromtimestamp(curr_time).strftime('%H:%M:%S')}] ID #{tid} {confirmed_behavior.value} ({confirmed_level.value})"
                self.recent_alerts.appendleft(ticker_badge)

        # 4. Aggregated Frame-level Statistics
        rank_order = {ThreatLevel.LOW: 0, ThreatLevel.MEDIUM: 1, ThreatLevel.HIGH: 2, ThreatLevel.CRITICAL: 3}
        highest_threat = ThreatLevel.LOW
        highest_score = 0.0

        for tm in threat_marks:
            if rank_order[tm.threat_level] > rank_order[highest_threat]:
                highest_threat = tm.threat_level
                highest_score = tm.threat_score
            elif rank_order[tm.threat_level] == rank_order[highest_threat]:
                highest_score = max(highest_score, tm.threat_score)

        # Prune inactive tracks
        self.state_machine.prune_stale_tracks(curr_time)
        active_ids = {s.track_id for s in subjects}
        stale_history = [tid for tid in self.history_buffers if tid not in active_ids and (curr_time - self.history_buffers[tid][-1].timestamp) > 6.0]
        for tid in stale_history:
            del self.history_buffers[tid]
            self.prev_scores.pop(tid, None)

        return SOCEngineOutput(
            frame_index=frame_index,
            timestamp=now_iso,
            subjects_count=len(subjects),
            threat_marks=threat_marks,
            highest_threat_level=highest_threat,
            highest_threat_score=round(highest_score, 2),
            active_alerts=list(self.recent_alerts),
            audit_events=audit_events
        )
