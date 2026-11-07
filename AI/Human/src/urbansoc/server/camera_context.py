"""Multi-tenant Camera Context Manager ensuring strict isolation between multiple camera feeds."""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.domain.enums import ThreatLevel
from urbansoc.domain.geometry import BBox, iou_xyxy
from urbansoc.domain.keypoints import (
    COCO_KEYPOINT_NAMES,
    KEYPOINT_CONFIDENCE_THRESHOLD,
)
from urbansoc.domain.schemas import (
    HumanPoseTrack,
    KeypointCOCO,
    SOCFrameAnalysisResult,
)
from urbansoc.domain.webhook_models import CameraLocationConfig
from urbansoc.render.hud import draw_diagnostic_alert_box, draw_soc_hud_dashboard
from urbansoc.render.skeleton import draw_pose_skeleton_and_indicators
from urbansoc.render.theme import THREAT_COLORS
from urbansoc.telemetry.webhook_dispatcher import EventThrottler

logger = logging.getLogger("urbansoc.server.camera_context")


class CameraContext:
    """Isolated state and processing context for an individual camera stream.

    Guarantees that Track IDs, kinematics history, and Hysteresis state machines
    from Camera A never cross-contaminate or collide with Camera B (AGENTS.md CD-02, CD-05).
    """

    def __init__(
        self,
        camera_id: str,
        config: Optional[CameraLocationConfig] = None,
        output_dir: str = "output",
        fps: float = 15.0,
        cooldown_seconds: float = 3.0,
    ) -> None:
        self.camera_id = camera_id
        self.config = config if config is not None else CameraLocationConfig(camera_id=camera_id)
        self.output_dir = os.path.abspath(output_dir)
        self.fps = fps
        self.cooldown_seconds = cooldown_seconds

        # Dedicated behavior engine and debouncer per camera
        camera_output_dir = os.path.join(self.output_dir, "cameras", camera_id)
        os.makedirs(camera_output_dir, exist_ok=True)

        self.behavior_engine = BehaviorEngine(
            fps=fps,
            enter_debounce_frames=8,
            exit_debounce_frames=12,
            fast_track_debounce_frames=6,
            output_dir=camera_output_dir,
        )

        # Dedicated ByteTrack tracker per camera to isolate Track IDs
        try:
            import warnings
            import supervision as sv

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning)
                self.tracker: Optional[sv.ByteTrack] = sv.ByteTrack(
                    track_activation_threshold=0.25,
                    lost_track_buffer=45,
                    minimum_matching_threshold=0.80,
                    frame_rate=max(1, int(fps)),
                )
        except Exception as e:
            logger.warning("Could not initialize ByteTrack for camera %s: %s", camera_id, e)
            self.tracker = None

        # Dedicated event throttler per camera (so cooldown on CAM_01 doesn't silence CAM_02)
        self.throttler = EventThrottler(default_cooldown=cooldown_seconds)

        # State tracking
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.measured_fps = fps
        self._fps_window: List[float] = []

        self.latest_analysis: Optional[SOCFrameAnalysisResult] = None
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_display_frame: Optional[np.ndarray] = None
        self.is_active = True
        self._lock = threading.Lock()

    def process_detections(
        self,
        frame_bgr: np.ndarray,
        detections: Optional[Any],
        raw_kpts_data: Optional[np.ndarray],
        raw_boxes_xyxy: Optional[np.ndarray],
        t_infer: float = 0.0,
        timestamp: Optional[float] = None,
        keypoint_conf_threshold: float = KEYPOINT_CONFIDENCE_THRESHOLD,
    ) -> Tuple[SOCFrameAnalysisResult, np.ndarray]:
        """Process pre-inferred detections through this camera's dedicated tracker & behavior engine."""
        t_start = time.time()
        curr_time = t_start if (timestamp is None or timestamp <= 0) else timestamp
        dt_obj = datetime.fromtimestamp(curr_time)
        now_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        raw_poses: List[HumanPoseTrack] = []
        t_track = 0.0

        if detections is not None and self.tracker is not None and len(detections) > 0:
            t_tr_start = time.time()
            tracked = self.tracker.update_with_detections(detections)
            t_track = (time.time() - t_tr_start) * 1000.0

            for idx in range(len(tracked)):
                xyxy = tracked.xyxy[idx]
                det_conf = float(tracked.confidence[idx]) if tracked.confidence is not None else 1.0
                tracker_id = tracked.tracker_id[idx] if tracked.tracker_id is not None else None
                if tracker_id is None:
                    continue

                track_id = int(tracker_id)
                track_bbox = BBox.from_xyxy(xyxy[0], xyxy[1], xyxy[2], xyxy[3])
                matched_keypoints: List[KeypointCOCO] = []

                if raw_boxes_xyxy is not None and raw_kpts_data is not None and len(raw_boxes_xyxy) > 0:
                    best_iou = -1.0
                    best_box_idx = -1
                    for r_idx, r_box in enumerate(raw_boxes_xyxy):
                        c_iou = iou_xyxy(track_bbox, r_box)
                        if c_iou > best_iou:
                            best_iou = c_iou
                            best_box_idx = r_idx

                    if best_box_idx >= 0:
                        kpt_array = raw_kpts_data[best_box_idx]
                        for k_idx in range(min(17, len(kpt_array))):
                            kx, ky, kc = kpt_array[k_idx]
                            k_name = (
                                COCO_KEYPOINT_NAMES[k_idx]
                                if k_idx < len(COCO_KEYPOINT_NAMES)
                                else f"kp_{k_idx}"
                            )
                            matched_keypoints.append(
                                KeypointCOCO(
                                    id=k_idx,
                                    name=k_name,
                                    x=float(kx),
                                    y=float(ky),
                                    confidence=float(kc),
                                )
                            )

                pose = HumanPoseTrack(
                    track_id=track_id,
                    bbox=track_bbox,
                    detection_conf=det_conf,
                    keypoints=matched_keypoints,
                )
                raw_poses.append(pose)

        # Behavioral analysis
        t_beh_start = time.time()
        tracked_poses, telemetry, alerts = self.behavior_engine.update(
            raw_poses, curr_time, self.frame_count
        )
        t_beh = (time.time() - t_beh_start) * 1000.0

        # Threat aggregation
        threat_rank = {
            ThreatLevel.LOW: 0,
            ThreatLevel.MEDIUM: 1,
            ThreatLevel.HIGH: 2,
            ThreatLevel.CRITICAL: 3,
        }
        highest_threat = ThreatLevel.LOW
        highest_score = 0.0
        critical_events: List[str] = []

        for p in tracked_poses:
            p_threat = p.behavior.threat_level
            p_score = p.behavior.threat_score
            if threat_rank.get(p_threat, 0) > threat_rank.get(highest_threat, 0):
                highest_threat = p_threat
            if p_score > highest_score:
                highest_score = p_score

            if p_threat in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                critical_events.append(
                    f"ID #{p.track_id} [{p.behavior.primary_behavior.value}]: {p.behavior.reasoning}"
                )

        analysis = SOCFrameAnalysisResult(
            frame_index=self.frame_count,
            timestamp=now_str,
            human_count=len(tracked_poses),
            humans=tracked_poses,
            highest_threat_level=highest_threat,
            highest_threat_score=highest_score,
            critical_events=critical_events,
            telemetry_list=telemetry,
            recent_alerts=alerts,
            inference_time_ms=t_infer,
            tracking_time_ms=t_track,
            behavior_time_ms=t_beh,
        )

        # Render display overlay
        display_frame = frame_bgr.copy()
        for human in tracked_poses:
            palette = THREAT_COLORS[human.behavior.threat_level]
            draw_pose_skeleton_and_indicators(
                display_frame,
                human,
                palette,
                conf_thresh=keypoint_conf_threshold,
            )

        display_frame = draw_soc_hud_dashboard(display_frame, analysis, self.measured_fps)
        display_frame = draw_diagnostic_alert_box(display_frame, analysis)

        # Atomically update context state
        self.update_frame(frame_bgr, display_frame, analysis)

        return analysis, display_frame

    def process_poses(
        self,
        frame_bgr: np.ndarray,
        poses: List[HumanPoseTrack],
        timestamp: Optional[float] = None,
        keypoint_conf_threshold: float = KEYPOINT_CONFIDENCE_THRESHOLD,
    ) -> Tuple[SOCFrameAnalysisResult, np.ndarray]:
        """Directly process explicit human pose tracks through this camera's isolated BehaviorEngine."""
        t_start = time.time()
        curr_time = t_start if (timestamp is None or timestamp <= 0) else timestamp
        dt_obj = datetime.fromtimestamp(curr_time)
        now_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        tracked_poses, telemetry, alerts = self.behavior_engine.update(
            poses, curr_time, self.frame_count
        )

        threat_rank = {
            ThreatLevel.LOW: 0,
            ThreatLevel.MEDIUM: 1,
            ThreatLevel.HIGH: 2,
            ThreatLevel.CRITICAL: 3,
        }
        highest_threat = ThreatLevel.LOW
        highest_score = 0.0
        critical_events: List[str] = []

        for p in tracked_poses:
            p_threat = p.behavior.threat_level
            p_score = p.behavior.threat_score
            if threat_rank.get(p_threat, 0) > threat_rank.get(highest_threat, 0):
                highest_threat = p_threat
            if p_score > highest_score:
                highest_score = p_score

            if p_threat in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                critical_events.append(
                    f"ID #{p.track_id} [{p.behavior.primary_behavior.value}]: {p.behavior.reasoning}"
                )

        analysis = SOCFrameAnalysisResult(
            frame_index=self.frame_count,
            timestamp=now_str,
            human_count=len(tracked_poses),
            humans=tracked_poses,
            highest_threat_level=highest_threat,
            highest_threat_score=highest_score,
            critical_events=critical_events,
            telemetry_list=telemetry,
            recent_alerts=alerts,
        )

        display_frame = frame_bgr.copy()
        for human in tracked_poses:
            palette = THREAT_COLORS[human.behavior.threat_level]
            draw_pose_skeleton_and_indicators(
                display_frame,
                human,
                palette,
                conf_thresh=keypoint_conf_threshold,
            )

        display_frame = draw_soc_hud_dashboard(display_frame, analysis, self.measured_fps)
        display_frame = draw_diagnostic_alert_box(display_frame, analysis)

        self.update_frame(frame_bgr, display_frame, analysis)
        return analysis, display_frame

    def update_frame(
        self,
        raw_frame: np.ndarray,
        display_frame: np.ndarray,
        analysis: SOCFrameAnalysisResult,
    ) -> None:
        """Atomically update the latest analysis and visual frame for this camera."""
        now = time.time()
        with self._lock:
            dt = now - self.last_frame_time
            self.last_frame_time = now
            self.frame_count += 1

            if dt > 0.001:
                inst_fps = 1.0 / dt
                self._fps_window.append(inst_fps)
                if len(self._fps_window) > 10:
                    self._fps_window.pop(0)
                self.measured_fps = sum(self._fps_window) / len(self._fps_window)

            self.latest_frame = raw_frame
            self.latest_display_frame = display_frame
            self.latest_analysis = analysis
            self.is_active = True

    def get_status_dict(self) -> Dict[str, Any]:
        """Return a snapshot dictionary of this camera's current telemetry status."""
        now = time.time()
        with self._lock:
            highest_threat = (
                self.latest_analysis.highest_threat_level.value
                if self.latest_analysis
                else "LOW"
            )
            highest_score = (
                self.latest_analysis.highest_threat_score
                if self.latest_analysis
                else 0.0
            )
            human_count = (
                self.latest_analysis.human_count
                if self.latest_analysis
                else 0
            )
            primary_action = "NORMAL"
            if self.latest_analysis and self.latest_analysis.humans:
                primary_action = self.latest_analysis.humans[0].behavior.primary_behavior.value

            is_online = (now - self.last_frame_time) < 6.0

            return {
                "camera_id": self.camera_id,
                "name": self.config.name,
                "location": {
                    "latitude": self.config.latitude,
                    "longitude": self.config.longitude,
                    "address": self.config.address,
                },
                "status": "ONLINE" if is_online else "OFFLINE",
                "fps": round(self.measured_fps, 1),
                "total_frames": self.frame_count,
                "seconds_since_last_frame": round(now - self.last_frame_time, 2),
                "human_count": human_count,
                "highest_threat": highest_threat,
                "threat_score": round(highest_score, 2),
                "primary_action": primary_action,
                "has_snapshot": (self.latest_display_frame is not None),
            }


class CameraContextManager:
    """Thread-safe registry managing independent CameraContext instances for all connected laptops/cameras."""

    def __init__(self, output_dir: str = "output", default_fps: float = 15.0) -> None:
        self.output_dir = os.path.abspath(output_dir)
        self.default_fps = default_fps
        self._contexts: Dict[str, CameraContext] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self,
        camera_id: str,
        config: Optional[CameraLocationConfig] = None,
        fps: Optional[float] = None,
    ) -> CameraContext:
        """Retrieve existing camera context or lazily create a new isolated context."""
        clean_id = camera_id.strip()
        with self._lock:
            if clean_id not in self._contexts:
                actual_fps = fps if fps is not None else self.default_fps
                ctx = CameraContext(
                    camera_id=clean_id,
                    config=config,
                    output_dir=self.output_dir,
                    fps=actual_fps,
                )
                self._contexts[clean_id] = ctx
                logger.info("Allocated new CameraContext for camera '%s'", clean_id)
            elif config is not None:
                # Update config if provided
                self._contexts[clean_id].config = config

            return self._contexts[clean_id]

    def get(self, camera_id: str) -> Optional[CameraContext]:
        with self._lock:
            return self._contexts.get(camera_id)

    def get_all_contexts(self) -> Dict[str, CameraContext]:
        with self._lock:
            return dict(self._contexts)

    def prune_stale_cameras(self, timeout_seconds: float = 30.0) -> List[str]:
        """Mark cameras offline if no frames received within timeout."""
        now = time.time()
        pruned = []
        with self._lock:
            for cid, ctx in self._contexts.items():
                if now - ctx.last_frame_time > timeout_seconds:
                    ctx.is_active = False
                    pruned.append(cid)
        return pruned
