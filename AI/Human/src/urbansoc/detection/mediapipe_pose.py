"""Resilient fallback detection engine using MediaPipe Pose Landmarker and OpenCV HOG."""

import logging
import math
import os
import time
import urllib.request
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from urbansoc.detection.base import PoseDetector
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox, iou_xyxy
from urbansoc.domain.keypoints import (
    KEYPOINT_CONFIDENCE_THRESHOLD,
    MEDIAPIPE_LANDMARK_NAMES,
    MEDIAPIPE_SKELETON_PAIRS,
)
from urbansoc.domain.schemas import (
    HumanPoseTrack,
    KeypointCOCO,
    SOCFrameAnalysisResult,
    TrackKinematicsTelemetry,
)
from urbansoc.render.hud import draw_diagnostic_alert_box, draw_soc_hud_dashboard
from urbansoc.render.skeleton import draw_corner_bounding_box
from urbansoc.render.theme import PERSON_PALETTES, THREAT_COLORS

logger = logging.getLogger("urbansoc.detection.mediapipe_pose")

MODEL_URL_LITE = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"


class MultiPersonTracker:
    """Greedy spatial-temporal tracker for multi-subject ID persistence across frames."""

    def __init__(self, max_disappeared: int = 12, cost_threshold: float = 0.85) -> None:
        self.max_disappeared = max_disappeared
        self.cost_threshold = cost_threshold
        self.next_track_id = 1
        self.tracks: Dict[int, dict] = {}

    def update(self, detected_boxes: List[BBox]) -> List[Tuple[int, BBox]]:
        """Match detected boxes with existing tracks using weighted IoU and centroid distance."""
        if not self.tracks:
            matches = []
            for box in detected_boxes:
                tid = self.next_track_id
                self.next_track_id += 1
                self.tracks[tid] = {"bbox": box, "disappeared": 0}
                matches.append((tid, box))
            return matches

        track_ids = list(self.tracks.keys())
        prev_boxes = [self.tracks[tid]["bbox"] for tid in track_ids]

        # Compute cost matrix
        matched_tracks = set()
        matched_detections = set()
        matches = []

        cost_matrix = []
        for i, prev_box in enumerate(prev_boxes):
            row = []
            c_prev = prev_box.centroid
            diag_prev = math.hypot(prev_box.width, prev_box.height)
            for j, det_box in enumerate(detected_boxes):
                iou = iou_xyxy(prev_box, det_box)
                c_det = det_box.centroid
                dist = math.hypot(c_prev[0] - c_det[0], c_prev[1] - c_det[1])
                cost = 0.65 * (1.0 - iou) + 0.35 * min(2.0, dist / max(1e-4, diag_prev))
                row.append(cost)
            cost_matrix.append(row)

        if cost_matrix and detected_boxes:
            flat_costs = []
            for i in range(len(track_ids)):
                for j in range(len(detected_boxes)):
                    flat_costs.append((cost_matrix[i][j], i, j))
            flat_costs.sort(key=lambda x: x[0])

            for cost, i, j in flat_costs:
                if cost > self.cost_threshold:
                    break
                if i in matched_tracks or j in matched_detections:
                    continue
                tid = track_ids[i]
                self.tracks[tid]["bbox"] = detected_boxes[j]
                self.tracks[tid]["disappeared"] = 0
                matches.append((tid, detected_boxes[j]))
                matched_tracks.add(i)
                matched_detections.add(j)

        # Increment disappeared for unmatched tracks
        for i, tid in enumerate(track_ids):
            if i not in matched_tracks:
                self.tracks[tid]["disappeared"] += 1

        # Add new tracks for unmatched detections
        for j, det_box in enumerate(detected_boxes):
            if j not in matched_detections:
                tid = self.next_track_id
                self.next_track_id += 1
                self.tracks[tid] = {"bbox": det_box, "disappeared": 0}
                matches.append((tid, det_box))

        # Evict dead tracks
        dead_ids = [
            tid
            for tid, m in self.tracks.items()
            if m["disappeared"] > self.max_disappeared
        ]
        for tid in dead_ids:
            del self.tracks[tid]

        return matches


class PoseSkeletonDetector(PoseDetector):
    """Resilient MediaPipe and OpenCV HOG pose detector."""

    def __init__(
        self,
        models_dir: str = "models",
        output_dir: str = "output",
        max_humans: int = 10,
        fps: float = 20.0,
    ) -> None:
        self.models_dir = os.path.abspath(models_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.max_humans = max_humans
        self.fps = fps
        self.show_debug_box = True
        self.tracker = MultiPersonTracker(max_disappeared=12)
        self._fps_history: deque = deque(maxlen=15)

        self.use_hog = False
        self.hog_detector: Optional[cv2.HOGDescriptor] = None
        self.landmarker = None

        self._init_backend()

    def _init_backend(self) -> None:
        os.makedirs(self.models_dir, exist_ok=True)
        model_path = os.path.join(self.models_dir, "pose_landmarker_lite.task")

        # Try downloading MediaPipe task if not present
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000:
            try:
                logger.info("Downloading MediaPipe Lite pose model: %s", MODEL_URL_LITE)
                urllib.request.urlretrieve(MODEL_URL_LITE, model_path)
            except Exception as e:
                logger.warning("Failed to download MediaPipe model (%s). Falling back to HOG.", e)

        # Try initializing MediaPipe
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                num_poses=self.max_humans,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_segmentation_masks=False,
            )
            self.landmarker = vision.PoseLandmarker.create_from_options(options)
            logger.info("MediaPipe PoseLandmarker initialized successfully.")
        except Exception as e:
            logger.warning("Could not initialize MediaPipe (%s). Activating OpenCV HOG fallback.", e)
            self.use_hog = True
            self.hog_detector = cv2.HOGDescriptor()
            self.hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def toggle_debug_box(self) -> bool:
        self.show_debug_box = not self.show_debug_box
        return self.show_debug_box

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        frame_index: int = 0,
        timestamp: float = 0.0,
    ) -> Tuple[SOCFrameAnalysisResult, np.ndarray]:
        t_start = time.time()
        now_dt = datetime.fromtimestamp(t_start if timestamp <= 0 else timestamp)
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        h, w = frame_bgr.shape[:2]
        detected_boxes: List[BBox] = []

        if self.use_hog or self.landmarker is None:
            # HOG detection fallback
            if self.hog_detector:
                gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                boxes, _ = self.hog_detector.detectMultiScale(
                    gray, winStride=(8, 8), padding=(4, 4), scale=1.05
                )
                for x, y, bw, bh in boxes:
                    detected_boxes.append(BBox.from_xywh(x, y, bw, bh))
        else:
            # MediaPipe Landmarker detection
            try:
                import mediapipe as mp
                rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = self.landmarker.detect(mp_image)

                for pose_landmarks in detection_result.pose_landmarks:
                    xs = [lm.x * w for lm in pose_landmarks]
                    ys = [lm.y * h for lm in pose_landmarks]
                    x1 = max(0, int(min(xs) - 10))
                    y1 = max(0, int(min(ys) - 10))
                    x2 = min(w, int(max(xs) + 10))
                    y2 = min(h, int(max(ys) + 10))
                    detected_boxes.append(BBox.from_xyxy(x1, y1, x2, y2))
            except Exception as e:
                logger.error("MediaPipe detection error: %s", e, exc_info=True)

        # Track associations
        matched = self.tracker.update(detected_boxes)
        tracked_poses: List[HumanPoseTrack] = []
        telemetry_list: List[TrackKinematicsTelemetry] = []

        for tid, box in matched:
            pose = HumanPoseTrack(
                track_id=tid,
                bbox=box,
                detection_conf=0.85,
                keypoints=[],
            )
            tracked_poses.append(pose)
            telemetry_list.append(
                TrackKinematicsTelemetry(
                    track_id=tid,
                    spine_angle=0.0,
                    aspect_ratio=round(box.aspect_ratio, 2),
                    speed=0.0,
                    wrist_energy=0.0,
                    dwell_time=0.0,
                    confirmed_behavior=BehaviorType.NORMAL.value,
                    threat_level=ThreatLevel.LOW,
                    threat_score=0.10,
                )
            )

        t_infer = (time.time() - t_start) * 1000.0
        self._fps_history.append(1.0 / max(1e-4, time.time() - t_start))
        current_fps = sum(self._fps_history) / len(self._fps_history)

        analysis = SOCFrameAnalysisResult(
            frame_index=frame_index,
            timestamp=now_str,
            human_count=len(tracked_poses),
            humans=tracked_poses,
            highest_threat_level=ThreatLevel.LOW,
            highest_threat_score=0.10,
            telemetry_list=telemetry_list,
            recent_alerts=[],
            inference_time_ms=t_infer,
            behavior_time_ms=0.0,
        )

        # Draw overlays
        annotated = frame_bgr.copy()
        for i, pose in enumerate(tracked_poses):
            palette = PERSON_PALETTES[(pose.track_id - 1) % len(PERSON_PALETTES)]
            draw_corner_bounding_box(annotated, pose.bbox, palette["box"])
            x1, y1, _, _ = pose.bbox.to_xyxy()
            cv2.putText(
                annotated,
                f"ID #{pose.track_id} [FALLBACK]",
                (x1 + 5, max(15, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                palette["box"],
                1,
                cv2.LINE_AA,
            )

        annotated = draw_soc_hud_dashboard(annotated, analysis, current_fps)
        if self.show_debug_box:
            annotated = draw_diagnostic_alert_box(annotated, analysis)

        return analysis, annotated

    def close(self) -> None:
        if self.landmarker and hasattr(self.landmarker, "close"):
            try:
                self.landmarker.close()
            except Exception:
                pass
