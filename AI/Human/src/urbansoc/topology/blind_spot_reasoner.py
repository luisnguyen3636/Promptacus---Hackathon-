"""Five-Factor Multi-Camera Blind-Spot Trajectory Reasoning Engine."""

from datetime import datetime, timezone, timedelta
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from urbansoc.topology.models import (
    BlindSpotRoute,
    PredictedTargetCamera,
    SubjectTacticalProfile,
)
from urbansoc.topology.registry import NamedCameraRegistry


class FiveFactorBlindSpotReasoner:
    """Master reasoning engine for predictive trajectory and handover across camera blind spots."""

    def __init__(self, registry: Optional[NamedCameraRegistry] = None) -> None:
        self.registry = registry or NamedCameraRegistry()

    def infer_subject_tactical_profile(
        self,
        detected_action: str,
        bbox_norm: Tuple[float, float, float, float] = (0.5, 0.5, 0.6, 0.8),
        velocity_vector: Tuple[float, float] = (0.0, 0.0),
        keypoints: Optional[List[Dict[str, Any]]] = None,
        exit_velocity_mps: float = 4.5,
        exit_heading_deg: float = 90.0,
        dwell_time_sec: float = 0.0,
        pre_crime_loitering: bool = False,
    ) -> SubjectTacticalProfile:
        """Expose tactical profile inference for testing and specialized analysis."""
        return self._evaluate_biomechanics_and_handedness(
            detected_action=detected_action,
            keypoints=keypoints or [],
            exit_velocity_mps=exit_velocity_mps,
            exit_heading_deg=exit_heading_deg,
            pre_crime_loitering=pre_crime_loitering,
            dwell_time_sec=dwell_time_sec,
        )

    def predict_hidden_actions(
        self,
        psychological_state: str,
        held_object: str = "",
        detected_action: str = "NORMAL",
    ) -> List[str]:
        """Predict plausible hidden actions in blind spot."""
        actions = []
        if detected_action in ("WEAPON_THREAT", "KNIFE_THREAT", "WEAPON_BRANDISHING"):
            actions.extend(["WEAPON_STASHING", "EVIDENCE_DUMPING"])
        elif detected_action == "SNATCHING":
            actions.extend(["EVIDENCE_DUMPING", "LOOT_EXTRACTION", "FOOT_PURSUIT_SPRINT"])
        elif detected_action == "FIGHTING":
            actions.extend(["FLEEING", "CLOTHING_CHANGE"])
        else:
            actions.append("FLEEING")

        if psychological_state == "HIGH_PANIC" and "EVIDENCE_DUMPING" not in actions:
            actions.append("EVIDENCE_DUMPING")
        if psychological_state == "HIGH_PANIC" and "CLOTHING_CHANGE" not in actions:
            actions.append("CLOTHING_CHANGE")
        return actions

    def analyze_blind_spot_trajectory(
        self,
        origin_camera_id: str,
        detected_action: str,
        bbox_norm: Tuple[float, float, float, float],
        velocity_vector: Tuple[float, float],
        keypoints: Optional[List[Dict[str, Any]]] = None,
        dwell_time_sec: float = 0.0,
        pre_crime_loitering: bool = False,
        exit_velocity_mps: float = 4.5,
        visual_description: str = "",
    ) -> Dict[str, Any]:
        """Execute the 5-factor blind-spot reasoning algorithm and generate detailed predictive report."""
        origin_node = self.registry.get_camera(origin_camera_id)
        origin_cam_name = origin_node.camera_name if origin_node else f"CAM_{origin_camera_id}"

        # 1. Match Exit Gate on Origin Camera
        exit_gate = self.registry.match_exit_gate(origin_camera_id, bbox_norm, velocity_vector)
        exit_gate_id = exit_gate.gate_id if exit_gate else "PERIMETER_EXIT_BOUNDARY"
        bs_zone_id = exit_gate.connected_blind_spot_id if exit_gate else "BS_ZONE_DEFAULT"
        exit_bearing_deg = exit_gate.compass_bearing_deg if exit_gate else 90.0

        bs_zone = self.registry.get_blind_spot_zone(bs_zone_id)
        bs_desc = bs_zone.description if bs_zone else "Hành lang khuất tầm nhìn tiếp giáp giữa các camera đích danh"

        # 2. Step 5.1: Biomechanics & Handedness Analysis
        tactical_profile = self._evaluate_biomechanics_and_handedness(
            detected_action=detected_action,
            keypoints=keypoints or [],
            exit_velocity_mps=exit_velocity_mps,
            exit_heading_deg=exit_bearing_deg,
            pre_crime_loitering=pre_crime_loitering,
            dwell_time_sec=dwell_time_sec,
        )

        # 3. Retrieve Candidate Routes to Connected Named Cameras
        routes = self.registry.resolve_connected_cameras(
            origin_camera_id=origin_camera_id,
            blind_spot_id=bs_zone_id,
            exit_heading_deg=exit_bearing_deg,
        )

        # 4. Step 5.2 - 5.5: Score each target camera and synthesize probabilities
        predicted_cameras = self._evaluate_and_rank_target_cameras(
            routes=routes,
            tactical_profile=tactical_profile,
            detected_action=detected_action,
            exit_velocity_mps=exit_velocity_mps,
            exit_heading_deg=exit_bearing_deg,
            origin_cam_name=origin_cam_name,
        )

        # 5. Build ReID Token
        now_dt = datetime.now(timezone.utc)
        reid_token = {
            "global_subject_tag": f"SUBJECT_{int(time.time())}_{tactical_profile.dominant_hand[:1]}",
            "visual_appearance_signature": visual_description or (
                f"Đối tượng sải chân dài, tay giữ đồ là {tactical_profile.active_holding_hand.lower()}, "
                f"dáng chạy hướng {exit_bearing_deg} độ"
            ),
            "post_blind_spot_watch_notes": (
                "Lưu ý cho Camera đón lõng: Đối tượng có thể đã cất giấu hung khí hoặc phi tang vật chứng trong hẻm"
                if detected_action in ("WEAPON_THREAT", "KNIFE_THREAT", "SNATCHING")
                else "Theo dõi sự xuất hiện tự nhiên từ cổng đón lõng dự kiến"
            ),
        }

        return {
            "is_triggered": True,
            "origin_camera_name": origin_cam_name,
            "exit_gate_on_origin_cam": exit_gate_id,
            "blind_spot_zone_id": bs_zone_id,
            "blind_spot_description": bs_desc,
            "subject_tactical_profile": {
                "dominant_hand": tactical_profile.dominant_hand,
                "active_holding_hand": tactical_profile.active_holding_hand,
                "held_object_description": tactical_profile.held_object_description,
                "gait_and_biomechanics": tactical_profile.gait_and_biomechanics,
                "psychological_state": tactical_profile.psychological_state,
                "psychological_evidence": tactical_profile.psychological_evidence,
                "exit_velocity_mps": tactical_profile.exit_velocity_mps,
                "exit_heading_compass_deg": tactical_profile.exit_heading_compass_deg,
            },
            "predicted_next_cameras": [
                {
                    "rank": p.rank,
                    "target_camera_id": p.target_camera_id,
                    "target_camera_name": p.target_camera_name,
                    "target_camera_location": p.target_camera_location,
                    "route_id": p.route_id,
                    "route_description": p.route_description,
                    "blind_spot_distance_meters": p.blind_spot_distance_meters,
                    "expected_entry_gate_on_target_cam": p.expected_entry_gate_on_target_cam,
                    "probability": p.probability,
                    "estimated_arrival_seconds": list(p.estimated_arrival_seconds),
                    "expected_arrival_timestamp_window": list(p.expected_arrival_timestamp_window),
                    "predicted_hidden_actions_in_blind_spot": p.predicted_hidden_actions_in_blind_spot,
                    "score_breakdown": p.score_breakdown,
                    "detailed_tactical_reasoning": p.detailed_tactical_reasoning,
                }
                for p in predicted_cameras
            ],
            "cross_camera_reid_handover_token": reid_token,
        }

    def _evaluate_biomechanics_and_handedness(
        self,
        detected_action: str,
        keypoints: List[Dict[str, Any]],
        exit_velocity_mps: float,
        exit_heading_deg: float,
        pre_crime_loitering: bool,
        dwell_time_sec: float,
    ) -> SubjectTacticalProfile:
        """Step 5.1 & 5.2: Biomechanics, Handedness & Psychological Profiling."""
        action = detected_action.upper()

        # Default hand inference
        dominant_hand = "RIGHT"
        active_holding = "NONE"
        held_desc = "Không phát hiện vật cầm cố định"

        if action in ("WEAPON_THREAT", "KNIFE_THREAT"):
            active_holding = "RIGHT_HAND"
            dominant_hand = "RIGHT"
            held_desc = "Dao hoặc hung khí sắc nhọn ở tay phải"
        elif action == "SNATCHING":
            active_holding = "LEFT_HAND"
            dominant_hand = "RIGHT"
            held_desc = "Túi xách / tài sản vừa cướp ôm chặt ở tay trái sát mạn sườn"
        elif action == "FIGHTING":
            active_holding = "BOTH_HANDS"
            dominant_hand = "RIGHT"
            held_desc = "Hai nắm đấm co thủ vùng mặt"

        # Gait and biomechanics
        if exit_velocity_mps > 4.5:
            gait = "Sải chân mở rộng tối đa, vai hơi chúi về phía trước, trọng tâm cơ thể dồn bảo vệ tay giữ vật"
        else:
            gait = "Bước đi nhanh dứt khoát, trục vai giữ thăng bằng ổn định"

        # Psychological state profiling (PANIC vs. PREMEDITATED)
        if pre_crime_loitering or dwell_time_sec > 25.0:
            psych_state = "PREMEDITATED_CALM"
            psych_evidence = (
                f"Có lịch sử quan sát/loitering kéo dài {dwell_time_sec:.0f}s trước khi hành động; "
                "chủ động quan sát lộ trình thoát, rẽ dứt khoát theo góc cua định trước."
            )
        else:
            psych_state = "HIGH_PANIC"
            psych_evidence = (
                "Hành động bộc phát không qua khảo sát; nhịp chạy nước rút gấp gáp, "
                "xu hướng lao theo lối thoát rộng và thẳng theo hiệu ứng đường hầm thị giác."
            )

        return SubjectTacticalProfile(
            dominant_hand=dominant_hand,
            active_holding_hand=active_holding,
            held_object_description=held_desc,
            gait_and_biomechanics=gait,
            psychological_state=psych_state,
            psychological_evidence=psych_evidence,
            exit_velocity_mps=round(exit_velocity_mps, 1),
            exit_heading_compass_deg=round(exit_heading_deg, 1),
        )

    def _evaluate_and_rank_target_cameras(
        self,
        routes: List[BlindSpotRoute],
        tactical_profile: SubjectTacticalProfile,
        detected_action: str,
        exit_velocity_mps: float,
        exit_heading_deg: float,
        origin_cam_name: str,
    ) -> List[PredictedTargetCamera]:
        """Steps 5.3 - 5.5: Multi-factor scoring, probability normalization, and ETA calculation."""
        if not routes:
            return []

        now_utc = datetime.now(timezone.utc)
        scored_routes = []

        # Predict hidden actions in blind spot
        hidden_actions = []
        extra_stop_delay_sec = 0
        if detected_action in ("WEAPON_THREAT", "KNIFE_THREAT"):
            hidden_actions = ["EVIDENCE_DUMPING", "WEAPON_CONCEALMENT"]
            extra_stop_delay_sec = 5  # Time to toss knife in dumpster
        elif detected_action == "SNATCHING":
            hidden_actions = ["LOOT_EXTRACTION", "VEHICLE_BOARDING"]
            extra_stop_delay_sec = 4
        elif detected_action == "FIGHTING":
            hidden_actions = ["FLEEING", "CLOTHING_ADJUSTMENT"]
        else:
            hidden_actions = ["FLEEING"]

        for route in routes:
            # Factor 1: Kinematic Alignment Score (Heading delta)
            heading_delta = abs((route.optimal_heading_deg - exit_heading_deg + 180) % 360 - 180)
            if heading_delta <= 45.0:
                kinematic_score = 0.90
            elif heading_delta <= 90.0:
                kinematic_score = 0.65
            else:
                kinematic_score = 0.30

            # Factor 2: Biomechanical Handedness Score
            # If turning left, free right hand can brace against walls/corners
            biomech_score = 0.75
            if tactical_profile.active_holding_hand == "LEFT_HAND" and heading_delta > 30.0:
                biomech_score = 0.85
            elif tactical_profile.active_holding_hand == "RIGHT_HAND":
                biomech_score = 0.80

            # Factor 3: Psychological Affinity Score
            # HIGH_PANIC prefers wide straight roads; PREMEDITATED prefers alleys & parking lots
            if tactical_profile.psychological_state == "HIGH_PANIC":
                if "WIDE_ROAD" in route.features or "SPEED_SPRINT" in route.features:
                    psych_score = 0.92
                else:
                    psych_score = 0.50
            else:  # PREMEDITATED_CALM
                if "PARKING_LOT" in route.features or "DARK_ALLEY" in route.features:
                    psych_score = 0.95
                else:
                    psych_score = 0.60

            # Factor 4: Tactical Post-Crime Score (needs trash bin or escape vehicle)
            tactical_score = 0.70
            if "EVIDENCE_DUMPING" in hidden_actions and "TRASH_BIN" in route.features:
                tactical_score += 0.20
            if "VEHICLE_BOARDING" in hidden_actions and "PARKING_LOT" in route.features:
                tactical_score += 0.20
            tactical_score = min(1.0, tactical_score)

            friction_penalty = route.friction_penalty

            raw_score = (
                kinematic_score * 0.30
                + biomech_score * 0.20
                + psych_score * 0.30
                + tactical_score * 0.20
                - friction_penalty
            )
            raw_score = max(0.05, raw_score)

            scored_routes.append({
                "route": route,
                "raw_score": raw_score,
                "breakdown": {
                    "kinematic_alignment_score": round(kinematic_score, 2),
                    "biomechanical_handedness_score": round(biomech_score, 2),
                    "psychological_affinity_score": round(psych_score, 2),
                    "tactical_post_crime_score": round(tactical_score, 2),
                    "topological_friction_penalty": round(friction_penalty, 2),
                },
            })

        # Probability normalization: sum(P) = 1.0
        total_raw = sum(item["raw_score"] for item in scored_routes)
        scored_routes.sort(key=lambda x: x["raw_score"], reverse=True)

        results: List[PredictedTargetCamera] = []
        for rank, item in enumerate(scored_routes, start=1):
            route = item["route"]
            prob = round(item["raw_score"] / total_raw, 2) if total_raw > 0 else 0.50

            # ETA calculation based on velocity + hidden action delay
            eff_velocity = max(2.5, exit_velocity_mps)
            base_transit_sec = route.distance_meters / eff_velocity
            eta_min = max(3, int(base_transit_sec + extra_stop_delay_sec * 0.5))
            eta_max = max(eta_min + 3, int(base_transit_sec * 1.35 + extra_stop_delay_sec))

            t_start = (now_utc + timedelta(seconds=eta_min)).isoformat()
            t_end = (now_utc + timedelta(seconds=eta_max)).isoformat()

            reasoning = (
                f"Dự báo đối tượng sẽ xuất hiện tại {route.target_camera_name} (Xác suất {int(prob * 100)}%) vì: "
                f"(1) {tactical_profile.psychological_state} phù hợp với tuyến đường {route.route_description}; "
                f"(2) Trọng tâm bảo vệ {tactical_profile.active_holding_hand.lower()} và quán tính hướng {exit_heading_deg}° "
                f"khớp cổng đón lõng {route.expected_entry_gate}; "
                f"(3) Cần {eta_min}-{eta_max}s qua vùng mù {route.distance_meters}m "
                f"(kèm thao tác ẩn: {', '.join(hidden_actions)})."
            )

            results.append(PredictedTargetCamera(
                rank=rank,
                target_camera_id=route.target_camera_id,
                target_camera_name=route.target_camera_name,
                target_camera_location=route.target_camera_location,
                route_id=route.route_id,
                route_description=route.route_description,
                blind_spot_distance_meters=route.distance_meters,
                expected_entry_gate_on_target_cam=route.expected_entry_gate,
                probability=prob,
                estimated_arrival_seconds=(eta_min, eta_max),
                expected_arrival_timestamp_window=(t_start, t_end),
                predicted_hidden_actions_in_blind_spot=hidden_actions,
                score_breakdown=item["breakdown"],
                detailed_tactical_reasoning=reasoning,
            ))

        return results
