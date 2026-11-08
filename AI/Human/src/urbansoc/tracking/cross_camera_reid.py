"""Cross-Camera Re-Identification and Multi-Camera Global Identity Tracking Module.

Provides robust cross-camera tracking, appearance matching, and seamless handover
across camera topology zones without requiring heavy deep neural network overhead.
"""

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO

logger = logging.getLogger("urbansoc.tracking.cross_camera_reid")


@dataclass
class ReIDAppearanceSignature:
    """Multimodal appearance and biomechanical signature of a tracked individual."""
    upper_body_hist: np.ndarray          # HSV histogram (H: 16 bins, S: 8 bins)
    lower_body_hist: np.ndarray          # HSV histogram (H: 16 bins, S: 8 bins)
    full_body_hist: np.ndarray           # HSV histogram (H: 16 bins, S: 8 bins)
    aspect_ratio: float                  # Height / Width ratio
    relative_height: float               # Height normalized to frame height
    spine_angle: float = 0.0             # Spine inclination in degrees
    speed: float = 0.0                   # Movement velocity magnitude
    velocity_vector: Tuple[float, float] = (0.0, 0.0)
    dominant_colors: List[str] = field(default_factory=list)

    def compute_similarity(self, other: "ReIDAppearanceSignature") -> float:
        """Compute multi-factor appearance similarity score between two signatures in [0.0, 1.0]."""
        if other is None:
            return 0.0

        # 1. Upper body color correlation (HSV)
        upper_sim = float(cv2.compareHist(
            self.upper_body_hist,
            other.upper_body_hist,
            cv2.HISTCMP_CORREL,
        ))
        upper_score = max(0.0, min(1.0, (upper_sim + 1.0) / 2.0))

        # 2. Lower body color correlation (HSV)
        lower_sim = float(cv2.compareHist(
            self.lower_body_hist,
            other.lower_body_hist,
            cv2.HISTCMP_CORREL,
        ))
        lower_score = max(0.0, min(1.0, (lower_sim + 1.0) / 2.0))

        # 3. Full body color correlation (HSV)
        full_sim = float(cv2.compareHist(
            self.full_body_hist,
            other.full_body_hist,
            cv2.HISTCMP_CORREL,
        ))
        full_score = max(0.0, min(1.0, (full_sim + 1.0) / 2.0))

        # 4. Aspect Ratio & Anthropometric Morphological Consistency
        ar1 = max(0.1, self.aspect_ratio)
        ar2 = max(0.1, other.aspect_ratio)
        ar_score = max(0.0, 1.0 - (abs(ar1 - ar2) / max(ar1, ar2)))

        # Weighted combination: upper body 45%, lower body 35%, full body 10%, morphology 10%
        total_score = (
            0.45 * upper_score
            + 0.35 * lower_score
            + 0.10 * full_score
            + 0.10 * ar_score
        )
        return float(round(total_score, 4))


def _compute_hsv_histogram(image_bgr: np.ndarray, h_bins: int = 16, s_bins: int = 8) -> np.ndarray:
    """Compute normalized 2D HSV color histogram (H and S channels) for illumination resilience."""
    if image_bgr is None or image_bgr.size == 0 or image_bgr.shape[0] < 4 or image_bgr.shape[1] < 4:
        hist = np.zeros((h_bins, s_bins), dtype=np.float32)
        hist[0, 0] = 1.0
        return hist

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [h_bins, s_bins], [0, 180, 0, 256])
    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return hist.astype(np.float32)


def extract_appearance_signature(
    crop_bgr: np.ndarray,
    bbox: BBox,
    frame_shape: Optional[Tuple[int, int]] = None,
    keypoints: Optional[List[KeypointCOCO]] = None,
    velocity_vector: Tuple[float, float] = (0.0, 0.0),
    speed: float = 0.0,
) -> ReIDAppearanceSignature:
    """Extract fast and robust appearance and anthropometric signature from suspect crop."""
    h_box = max(1.0, float(bbox.height))
    w_box = max(1.0, float(bbox.width))
    aspect_ratio = float(round(h_box / w_box, 2))

    frame_h = float(frame_shape[0]) if frame_shape and frame_shape[0] > 0 else 720.0
    relative_height = float(round(h_box / frame_h, 3))

    if crop_bgr is not None and crop_bgr.size > 0:
        h, w = crop_bgr.shape[:2]
        split_y = max(1, int(h * 0.50))
        upper_img = crop_bgr[0:split_y, 0:w]
        lower_img = crop_bgr[split_y:h, 0:w]

        upper_hist = _compute_hsv_histogram(upper_img)
        lower_hist = _compute_hsv_histogram(lower_img)
        full_hist = _compute_hsv_histogram(crop_bgr)
    else:
        upper_hist = np.zeros((16, 8), dtype=np.float32)
        lower_hist = np.zeros((16, 8), dtype=np.float32)
        full_hist = np.zeros((16, 8), dtype=np.float32)

    # Spine angle calculation if keypoints are available
    spine_angle = 0.0
    if keypoints:
        kp_map = {kp.id: kp for kp in keypoints if kp.confidence >= 0.25}
        mid_s_y = None
        mid_h_y = None
        if 5 in kp_map and 6 in kp_map:  # Left & Right Shoulders
            mid_s_y = (kp_map[5].y + kp_map[6].y) / 2.0
            mid_s_x = (kp_map[5].x + kp_map[6].x) / 2.0
        if 11 in kp_map and 12 in kp_map:  # Left & Right Hips
            mid_h_y = (kp_map[11].y + kp_map[12].y) / 2.0
            mid_h_x = (kp_map[11].x + kp_map[12].x) / 2.0

        if mid_s_y is not None and mid_h_y is not None:
            dy = mid_s_y - mid_h_y
            dx = mid_s_x - mid_h_x
            mag = math.hypot(dx, dy)
            if mag > 1e-4:
                cos_ang = max(-1.0, min(1.0, -dy / mag))
                spine_angle = float(round(math.degrees(math.acos(cos_ang)), 2))

    return ReIDAppearanceSignature(
        upper_body_hist=upper_hist,
        lower_body_hist=lower_hist,
        full_body_hist=full_hist,
        aspect_ratio=aspect_ratio,
        relative_height=relative_height,
        spine_angle=spine_angle,
        speed=speed,
        velocity_vector=velocity_vector,
    )


@dataclass
class GlobalSubjectProfile:
    """Master identity profile tracking an individual across multiple camera views."""
    global_id: str                               # Unified ID: e.g. "PERSON_001"
    origin_camera_id: str                        # Camera where subject first appeared
    current_camera_id: str                       # Current camera actively viewing subject
    current_local_track_id: int                  # Local track_id on current camera
    first_seen_time: float                       # Epoch timestamp of first sighting
    last_seen_time: float                        # Epoch timestamp of most recent sighting
    active_threat_level: ThreatLevel = ThreatLevel.LOW
    highest_threat_score: float = 0.0
    primary_action: str = "NORMAL"
    signatures: List[ReIDAppearanceSignature] = field(default_factory=list)
    travel_chain: List[Dict[str, Any]] = field(default_factory=list)
    expected_next_cameras: List[Dict[str, Any]] = field(default_factory=list)
    last_crop_b64: Optional[str] = None

    @property
    def latest_signature(self) -> Optional[ReIDAppearanceSignature]:
        return self.signatures[-1] if self.signatures else None

    @property
    def travel_path_summary(self) -> str:
        """Return human-readable camera transition path, e.g. 'CAM_01 -> CAM_02'."""
        if not self.travel_chain:
            return self.origin_camera_id
        cams = [entry.get("camera_id", "UNKNOWN") for entry in self.travel_chain]
        # Remove consecutive duplicates
        cleaned = [cams[0]]
        for c in cams[1:]:
            if c != cleaned[-1]:
                cleaned.append(c)
        return " -> ".join(cleaned)


class CrossCameraReIDCoordinator:
    """Centralized coordinator for cross-camera re-identification and unified identity management."""

    def __init__(
        self,
        match_threshold: float = 0.60,
        min_transit_seconds: float = 0.5,
        max_transit_seconds: float = 90.0,
    ) -> None:
        self.match_threshold = match_threshold
        self.min_transit_seconds = min_transit_seconds
        self.max_transit_seconds = max_transit_seconds

        self._lock = threading.Lock()
        self._global_counter = 0
        # global_id -> GlobalSubjectProfile
        self.global_profiles: Dict[str, GlobalSubjectProfile] = {}
        # (camera_id, local_track_id) -> global_id
        self.camera_to_global: Dict[Tuple[str, int], str] = {}

    def _generate_global_id(self) -> str:
        """Mint a fresh, sequential unified identity."""
        self._global_counter += 1
        return f"PERSON_{self._global_counter:03d}"

    def match_track(
        self,
        camera_id: str,
        candidate_sig: ReIDAppearanceSignature,
        now: float,
    ) -> Tuple[Optional[str], float]:
        """Find the best matching active global profile from other cameras within the transit time window."""
        best_id: Optional[str] = None
        best_score = 0.0

        for g_id, profile in self.global_profiles.items():
            # Skip if this profile is already actively mapped on the SAME camera to a different track
            if profile.current_camera_id == camera_id and (now - profile.last_seen_time) < 2.0:
                continue

            # Spatial-Temporal transit time check
            dt = now - profile.last_seen_time
            if dt < self.min_transit_seconds or dt > self.max_transit_seconds:
                continue

            # Temporal feasibility score (higher if within reasonable transit window 2s - 25s)
            if 2.0 <= dt <= 25.0:
                time_weight = 1.0
            else:
                time_weight = max(0.60, 1.0 - (dt / self.max_transit_seconds))

            # Appearance similarity
            latest_sig = profile.latest_signature
            if latest_sig is None:
                continue

            app_score = candidate_sig.compute_similarity(latest_sig)
            combined_score = (app_score * 0.85) + (time_weight * 0.15)

            if combined_score > best_score:
                best_score = combined_score
                best_id = g_id

        if best_score >= self.match_threshold:
            return best_id, best_score

        return None, best_score

    def register_or_update_track(
        self,
        camera_id: str,
        track: HumanPoseTrack,
        frame_bgr: Optional[np.ndarray] = None,
        timestamp: Optional[float] = None,
        handover_token: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, float]:
        """Register a new local track or update an existing track, returning (global_id, confidence).

        Guarantees that when a person transitions between cameras, their unified global_id is preserved.
        """
        now = time.time() if (timestamp is None or timestamp <= 0) else timestamp
        key = (camera_id, track.track_id)

        with self._lock:
            # 1. Existing mapping on this camera: update existing global profile
            if key in self.camera_to_global:
                g_id = self.camera_to_global[key]
                if g_id in self.global_profiles:
                    profile = self.global_profiles[g_id]
                    profile.last_seen_time = now
                    profile.current_camera_id = camera_id
                    profile.current_local_track_id = track.track_id

                    # Inherit/upgrade threat level
                    t_rank = {ThreatLevel.LOW: 1, ThreatLevel.MEDIUM: 2, ThreatLevel.HIGH: 3, ThreatLevel.CRITICAL: 4}
                    if t_rank.get(track.behavior.threat_level, 1) > t_rank.get(profile.active_threat_level, 1):
                        profile.active_threat_level = track.behavior.threat_level
                    profile.highest_threat_score = max(profile.highest_threat_score, track.behavior.threat_score)
                    if track.behavior.primary_behavior.value != "NORMAL":
                        profile.primary_action = track.behavior.primary_behavior.value

                    # Update travel chain entry
                    if profile.travel_chain and profile.travel_chain[-1]["camera_id"] == camera_id:
                        profile.travel_chain[-1]["last_seen"] = now
                    else:
                        profile.travel_chain.append({"camera_id": camera_id, "first_seen": now, "last_seen": now})

                    track.global_id = g_id
                    track.reid_confidence = 1.0
                    return g_id, 1.0

            # 2. New track on this camera: Extract appearance signature and attempt matching
            crop_img = None
            if frame_bgr is not None and frame_bgr.size > 0:
                h, w = frame_bgr.shape[:2]
                bx1 = max(0, int(track.bbox.x1))
                by1 = max(0, int(track.bbox.y1))
                bx2 = min(w, int(track.bbox.x2))
                by2 = min(h, int(track.bbox.y2))
                if bx2 > bx1 and by2 > by1:
                    crop_img = frame_bgr[by1:by2, bx1:bx2].copy()

            frame_shape = frame_bgr.shape[:2] if frame_bgr is not None else (720, 1280)
            sig = extract_appearance_signature(
                crop_bgr=crop_img,
                bbox=track.bbox,
                frame_shape=frame_shape,
                keypoints=track.keypoints,
                velocity_vector=getattr(track, "velocity_vector", (0.0, 0.0)),
                speed=float(getattr(track, "speed", 0.0)),
            )

            matched_id, confidence = self.match_track(camera_id, sig, now)

            if matched_id is not None:
                # Match found with existing global profile from another camera!
                g_id = matched_id
                profile = self.global_profiles[g_id]
                prev_cam = profile.current_camera_id
                profile.current_camera_id = camera_id
                profile.current_local_track_id = track.track_id
                profile.last_seen_time = now
                profile.signatures.append(sig)
                if len(profile.signatures) > 10:
                    profile.signatures.pop(0)

                # Record transition leg
                profile.travel_chain.append({"camera_id": camera_id, "first_seen": now, "last_seen": now})

                # Threat inheritance: Inherit higher threat state across camera boundaries
                t_rank = {ThreatLevel.LOW: 1, ThreatLevel.MEDIUM: 2, ThreatLevel.HIGH: 3, ThreatLevel.CRITICAL: 4}
                if t_rank.get(profile.active_threat_level, 1) > t_rank.get(track.behavior.threat_level, 1):
                    track.behavior.threat_level = profile.active_threat_level
                    track.behavior.threat_score = max(track.behavior.threat_score, profile.highest_threat_score)
                    if profile.primary_action != "NORMAL" and track.behavior.primary_behavior == BehaviorType.NORMAL:
                        try:
                            track.behavior.primary_behavior = BehaviorType(profile.primary_action)
                        except ValueError:
                            pass

                self.camera_to_global[key] = g_id
                track.global_id = g_id
                track.reid_confidence = confidence

                logger.info(
                    "[REID MATCH] Camera %s Local #%d matched to existing %s (from %s, conf: %.2f)",
                    camera_id, track.track_id, g_id, prev_cam, confidence,
                )
                return g_id, confidence

            # 3. No match found: Mint brand-new global profile
            g_id = self._generate_global_id()
            profile = GlobalSubjectProfile(
                global_id=g_id,
                origin_camera_id=camera_id,
                current_camera_id=camera_id,
                current_local_track_id=track.track_id,
                first_seen_time=now,
                last_seen_time=now,
                active_threat_level=track.behavior.threat_level,
                highest_threat_score=track.behavior.threat_score,
                primary_action=track.behavior.primary_behavior.value,
                signatures=[sig],
                travel_chain=[{"camera_id": camera_id, "first_seen": now, "last_seen": now}],
            )
            self.global_profiles[g_id] = profile
            self.camera_to_global[key] = g_id
            track.global_id = g_id
            track.reid_confidence = 1.0

            logger.info("[REID NEW] Camera %s Local #%d assigned new %s", camera_id, track.track_id, g_id)
            return g_id, 1.0

    def get_profile(self, global_id: str) -> Optional[GlobalSubjectProfile]:
        with self._lock:
            return self.global_profiles.get(global_id)

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "global_id": p.global_id,
                    "origin_camera": p.origin_camera_id,
                    "current_camera": p.current_camera_id,
                    "current_local_track_id": p.current_local_track_id,
                    "threat_level": p.active_threat_level.value,
                    "threat_score": round(p.highest_threat_score, 2),
                    "primary_action": p.primary_action,
                    "travel_path": p.travel_path_summary,
                    "first_seen": datetime.fromtimestamp(p.first_seen_time).isoformat(),
                    "last_seen": datetime.fromtimestamp(p.last_seen_time).isoformat(),
                }
                for p in self.global_profiles.values()
            ]
