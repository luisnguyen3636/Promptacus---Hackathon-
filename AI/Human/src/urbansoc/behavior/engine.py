"""Behavior engine coordinating kinematics, classification rules, debouncing, and audit logging."""

import os
from collections import deque
from datetime import datetime
from typing import Deque, Dict, List, Optional, Tuple

from urbansoc.behavior.interactions import analyze_multi_person_interactions
from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import evaluate_single_track_behavior
from urbansoc.behavior.state_machine import HysteresisDebouncer, TrackDebounceState
from urbansoc.domain.enums import AuditEventType, BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import (
    BehaviorAuditLogEntry,
    BehaviorPrediction,
    HumanPoseTrack,
    TrackHistoryState,
    TrackKinematicsTelemetry,
)
from urbansoc.telemetry.audit_logger import BehaviorAuditLogger


class BehaviorEngine:
    """Core behavioral analysis engine orchestrating multi-frame temporal reasoning."""

    def __init__(
        self,
        fps: float = 20.0,
        history_window_size: int = 30,
        fall_angle_threshold: float = 55.0,
        fall_aspect_ratio_thresh: float = 0.90,
        run_speed_multiplier: float = 1.75,
        loiter_time_threshold: float = 10.0,
        fight_wrist_energy_thresh: float = 1200.0,
        fight_distance_norm: float = 1.35,
        enter_debounce_frames: int = 8,
        exit_debounce_frames: int = 12,
        fast_track_debounce_frames: int = 6,
        bbox_ema_alpha: float = 0.65,
        output_dir: str = "output",
        heartbeat_interval: float = 1.0,
        track_disappeared_timeout: float = 5.0,
    ) -> None:
        self.fps = fps
        self.history_window_size = history_window_size
        self.fall_angle_threshold = fall_angle_threshold
        self.fall_aspect_ratio_thresh = fall_aspect_ratio_thresh
        self.run_speed_multiplier = run_speed_multiplier
        self.loiter_time_threshold = loiter_time_threshold
        self.fight_wrist_energy_thresh = fight_wrist_energy_thresh
        self.fight_distance_norm = fight_distance_norm
        self.bbox_ema_alpha = bbox_ema_alpha
        self.output_dir = os.path.abspath(output_dir)
        self.heartbeat_interval = heartbeat_interval
        self.track_disappeared_timeout = track_disappeared_timeout

        self.audit_logger = BehaviorAuditLogger(output_dir=self.output_dir, heartbeat_interval=heartbeat_interval)
        self.debouncer = HysteresisDebouncer(
            enter_debounce_frames=enter_debounce_frames,
            exit_debounce_frames=exit_debounce_frames,
            fast_track_debounce_frames=fast_track_debounce_frames,
        )

        self.tracks_meta: Dict[int, dict] = {}
        self.recent_alerts: Deque[str] = deque(maxlen=5)

    def update(
        self,
        tracked_poses: List[HumanPoseTrack],
        timestamp: Optional[float] = None,
        frame_index: int = 0,
    ) -> Tuple[List[HumanPoseTrack], List[TrackKinematicsTelemetry], List[str]]:
        """Process detections, smooth bounding boxes, extract kinematics, evaluate behaviors, and log events."""
        curr_time = datetime.now().timestamp() if timestamp is None else timestamp
        dt_obj = datetime.fromtimestamp(curr_time)
        now_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        time_badge_str = dt_obj.strftime("%H:%M:%S")

        states_by_id: Dict[int, TrackHistoryState] = {}
        single_raw_preds: Dict[int, Tuple[BehaviorPrediction, float, float]] = {}
        telemetry_list: List[TrackKinematicsTelemetry] = []

        # 1. Initialize and smooth each track
        for pose in tracked_poses:
            tid = pose.track_id

            if tid not in self.tracks_meta:
                # Track newly initialized
                self.tracks_meta[tid] = {
                    "first_seen": curr_time,
                    "last_seen": curr_time,
                    "initial_centroid": pose.bbox.centroid,
                    "history": deque(maxlen=self.history_window_size),
                    "smooth_bbox": pose.bbox,
                    "debounce_state": TrackDebounceState(confirmed_since=curr_time),
                    "last_heartbeat_time": curr_time,
                }

                # Log TRACK_INITIALIZED audit event
                init_entry = BehaviorAuditLogEntry(
                    event_id=f"EVT_{dt_obj.strftime('%Y%m%d_%H%M%S')}_{tid}",
                    timestamp=now_str,
                    frame_index=frame_index,
                    track_id=tid,
                    event_type=AuditEventType.TRACK_INITIALIZED.value,
                    previous_behavior=None,
                    current_behavior=BehaviorType.NORMAL.value,
                    threat_level=ThreatLevel.LOW.value,
                    threat_score=0.10,
                    telemetry={"spine_angle": 0.0, "aspect_ratio": round(pose.bbox.aspect_ratio, 2), "speed": 0.0, "wrist_velocity": 0.0},
                    reasoning="Initial track identity assigned by ByteTrack",
                    dwell_time_seconds=0.0,
                )
                self.audit_logger.log_event(init_entry)
            else:
                meta = self.tracks_meta[tid]
                meta["last_seen"] = curr_time

                # Smooth BBox with EMA
                alpha = self.bbox_ema_alpha
                prev_bbox = meta["smooth_bbox"]
                raw_x1, raw_y1, raw_x2, raw_y2 = pose.bbox.to_xyxy()
                prev_x1, prev_y1, prev_x2, prev_y2 = prev_bbox.to_xyxy()

                sm_x1 = int(round(alpha * raw_x1 + (1.0 - alpha) * prev_x1))
                sm_y1 = int(round(alpha * raw_y1 + (1.0 - alpha) * prev_y1))
                sm_x2 = int(round(alpha * raw_x2 + (1.0 - alpha) * prev_x2))
                sm_y2 = int(round(alpha * raw_y2 + (1.0 - alpha) * prev_y2))

                smoothed_bbox = BBox.from_xyxy(sm_x1, sm_y1, sm_x2, sm_y2)
                pose.bbox = smoothed_bbox
                meta["smooth_bbox"] = smoothed_bbox

            meta = self.tracks_meta[tid]
            dwell_time = curr_time - meta["first_seen"]
            pose.dwell_time_seconds = dwell_time

            # Extract kinematics and push to history
            state = extract_kinematics_state(pose, curr_time, meta["history"])
            meta["history"].append(state)
            states_by_id[tid] = state

            # Evaluate single track rule
            raw_pred, norm_spd, ar = evaluate_single_track_behavior(
                pose,
                state,
                meta["history"],
                dwell_time,
                meta["initial_centroid"],
                fall_angle_threshold=self.fall_angle_threshold,
                fall_aspect_ratio_thresh=self.fall_aspect_ratio_thresh,
                run_speed_multiplier=self.run_speed_multiplier,
                loiter_time_threshold=self.loiter_time_threshold,
            )
            single_raw_preds[tid] = (raw_pred, norm_spd, ar)

        # 2. Multi-person interaction evaluation (FIGHTING, SNATCHING, PURSUIT, RESTRAINING, SURROUNDING)
        confirmed_behaviors = {
            tid: self.tracks_meta[tid]["debounce_state"].confirmed_behavior
            for tid in self.tracks_meta
        }
        histories_by_id = {
            tid: list(self.tracks_meta[tid]["history"])
            for tid in self.tracks_meta
        }
        interaction_preds = analyze_multi_person_interactions(
            tracked_poses,
            states_by_id,
            confirmed_behaviors,
            histories_by_id=histories_by_id,
            fight_distance_norm=self.fight_distance_norm,
            fight_wrist_energy_thresh=self.fight_wrist_energy_thresh,
        )

        # 3. State machine debouncing & audit logging
        for pose in tracked_poses:
            tid = pose.track_id
            meta = self.tracks_meta[tid]
            deb_state = meta["debounce_state"]
            state = states_by_id[tid]
            raw_pred, norm_spd, ar = single_raw_preds[tid]

            # Multi-person dangerous interaction overrides single-track prediction with highest priority
            if tid in interaction_preds:
                raw_pred = interaction_preds[tid]

            # Run through Hysteresis State Machine
            transition = self.debouncer.process_candidate(deb_state, raw_pred, curr_time)

            telemetry_dict = {
                "spine_angle": round(state.spine_angle, 1),
                "aspect_ratio": round(ar, 2),
                "speed": round(norm_spd, 2),
                "wrist_velocity": round(state.wrist_velocity, 1),
            }

            if transition is not None:
                (
                    event_type,
                    prev_beh,
                    curr_beh,
                    threat_lvl,
                    threat_sc,
                    reasoning,
                    interacting_id,
                ) = transition

                # Log transition event
                event_entry = BehaviorAuditLogEntry(
                    event_id=f"EVT_{dt_obj.strftime('%Y%m%d_%H%M%S')}_{tid}",
                    timestamp=now_str,
                    frame_index=frame_index,
                    track_id=tid,
                    event_type=event_type,
                    previous_behavior=prev_beh,
                    current_behavior=curr_beh,
                    threat_level=threat_lvl.value,
                    threat_score=threat_sc,
                    telemetry=telemetry_dict,
                    reasoning=reasoning,
                    dwell_time_seconds=round(curr_time - deb_state.confirmed_since, 2),
                )
                self.audit_logger.log_event(event_entry)

                # Push to recent alerts
                alert_text = f"[{time_badge_str}] ID #{tid} {prev_beh} -> {curr_beh}"
                self.recent_alerts.appendleft(alert_text)

            # Heartbeat check for sustained HIGH or CRITICAL threats
            if deb_state.confirmed_threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                if curr_time - meta["last_heartbeat_time"] >= self.heartbeat_interval:
                    hb_entry = BehaviorAuditLogEntry(
                        event_id=f"HB_{dt_obj.strftime('%Y%m%d_%H%M%S')}_{tid}",
                        timestamp=now_str,
                        frame_index=frame_index,
                        track_id=tid,
                        event_type=AuditEventType.HEARTBEAT_ALERT.value,
                        previous_behavior=None,
                        current_behavior=deb_state.confirmed_behavior,
                        threat_level=deb_state.confirmed_threat_level.value,
                        threat_score=deb_state.confirmed_threat_score,
                        telemetry=telemetry_dict,
                        reasoning=f"Ongoing {deb_state.confirmed_behavior} event",
                        dwell_time_seconds=round(curr_time - deb_state.confirmed_since, 2),
                    )
                    self.audit_logger.log_event(hb_entry)
                    meta["last_heartbeat_time"] = curr_time

            # Assign confirmed behavior to pose object
            pose.behavior = BehaviorPrediction(
                primary_behavior=BehaviorType(deb_state.confirmed_behavior),
                confidence=raw_pred.confidence,
                threat_level=deb_state.confirmed_threat_level,
                threat_score=deb_state.confirmed_threat_score,
                reasoning=deb_state.confirmed_reasoning,
                interacting_with_track_id=deb_state.confirmed_interacting_id,
                role=getattr(deb_state, "confirmed_role", "individual"),
            )

            # Build telemetry object for rendering
            telemetry_list.append(
                TrackKinematicsTelemetry(
                    track_id=tid,
                    spine_angle=round(state.spine_angle, 1),
                    aspect_ratio=round(ar, 2),
                    speed=round(norm_spd, 2),
                    wrist_energy=round(state.wrist_velocity, 1),
                    dwell_time=round(pose.dwell_time_seconds, 1),
                    confirmed_behavior=deb_state.confirmed_behavior,
                    threat_level=deb_state.confirmed_threat_level,
                    threat_score=deb_state.confirmed_threat_score,
                )
            )

        # 4. Clean up tracks disappeared > timeout (5.0s)
        disappeared_ids = [
            tid
            for tid, m in self.tracks_meta.items()
            if (curr_time - m["last_seen"]) > self.track_disappeared_timeout
        ]
        for tid in disappeared_ids:
            del self.tracks_meta[tid]

        return tracked_poses, telemetry_list, list(self.recent_alerts)

    def close(self) -> None:
        """Release logger handles and internal state."""
        self.audit_logger.close()
