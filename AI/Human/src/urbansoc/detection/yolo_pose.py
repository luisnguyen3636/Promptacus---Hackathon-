"""YOLO11-Pose Detection and ByteTrack Integration Engine."""

import logging
import os
import time
import warnings
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional, Tuple

import cv2
import numpy as np

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.detection.base import PoseDetector
from urbansoc.detection.mediapipe_pose import PoseSkeletonDetector
from urbansoc.domain.enums import BehaviorType, ThreatLevel
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
from urbansoc.render.hud import draw_diagnostic_alert_box, draw_soc_hud_dashboard
from urbansoc.render.skeleton import draw_pose_skeleton_and_indicators
from urbansoc.render.theme import THREAT_COLORS

logger = logging.getLogger("urbansoc.detection.yolo_pose")


class YOLOPoseDetector(PoseDetector):
    """Primary detector combining YOLO11-Pose with Supervision ByteTrack and BehaviorEngine."""

    def __init__(
        self,
        model_path: str = "yolo/yolo11n-pose.pt",
        device: Optional[str] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        track_activation_threshold: float = 0.25,
        lost_track_buffer: int = 45,
        minimum_matching_threshold: float = 0.80,
        fps: float = 20.0,
        output_dir: str = "output",
        keypoint_conf_threshold: float = KEYPOINT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.track_activation_threshold = track_activation_threshold
        self.lost_track_buffer = lost_track_buffer
        self.minimum_matching_threshold = minimum_matching_threshold
        self.target_fps = fps
        self.output_dir = os.path.abspath(output_dir)
        self.keypoint_conf_threshold = keypoint_conf_threshold

        self.show_debug_box = True
        self.use_fallback = False
        self.fallback_detector: Optional[PoseSkeletonDetector] = None

        self._fps_history: Deque[float] = deque(maxlen=15)
        self.current_fps = fps

        self.behavior_engine = BehaviorEngine(
            fps=fps,
            enter_debounce_frames=8,
            exit_debounce_frames=12,
            fast_track_debounce_frames=6,
            bbox_ema_alpha=0.65,
            output_dir=self.output_dir,
        )

        self._init_yolo_and_bytetrack()

    def _resolve_model_path(self, path: str) -> Optional[str]:
        """Check candidate paths for the model weights."""
        candidates = [
            path,
            os.path.join("yolo", os.path.basename(path)),
            os.path.join("models", os.path.basename(path)),
            os.path.basename(path),
            os.path.join("/home/test/Hackathon-Test-", os.path.basename(path)),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate) and os.path.getsize(candidate) > 1000:
                return os.path.abspath(candidate)
        return None

    def _init_yolo_and_bytetrack(self) -> None:
        """Initialize PyTorch device, Ultralytics YOLO model, and Supervision ByteTrack."""
        resolved_path = self._resolve_model_path(self.model_path)

        if not resolved_path:
            logger.warning(
                "YOLO model weights not found at '%s'. Operating in resilient fallback mode (CD-05).",
                self.model_path,
            )
            self._activate_fallback()
            return

        # Determine compute device
        if self.device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                self.device = "cpu"

        try:
            from ultralytics import YOLO
            import supervision as sv

            logger.info("Loading YOLO pose model from '%s' on device '%s'...", resolved_path, self.device)
            self.model = YOLO(resolved_path)
            try:
                self.model.to(self.device)
            except Exception as e:
                logger.warning("Could not move model to %s: %s. Using default device.", self.device, e)

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning)
                self.tracker = sv.ByteTrack(
                    track_activation_threshold=self.track_activation_threshold,
                    lost_track_buffer=self.lost_track_buffer,
                    minimum_matching_threshold=self.minimum_matching_threshold,
                    frame_rate=int(self.target_fps),
                )
            logger.info("YOLO11-Pose and ByteTrack initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize YOLO or ByteTrack (%s). Activating fallback.", e, exc_info=True)
            self._activate_fallback()

    def _activate_fallback(self) -> None:
        self.use_fallback = True
        self.fallback_detector = PoseSkeletonDetector(
            models_dir=os.path.join(os.path.dirname(self.output_dir), "models"),
            output_dir=self.output_dir,
            fps=self.target_fps,
        )

    def toggle_debug_box(self) -> bool:
        self.show_debug_box = not self.show_debug_box
        if self.fallback_detector:
            self.fallback_detector.show_debug_box = self.show_debug_box
        return self.show_debug_box

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        frame_index: int = 0,
        timestamp: float = 0.0,
    ) -> Tuple[SOCFrameAnalysisResult, np.ndarray]:
        t_frame_start = time.time()
        curr_time = t_frame_start if timestamp <= 0 else timestamp
        dt_obj = datetime.fromtimestamp(curr_time)
        now_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        if self.use_fallback and self.fallback_detector is not None:
            return self.fallback_detector.process_frame(frame_bgr, frame_index, curr_time)

        import supervision as sv

        # Step 1: YOLO inference
        t_infer_start = time.time()
        results = self.model(
            frame_bgr,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )[0]
        t_infer = (time.time() - t_infer_start) * 1000.0

        # Step 2: ByteTrack update
        t_track_start = time.time()
        detections = sv.Detections.from_ultralytics(results)
        tracked = self.tracker.update_with_detections(detections)
        t_track = (time.time() - t_track_start) * 1000.0

        # Step 3: Extract raw boxes and keypoints
        raw_kpts_data = None
        raw_boxes_xyxy = None
        if results.keypoints is not None and hasattr(results.keypoints, "data"):
            raw_kpts_data = results.keypoints.data.cpu().numpy()
        if results.boxes is not None and hasattr(results.boxes, "xyxy"):
            raw_boxes_xyxy = results.boxes.xyxy.cpu().numpy()

        raw_poses: List[HumanPoseTrack] = []

        # Step 4: Associate keypoints to tracked subjects
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
                        k_name = COCO_KEYPOINT_NAMES[k_idx] if k_idx < len(COCO_KEYPOINT_NAMES) else f"kp_{k_idx}"
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

        # Step 5: Temporal behavioral analysis
        t_beh_start = time.time()
        tracked_poses, telemetry, alerts = self.behavior_engine.update(
            raw_poses, curr_time, frame_index
        )
        t_beh = (time.time() - t_beh_start) * 1000.0

        # Step 6: Threat aggregation
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

        # Step 7: Update FPS moving average
        dt_frame = max(1e-4, time.time() - t_frame_start)
        self._fps_history.append(1.0 / dt_frame)
        self.current_fps = sum(self._fps_history) / len(self._fps_history)

        # Step 8: Build analysis result
        analysis = SOCFrameAnalysisResult(
            frame_index=frame_index,
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

        # Step 9: Render overlays
        annotated = frame_bgr.copy()
        for human in tracked_poses:
            palette = THREAT_COLORS[human.behavior.threat_level]
            draw_pose_skeleton_and_indicators(
                annotated,
                human,
                palette,
                conf_thresh=self.keypoint_conf_threshold,
            )

        annotated = draw_soc_hud_dashboard(annotated, analysis, self.current_fps)
        if self.show_debug_box:
            annotated = draw_diagnostic_alert_box(annotated, analysis)

        return analysis, annotated

    def close(self) -> None:
        """Release behavior logger handles and fallback instances."""
        if hasattr(self, "behavior_engine") and self.behavior_engine:
            self.behavior_engine.close()
        if self.fallback_detector:
            self.fallback_detector.close()
