"""Asynchronous, non-blocking HTTP POST Webhook Dispatcher with Anti-Noise Filtering and Forensic SHA-256."""

import base64
import hashlib
import json
import logging
import math
import queue
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO, SOCFrameAnalysisResult
from urbansoc.domain.webhook_models import (
    CameraLocationConfig,
    SubjectCropData,
    WebhookIncidentPayload,
)

logger = logging.getLogger("urbansoc.telemetry.webhook_dispatcher")

# Import requests with fallback to urllib.request for resilient environments
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.error
    import urllib.request


def compute_forensic_sha256(raw_bytes: bytes, timestamp_ms: int) -> str:
    """Compute cryptographic SHA-256 hash combining raw JPEG bytes and exact millisecond timestamp.

    Forensic verification formula:
        SHA256 = hashlib.sha256(raw_bytes + str(timestamp_ms).encode('utf-8')).hexdigest()
    """
    hasher = hashlib.sha256()
    hasher.update(raw_bytes)
    hasher.update(str(timestamp_ms).encode("utf-8"))
    return hasher.hexdigest()


def crop_subject_image(
    frame: np.ndarray,
    bbox: BBox,
    margin: float = 0.10,
) -> Optional[np.ndarray]:
    """Safely crop a bounding box region with padding margin from an image."""
    if frame is None or frame.size == 0:
        return None

    h, w = frame.shape[:2]
    bx1, by1, bx2, by2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2

    box_w = max(1.0, bx2 - bx1)
    box_h = max(1.0, by2 - by1)

    pad_x = int(round(box_w * margin))
    pad_y = int(round(box_h * margin))

    x1 = max(0, int(bx1) - pad_x)
    y1 = max(0, int(by1) - pad_y)
    x2 = min(w, int(bx2) + pad_x)
    y2 = min(h, int(by2) + pad_y)

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2].copy()
    return crop if crop.size > 0 else None


def encode_image_and_hash(
    image: np.ndarray,
    timestamp_ms: int,
    quality: int = 80,
) -> Tuple[str, str, int]:
    """Encode OpenCV BGR image to JPEG bytes, compute SHA-256 hash with timestamp, and return Base64.

    Returns:
        (base64_data_url, sha256_hash, image_size_bytes)
    """
    if image is None or image.size == 0:
        return "", "", 0
    try:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, quality))]
        success, buffer = cv2.imencode(".jpg", image, encode_params)
        if not success:
            return "", "", 0
        raw_bytes = buffer.tobytes()
        sha256_hash = compute_forensic_sha256(raw_bytes, timestamp_ms)
        b64_str = base64.b64encode(raw_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_str}"
        return data_url, sha256_hash, len(raw_bytes)
    except Exception as e:
        logger.error("Failed to encode image and compute forensic hash: %s", e)
        return "", "", 0


def calculate_joint_angle(
    pt_a: Tuple[float, float],
    pt_vertex: Tuple[float, float],
    pt_b: Tuple[float, float],
) -> float:
    """Compute the angle at pt_vertex in degrees [0, 180]."""
    v1_x = pt_a[0] - pt_vertex[0]
    v1_y = pt_a[1] - pt_vertex[1]
    v2_x = pt_b[0] - pt_vertex[0]
    v2_y = pt_b[1] - pt_vertex[1]

    mag1 = math.hypot(v1_x, v1_y)
    mag2 = math.hypot(v2_x, v2_y)
    if mag1 < 1e-4 or mag2 < 1e-4:
        return 0.0

    dot = v1_x * v2_x + v1_y * v2_y
    cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return float(math.degrees(math.acos(cos_val)))


def extract_subject_kinematics(track: HumanPoseTrack) -> Dict[str, float]:
    """Extract biomechanical kinematic angles, distances, and aspect ratios from keypoints."""
    bh = max(1.0, float(track.bbox.height))
    bw = max(1.0, float(track.bbox.width))
    aspect_ratio = bh / bw

    kp_map = {kp.id: kp for kp in track.keypoints if kp.confidence >= 0.20}

    # Spine Angle: vector from mid-hip to mid-shoulder against vertical
    spine_angle = 0.0
    if LEFT_SHOULDER in kp_map and RIGHT_SHOULDER in kp_map and LEFT_HIP in kp_map and RIGHT_HIP in kp_map:
        mid_s_x = (kp_map[LEFT_SHOULDER].x + kp_map[RIGHT_SHOULDER].x) / 2.0
        mid_s_y = (kp_map[LEFT_SHOULDER].y + kp_map[RIGHT_SHOULDER].y) / 2.0
        mid_h_x = (kp_map[LEFT_HIP].x + kp_map[RIGHT_HIP].x) / 2.0
        mid_h_y = (kp_map[LEFT_HIP].y + kp_map[RIGHT_HIP].y) / 2.0

        dx = mid_s_x - mid_h_x
        dy = mid_s_y - mid_h_y  # negative if shoulders are above hips
        mag = math.hypot(dx, dy)
        if mag > 1e-4:
            # angle against upright vertical (dx=0, dy=-1)
            cos_spine = max(-1.0, min(1.0, -dy / mag))
            spine_angle = float(math.degrees(math.acos(cos_spine)))

    # Left & Right Elbow angles
    left_elbow_angle = 0.0
    if LEFT_SHOULDER in kp_map and LEFT_ELBOW in kp_map and LEFT_WRIST in kp_map:
        left_elbow_angle = calculate_joint_angle(
            (kp_map[LEFT_SHOULDER].x, kp_map[LEFT_SHOULDER].y),
            (kp_map[LEFT_ELBOW].x, kp_map[LEFT_ELBOW].y),
            (kp_map[LEFT_WRIST].x, kp_map[LEFT_WRIST].y),
        )

    right_elbow_angle = 0.0
    if RIGHT_SHOULDER in kp_map and RIGHT_ELBOW in kp_map and RIGHT_WRIST in kp_map:
        right_elbow_angle = calculate_joint_angle(
            (kp_map[RIGHT_SHOULDER].x, kp_map[RIGHT_SHOULDER].y),
            (kp_map[RIGHT_ELBOW].x, kp_map[RIGHT_ELBOW].y),
            (kp_map[RIGHT_WRIST].x, kp_map[RIGHT_WRIST].y),
        )

    # Arm extension ratios (distance from wrist to shoulder normalized by body height)
    left_arm_extension = 0.0
    if LEFT_SHOULDER in kp_map and LEFT_WRIST in kp_map:
        left_arm_extension = float(math.hypot(
            kp_map[LEFT_WRIST].x - kp_map[LEFT_SHOULDER].x,
            kp_map[LEFT_WRIST].y - kp_map[LEFT_SHOULDER].y,
        ) / bh)

    right_arm_extension = 0.0
    if RIGHT_SHOULDER in kp_map and RIGHT_WRIST in kp_map:
        right_arm_extension = float(math.hypot(
            kp_map[RIGHT_WRIST].x - kp_map[RIGHT_SHOULDER].x,
            kp_map[RIGHT_WRIST].y - kp_map[RIGHT_SHOULDER].y,
        ) / bh)

    # Wrist Distance (for tactical weapon aiming posture)
    wrist_distance = 0.0
    if LEFT_WRIST in kp_map and RIGHT_WRIST in kp_map:
        wrist_distance = float(math.hypot(
            kp_map[LEFT_WRIST].x - kp_map[RIGHT_WRIST].x,
            kp_map[LEFT_WRIST].y - kp_map[RIGHT_WRIST].y,
        ))

    return {
        "spine_angle": round(spine_angle, 2),
        "aspect_ratio": round(aspect_ratio, 2),
        "left_elbow_angle": round(left_elbow_angle, 2),
        "right_elbow_angle": round(right_elbow_angle, 2),
        "left_arm_extension": round(left_arm_extension, 3),
        "right_arm_extension": round(right_arm_extension, 3),
        "wrist_distance": round(wrist_distance, 2),
        "wrist_velocity": round(float(getattr(track, "wrist_velocity", 0.0)), 2),
    }


class EventThrottler:
    """Manages anti-noise filtering, cooldown, and deduplication per track to prevent flooding target servers."""

    THREAT_RANK = {
        ThreatLevel.LOW: 1,
        ThreatLevel.MEDIUM: 2,
        ThreatLevel.HIGH: 3,
        ThreatLevel.CRITICAL: 4,
    }

    def __init__(self, default_cooldown: float = 3.0) -> None:
        self.default_cooldown = default_cooldown
        # track_id -> {"last_time": float, "threat_level": ThreatLevel, "behavior": str}
        self._history: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def should_dispatch(
        self,
        track_id: int,
        behavior: str,
        threat_level: ThreatLevel,
        now: float,
        cooldown: Optional[float] = None,
    ) -> bool:
        """Determine if an event for a track should be dispatched immediately."""
        active_cooldown = cooldown if cooldown is not None else self.default_cooldown

        with self._lock:
            # Clean up ancient records older than 120s
            stale_keys = [
                tid for tid, data in self._history.items()
                if now - data["last_time"] > 120.0
            ]
            for tid in stale_keys:
                del self._history[tid]

            if track_id not in self._history:
                self._history[track_id] = {
                    "last_time": now,
                    "threat_level": threat_level,
                    "behavior": behavior,
                }
                return True

            prev = self._history[track_id]
            prev_rank = self.THREAT_RANK.get(prev["threat_level"], 1)
            curr_rank = self.THREAT_RANK.get(threat_level, 1)

            # 1. Anti-noise bypass: Immediate dispatch if threat level escalated (e.g. LOW -> HIGH or HIGH -> CRITICAL)
            if curr_rank > prev_rank:
                self._history[track_id] = {
                    "last_time": now,
                    "threat_level": threat_level,
                    "behavior": behavior,
                }
                return True

            # 2. Anti-noise bypass: Immediate dispatch if behavior transitioned to a different dangerous action
            if behavior != prev["behavior"] and curr_rank >= 3:
                self._history[track_id] = {
                    "last_time": now,
                    "threat_level": threat_level,
                    "behavior": behavior,
                }
                return True

            # 3. Time-based cooldown check (anti-spam filter)
            if now - prev["last_time"] >= active_cooldown:
                self._history[track_id] = {
                    "last_time": now,
                    "threat_level": threat_level,
                    "behavior": behavior,
                }
                return True

            return False


class WebhookDispatcher:
    """Asynchronous, non-blocking HTTP POST dispatcher with anti-noise filtering and forensic SHA-256."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        camera_config: Optional[CameraLocationConfig] = None,
        min_threat_level: str = "ALL",
        cooldown_seconds: float = 3.0,
        timeout: float = 3.5,
        max_retries: int = 2,
        queue_maxsize: int = 50,
        image_quality: int = 80,
        min_detection_conf: float = 0.35,
        min_bbox_area: int = 1200,
        filter_noise: bool = True,
    ) -> None:
        self.server_url = server_url.strip() if server_url else ""
        self.camera_config = camera_config if camera_config is not None else CameraLocationConfig()
        self.min_threat_level = min_threat_level.upper()
        self.cooldown_seconds = cooldown_seconds
        self.timeout = timeout
        self.max_retries = max_retries
        self.image_quality = image_quality
        self.min_detection_conf = min_detection_conf
        self.min_bbox_area = min_bbox_area
        self.filter_noise = filter_noise

        self.throttler = EventThrottler(default_cooldown=cooldown_seconds)
        self.queue: queue.Queue = queue.Queue(maxsize=queue_maxsize)
        self._stop_event = threading.Event()

        # Telemetry statistics
        self.dispatched_count = 0
        self.failed_count = 0
        self.dropped_count = 0
        self.filtered_noise_count = 0
        self.last_status_code: Optional[int] = None
        self.last_error_message: Optional[str] = None

        # Start dedicated background worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="SOCWebhookWorker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info(
            "WebhookDispatcher started. Target URL: %s | Camera: %s (Lat: %s, Lon: %s) | Anti-Noise: %s (min_conf: %.2f, min_area: %d)",
            self.server_url or "[DISABLED/LOCAL_LOG_ONLY]",
            self.camera_config.camera_id,
            self.camera_config.latitude,
            self.camera_config.longitude,
            self.filter_noise,
            self.min_detection_conf,
            self.min_bbox_area,
        )

    @property
    def is_enabled(self) -> bool:
        return bool(self.server_url)

    def dispatch_frame_event(
        self,
        frame: np.ndarray,
        annotated_frame: Optional[np.ndarray],
        analysis_result: SOCFrameAnalysisResult,
        audio_result: Optional[Any] = None,
    ) -> bool:
        """Extract metadata, filter noise, crop subjects, compute SHA-256, and enqueue non-blocking.

        Returns:
            True if an event was enqueued, False if filtered out or queue was full.
        """
        if not self.is_enabled:
            return False

        if frame is None or frame.size == 0:
            return False

        now = time.time()
        now_dt = datetime.now()
        timestamp_ms = int(now * 1000)
        iso_timestamp = now_dt.isoformat()

        # Anti-Noise Filter 1 & 2: Filter subjects by confidence, bounding box area, and threat level
        candidate_tracks: List[HumanPoseTrack] = []
        for track in analysis_result.humans:
            # Check noise thresholds
            if self.filter_noise:
                if track.detection_conf < self.min_detection_conf:
                    self.filtered_noise_count += 1
                    continue
                box_area = track.bbox.width * track.bbox.height
                if box_area < self.min_bbox_area or track.bbox.width < 25 or track.bbox.height < 50:
                    self.filtered_noise_count += 1
                    continue

            # Check threat level requirement
            if self._satisfies_min_threat(track.behavior.threat_level):
                candidate_tracks.append(track)

        if not candidate_tracks:
            return False

        # Anti-Noise Filter 3: Check throttler cooldown & deduplication
        dispatched_candidates: List[HumanPoseTrack] = []
        for track in candidate_tracks:
            b_name = track.behavior.primary_behavior.value
            t_level = track.behavior.threat_level
            if self.throttler.should_dispatch(track.track_id, b_name, t_level, now, self.cooldown_seconds):
                dispatched_candidates.append(track)

        if not dispatched_candidates:
            return False

        # Prepare visual frame and compute forensic SHA-256
        target_visual_frame = annotated_frame if annotated_frame is not None else frame
        full_image_b64, full_image_hash, full_image_size = encode_image_and_hash(
            target_visual_frame,
            timestamp_ms=timestamp_ms,
            quality=self.image_quality,
        )

        h_val, w_val = target_visual_frame.shape[:2]
        full_image_data = {
            "format": "jpeg",
            "width": w_val,
            "height": h_val,
            "image_base64": full_image_b64,
            "sha256_hash": full_image_hash,
            "image_size_bytes": full_image_size,
        }

        # Prepare comprehensive subjects metadata and cropped images
        subject_crop_list: List[SubjectCropData] = []
        is_weapon_detected = False
        detected_weapon_types: List[str] = []
        weapon_confidence = 0.0
        primary_action = dispatched_candidates[0].behavior.primary_behavior.value
        highest_score = 0.0
        highest_level = ThreatLevel.LOW

        for track in analysis_result.humans:
            # Skip noise outliers if filtering is enabled
            if self.filter_noise:
                if track.detection_conf < (self.min_detection_conf * 0.8):
                    continue
                box_area = track.bbox.width * track.bbox.height
                if box_area < (self.min_bbox_area * 0.5):
                    continue

            # Crop image for each track involved and calculate SHA-256
            crop_img = crop_subject_image(frame, track.bbox, margin=0.10)
            crop_b64, crop_sha256, crop_size = encode_image_and_hash(
                crop_img,
                timestamp_ms=timestamp_ms,
                quality=self.image_quality,
            )

            # Classify role
            b_enum = track.behavior.primary_behavior
            role = self._infer_role(b_enum)

            if track.behavior.threat_score > highest_score:
                highest_score = track.behavior.threat_score
                highest_level = track.behavior.threat_level
                primary_action = b_enum.value

            if b_enum == BehaviorType.WEAPON_THREAT:
                is_weapon_detected = True
                detected_weapon_types.append("TACTICAL_WEAPON_POSTURE")
                weapon_confidence = max(weapon_confidence, track.behavior.confidence)

            # Extract detailed kinematics and 17 COCO keypoints
            kinematics_data = extract_subject_kinematics(track)
            serialized_keypoints = [
                {
                    "id": kp.id,
                    "name": kp.name,
                    "x": round(float(kp.x), 1),
                    "y": round(float(kp.y), 1),
                    "confidence": round(float(kp.confidence), 3),
                }
                for kp in track.keypoints
            ]

            bx = int(track.bbox.x1)
            by = int(track.bbox.y1)
            bw = max(1, int(track.bbox.width))
            bh = max(1, int(track.bbox.height))

            subject_data = SubjectCropData(
                track_id=track.track_id,
                role=role,
                behavior=b_enum.value,
                threat_level=track.behavior.threat_level.value,
                threat_score=track.behavior.threat_score,
                confidence=float(track.detection_conf),
                bbox=[bx, by, int(track.bbox.x2), int(track.bbox.y2)],
                bbox_width=bw,
                bbox_height=bh,
                bbox_aspect_ratio=round(bh / bw, 2),
                bbox_area=bw * bh,
                dwell_time_seconds=float(getattr(track, "dwell_time_seconds", 0.0)),
                speed=float(getattr(track, "speed", 0.0)),
                velocity_vector=[float(v) for v in getattr(track, "velocity_vector", (0.0, 0.0))],
                kinematics=kinematics_data,
                keypoints=serialized_keypoints,
                crop_image_base64=crop_b64,
                crop_image_sha256=crop_sha256,
                crop_image_size_bytes=crop_size,
            )
            subject_crop_list.append(subject_data)

        # Build weapon summary
        weapon_info: Dict[str, Any] = {
            "is_weapon_detected": is_weapon_detected,
            "weapon_types": detected_weapon_types if detected_weapon_types else [],
            "confidence": round(weapon_confidence, 4),
            "description": "Tactical pointing or overhead strike stance detected" if is_weapon_detected else "No active weapon posture identified",
        }

        # Build audio info
        audio_info: Dict[str, Any] = {}
        if audio_result is not None:
            audio_info = {
                "is_audio_active": True,
                "audio_threat_detected": getattr(audio_result, "is_threat", False),
                "event_type": str(getattr(audio_result, "event_type", "NONE")),
                "confidence": round(float(getattr(audio_result, "confidence", 0.0)), 4),
                "rms_db": round(float(getattr(audio_result, "rms_db", 0.0)), 2),
            }
        else:
            audio_info = {"is_audio_active": False, "audio_threat_detected": False}

        event_id = f"EVT_{now_dt.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        payload = WebhookIncidentPayload(
            event_id=event_id,
            timestamp=iso_timestamp,
            timestamp_ms=timestamp_ms,
            camera=self.camera_config,
            primary_action=primary_action,
            threat_level=highest_level.value,
            threat_score=highest_score,
            is_urgent=(highest_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)),
            reasoning=f"Detected action: {primary_action} (threat score: {highest_score:.2f})",
            weapon=weapon_info,
            subjects=subject_crop_list,
            full_image=full_image_data,
            audio=audio_info,
            audit={
                "frame_index": analysis_result.frame_index,
                "human_count": analysis_result.human_count,
                "hash_algorithm": "SHA-256 (RAW_JPEG_BYTES + TIMESTAMP_MS)",
                "anti_noise_filtering": {
                    "enabled": self.filter_noise,
                    "min_conf": self.min_detection_conf,
                    "min_bbox_area": self.min_bbox_area,
                    "cooldown_seconds": self.cooldown_seconds,
                    "filtered_noise_count": self.filtered_noise_count,
                },
                "verification_status": "AI_AUTO_DETECTED_PENDING_SOC_CONFIRMATION",
            },
        )

        payload_dict = payload.to_dict()

        # Enqueue non-blocking
        try:
            self.queue.put_nowait(payload_dict)
            return True
        except queue.Full:
            self.dropped_count += 1
            # Drop the oldest event in queue to accommodate the latest critical event
            try:
                _ = self.queue.get_nowait()
                self.queue.put_nowait(payload_dict)
                logger.warning("Webhook queue was full: dropped oldest event to enqueue %s", event_id)
                return True
            except (queue.Empty, queue.Full):
                logger.error("Failed to enqueue event %s: queue contention", event_id)
                return False

    def _satisfies_min_threat(self, threat_level: ThreatLevel) -> bool:
        """Check if threat_level meets the configured minimum filter."""
        if self.min_threat_level == "ALL":
            return True
        rank_map = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }
        min_rank = rank_map.get(self.min_threat_level, 1)
        curr_rank = rank_map.get(threat_level.value, 1)
        return curr_rank >= min_rank

    @staticmethod
    def _infer_role(behavior: BehaviorType) -> str:
        """Infer presumptive role based on kinematic behavior."""
        if behavior in (
            BehaviorType.WEAPON_THREAT,
            BehaviorType.FIGHTING,
            BehaviorType.SNATCHING,
            BehaviorType.PURSUIT,
            BehaviorType.RESTRAINING,
            BehaviorType.SURROUNDING,
            BehaviorType.INTRUSION,
        ):
            return "suspect"
        elif behavior in (BehaviorType.HANDS_UP, BehaviorType.FALLEN):
            return "victim"
        elif behavior in (BehaviorType.RUNNING, BehaviorType.CROUCHING, BehaviorType.LOITERING):
            return "participant"
        return "bystander"

    def _worker_loop(self) -> None:
        """Continuous background loop processing queued incident events."""
        while not self._stop_event.is_set():
            try:
                payload_dict = self.queue.get(timeout=0.25)
            except queue.Empty:
                continue

            if payload_dict is None:  # Sentinel to terminate
                break

            self._send_post_with_retry(payload_dict)
            self.queue.task_done()

    def _send_post_with_retry(self, payload: Dict[str, Any]) -> bool:
        """Send HTTP POST with exponential backoff and timeout."""
        if not self.server_url:
            return False

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "UrbanSafety-AI-SOC/2.0 WebhookDispatcher",
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for attempt in range(1, self.max_retries + 2):
            try:
                if HAS_REQUESTS:
                    resp = requests.post(
                        self.server_url,
                        data=body_bytes,
                        headers=headers,
                        timeout=self.timeout,
                    )
                    self.last_status_code = resp.status_code
                    if 200 <= resp.status_code < 300:
                        self.dispatched_count += 1
                        logger.debug("Successfully dispatched event %s (HTTP %d)", payload.get("event_id"), resp.status_code)
                        return True
                    else:
                        logger.warning(
                            "Webhook HTTP %d from %s (attempt %d/%d)",
                            resp.status_code, self.server_url, attempt, self.max_retries + 1,
                        )
                else:
                    # Fallback using urllib.request
                    req = urllib.request.Request(
                        self.server_url,
                        data=body_bytes,
                        headers=headers,
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        self.last_status_code = resp.status
                        if 200 <= resp.status < 300:
                            self.dispatched_count += 1
                            return True

            except Exception as e:
                self.last_error_message = str(e)
                logger.warning(
                    "Webhook POST failed to %s on attempt %d/%d: %s",
                    self.server_url, attempt, self.max_retries + 1, e,
                )

            if attempt <= self.max_retries and not self._stop_event.is_set():
                time.sleep(0.25 * attempt)

        self.failed_count += 1
        return False

    def shutdown(self, timeout: float = 2.0) -> None:
        """Gracefully stop worker thread and flush pending queue."""
        logger.info("Shutting down WebhookDispatcher...")
        self._stop_event.set()
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            pass

        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
        logger.info(
            "WebhookDispatcher stopped. Total Dispatched: %d | Failed: %d | Dropped: %d | Filtered Noise: %d",
            self.dispatched_count, self.failed_count, self.dropped_count, self.filtered_noise_count,
        )
