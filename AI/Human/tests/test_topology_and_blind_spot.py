"""Comprehensive Unit and Integration tests for Multi-Camera Named Topology,
12 Behavioral Analytics, Operator Incident Memory Suppression, and 5-Factor Blind-Spot Reasoning Engine.

Strictly adheres to AGENTS.md requirements:
- CD-01, CD-02: Strict Architectural Lock
- CD-04: Operational HITL Integrity (max state: AWAITING_OPERATOR_VERIFICATION)
- CD-05: >= 30 test cases for rock-solid stability
"""

import math
import time
from typing import Any, Dict, List

import numpy as np
import pytest

from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
from urbansoc.behavior.twelve_actions import (
    ACTION_WEIGHTS,
    ALL_TWELVE_ACTIONS,
    TwelveBehaviorAndThreatEngine,
)
from urbansoc.topology.blind_spot_reasoner import FiveFactorBlindSpotReasoner
from urbansoc.topology.incident_memory import IncidentMemoryEngine, compute_iou
from urbansoc.topology.models import (
    BlindSpotRoute,
    BlindSpotZone,
    ExitGateConfig,
    NamedCameraNode,
)
from urbansoc.topology.registry import (
    NamedCameraRegistry,
    compute_geographic_bearing,
    compute_haversine_distance_meters,
)


# ==============================================================================
# 1. NAMED CAMERA REGISTRY & TOPOLOGY TESTS
# ==============================================================================

class TestNamedCameraRegistry:
    @pytest.fixture
    def registry(self) -> NamedCameraRegistry:
        return NamedCameraRegistry()

    def test_default_cameras_count(self, registry: NamedCameraRegistry) -> None:
        cameras = list(registry.cameras.values())
        assert len(cameras) >= 4
        cam_ids = [c.camera_id for c in cameras]
        assert "CAM_01" in cam_ids
        assert "CAM_02" in cam_ids
        assert "CAM_03" in cam_ids
        assert "CAM_04" in cam_ids

    def test_lookup_camera_by_id(self, registry: NamedCameraRegistry) -> None:
        cam1 = registry.get_camera("CAM_01")
        assert cam1 is not None
        assert "Chu Văn An" in cam1.camera_name
        assert cam1.gps_lat == 10.803450
        assert cam1.gps_lng == 106.702310

    def test_lookup_camera_by_name(self, registry: NamedCameraRegistry) -> None:
        cam2 = registry.get_camera("Đinh Bộ Lĩnh")
        assert cam2 is not None
        assert cam2.camera_id == "CAM_02"

    def test_lookup_camera_fallback_id(self, registry: NamedCameraRegistry) -> None:
        cam = registry.get_camera("Hẻm 12")
        assert cam is not None
        assert cam.camera_id == "CAM_02"

    def test_unknown_camera_returns_none(self, registry: NamedCameraRegistry) -> None:
        assert registry.get_camera("UNKNOWN_CAM_99") is None

    def test_haversine_distance_calculation(self) -> None:
        # Distance between CAM_01 and CAM_02 (~100 meters)
        d = compute_haversine_distance_meters(
            10.803450, 106.702310, 10.803200, 106.703200
        )
        assert 80.0 < d < 120.0

    def test_haversine_distance_zero_for_same_point(self) -> None:
        d = compute_haversine_distance_meters(10.8, 106.7, 10.8, 106.7)
        assert d == 0.0

    def test_compass_bearing_cardinal_directions(self) -> None:
        # Due North
        b_north = compute_geographic_bearing(10.0, 106.0, 11.0, 106.0)
        assert abs(b_north - 0.0) < 1.0 or abs(b_north - 360.0) < 1.0

        # Due East
        b_east = compute_geographic_bearing(10.0, 106.0, 10.0, 107.0)
        assert abs(b_east - 90.0) < 1.0

        # Due South
        b_south = compute_geographic_bearing(11.0, 106.0, 10.0, 106.0)
        assert abs(b_south - 180.0) < 1.0

        # Due West
        b_west = compute_geographic_bearing(10.0, 107.0, 10.0, 106.0)
        assert abs(b_west - 270.0) < 1.0

    def test_match_exit_gate_by_bounding_box(self, registry: NamedCameraRegistry) -> None:
        # CAM_01 EAST_ALLEY_GATE polygon is [(0.75, 0.20), (1.0, 0.20), (1.0, 0.95), (0.75, 0.95)]
        gate = registry.match_exit_gate(
            camera_id_or_name="CAM_01",
            bbox_norm=(0.80, 0.40, 0.90, 0.60),
            velocity_vector=(0.0, 0.0),
        )
        assert gate is not None
        assert gate.gate_id == "EAST_ALLEY_GATE"
        assert gate.connected_blind_spot_id == "BS_ZONE_01"

    def test_match_exit_gate_by_velocity_heading(self, registry: NamedCameraRegistry) -> None:
        # Suspect near right edge (x >= 0.88) moving East (vx=1.0)
        gate = registry.match_exit_gate(
            camera_id_or_name="CAM_01",
            bbox_norm=(0.88, 0.45, 0.96, 0.85),
            velocity_vector=(1.0, 0.0),
        )
        assert gate is not None
        assert gate.gate_id == "EAST_ALLEY_GATE"

    def test_match_exit_gate_fallback_default(self, registry: NamedCameraRegistry) -> None:
        # Stationary target in dead center with zero velocity
        gate = registry.match_exit_gate(
            camera_id_or_name="CAM_01",
            bbox_norm=(0.48, 0.48, 0.52, 0.52),
            velocity_vector=(0.0, 0.0),
        )
        assert gate is not None
        assert gate.gate_id in ("EAST_ALLEY_GATE", "SOUTH_STREET_EDGE")

    def test_blind_spot_zone_lookup(self, registry: NamedCameraRegistry) -> None:
        zone = registry.get_blind_spot_zone("BS_ZONE_01")
        assert zone is not None
        assert len(zone.routes) >= 2
        assert zone.routes[0].target_camera_id == "CAM_02"
        assert zone.has_dumping_spots is True


# ==============================================================================
# 2. OPERATOR INCIDENT MEMORY & FALSE POSITIVE SUPPRESSION TESTS
# ==============================================================================

class TestIncidentMemoryEngine:
    @pytest.fixture
    def memory_engine(self) -> IncidentMemoryEngine:
        return IncidentMemoryEngine()

    def test_iou_calculation_identical_boxes(self) -> None:
        box = (0.2, 0.3, 0.6, 0.7)
        assert compute_iou(box, box) == 1.0

    def test_iou_calculation_disjoint_boxes(self) -> None:
        box1 = (0.0, 0.0, 0.2, 0.2)
        box2 = (0.5, 0.5, 0.8, 0.8)
        assert compute_iou(box1, box2) == 0.0

    def test_iou_calculation_partial_overlap(self) -> None:
        box1 = (0.0, 0.0, 0.6, 0.6)
        box2 = (0.3, 0.3, 0.9, 0.9)
        iou = compute_iou(box1, box2)
        assert 0.14 < iou < 0.15

    def test_suppress_fp_rule_001_high_iou(self, memory_engine: IncidentMemoryEngine) -> None:
        # FP_RULE_001 is on CAM_01, bbox [0.15, 0.40, 0.35, 0.75], label RESTRAINING
        suppressed, rule_id, reason = memory_engine.check_suppression(
            camera_name="CAM_01 - Cổng Trường Chu Văn An",
            detected_label="RESTRAINING",
            bbox_norm=(0.16, 0.41, 0.34, 0.74),
            context_text="School gate students greeting",
        )
        assert suppressed is True
        assert rule_id == "FP_RULE_001"
        assert "học sinh" in reason.lower()

    def test_suppress_fp_rule_002_by_context_keyword(self, memory_engine: IncidentMemoryEngine) -> None:
        # FP_RULE_002 is on CAM_02, label WEAPON_THREAT, keyword "umbrella", "ô dù"
        suppressed, rule_id, reason = memory_engine.check_suppression(
            camera_name="CAM_02 - Hẻm 12 Đinh Bộ Lĩnh",
            detected_label="WEAPON_THREAT",
            bbox_norm=(0.1, 0.1, 0.4, 0.4),
            context_text="Người dân cầm dù che mưa ô dù",
        )
        assert suppressed is True
        assert rule_id == "FP_RULE_002"
        assert "dù che mưa" in reason.lower() or "hung khí" in reason.lower()

    def test_no_suppression_when_camera_mismatched(self, memory_engine: IncidentMemoryEngine) -> None:
        suppressed, rule_id, _ = memory_engine.check_suppression(
            camera_name="CAM_04 - Ngã Tư Nguyễn Xí",
            detected_label="RESTRAINING",
            bbox_norm=(0.15, 0.40, 0.35, 0.75),
        )
        assert suppressed is False
        assert rule_id is None

    def test_no_suppression_when_label_mismatched(self, memory_engine: IncidentMemoryEngine) -> None:
        suppressed, rule_id, _ = memory_engine.check_suppression(
            camera_name="CAM_01 - Cổng Trường Chu Văn An",
            detected_label="FIGHTING",  # Rule 001 targets RESTRAINING, not FIGHTING
            bbox_norm=(0.16, 0.41, 0.34, 0.74),
        )
        assert suppressed is False
        assert rule_id is None

    def test_no_suppression_when_iou_too_low(self, memory_engine: IncidentMemoryEngine) -> None:
        suppressed, rule_id, _ = memory_engine.check_suppression(
            camera_name="CAM_01 - Cổng Trường Chu Văn An",
            detected_label="RESTRAINING",
            bbox_norm=(0.80, 0.10, 0.95, 0.30),  # Completely different corner
        )
        assert suppressed is False
        assert rule_id is None


# ==============================================================================
# 3. TWELVE BEHAVIORS & DYNAMIC THREAT STATE MACHINE TESTS
# ==============================================================================

class TestTwelveBehaviorAndThreatEngine:
    @pytest.fixture
    def engine(self) -> TwelveBehaviorAndThreatEngine:
        return TwelveBehaviorAndThreatEngine()

    def test_all_twelve_behaviors_registered(self) -> None:
        assert len(ALL_TWELVE_ACTIONS) == 12
        for b in ALL_TWELVE_ACTIONS:
            assert b in ACTION_WEIGHTS
            assert ACTION_WEIGHTS[b] > 0.0

    def test_score_escalation_single_action(self, engine: TwelveBehaviorAndThreatEngine) -> None:
        score, prev, curr, hist, vlm_rate = engine.update_threat(
            track_id="sub_1",
            detected_actions=["LOITERING"],
            timestamp_sec=100.0,
        )
        assert score >= ACTION_WEIGHTS["LOITERING"]
        assert curr in ("Low", "Medium")
        assert prev == "Low"

    def test_score_escalation_severe_crime(self, engine: TwelveBehaviorAndThreatEngine) -> None:
        score, prev, curr, hist, vlm_rate = engine.update_threat(
            track_id="sub_2",
            detected_actions=["FIGHTING", "WEAPON_THREAT"],
            timestamp_sec=100.0,
        )
        assert score >= 75.0
        assert curr in ("High", "Critical")
        assert vlm_rate <= 1.0

    def test_exponential_decay_formula(self, engine: TwelveBehaviorAndThreatEngine) -> None:
        # Initial score at t=10.0
        score_t0, _, _, _, _ = engine.update_threat(
            track_id="sub_3",
            detected_actions=["FLEEING"],
            timestamp_sec=10.0,
        )
        # Check decay at t=20.0s (dt=10s) without new actions
        decay_factor = math.exp(-0.08 * 10.0)
        expected_decayed = score_t0 * decay_factor

        score_t10, _, _, _, _ = engine.update_threat(
            track_id="sub_3",
            detected_actions=[],
            timestamp_sec=20.0,
        )
        assert abs(score_t10 - expected_decayed) < 1.0

    def test_false_positive_suppression_resets_threat_to_low(
        self, engine: TwelveBehaviorAndThreatEngine
    ) -> None:
        # First escalate
        engine.update_threat(
            track_id="sub_4",
            detected_actions=["FIGHTING"],
            timestamp_sec=1.0,
        )
        # Suppress
        score, prev, curr, hist, vlm_rate = engine.update_threat(
            track_id="sub_4",
            detected_actions=["FIGHTING"],
            false_positive_suppressed=True,
            timestamp_sec=2.0,
        )
        assert score == 0.0
        assert curr == "Low"
        assert vlm_rate == 5.0

    def test_anti_flapping_downgrade_requires_consecutive_frames(
        self, engine: TwelveBehaviorAndThreatEngine
    ) -> None:
        # Push to High
        engine.update_threat("sub_5", ["FIGHTING"], timestamp_sec=1.0)
        # 1 frame of zero action does NOT instantly plunge to Low
        _, _, curr_1, _, _ = engine.update_threat("sub_5", [], timestamp_sec=1.5)
        assert curr_1 != "Low"

    def test_soc_action_state_mapping(self) -> None:
        assert TwelveBehaviorAndThreatEngine.get_soc_action_state("Low") == "MONITORING_ONLY"
        assert TwelveBehaviorAndThreatEngine.get_soc_action_state("Medium") == "ENHANCED_TRACKING"
        assert TwelveBehaviorAndThreatEngine.get_soc_action_state("High") == "AWAITING_OPERATOR_VERIFICATION"
        assert TwelveBehaviorAndThreatEngine.get_soc_action_state("Critical") == "AWAITING_OPERATOR_VERIFICATION"

    def test_rule_hitl_never_auto_confirms(self, engine: TwelveBehaviorAndThreatEngine) -> None:
        # Maximum possible score
        score, _, curr, _, _ = engine.update_threat(
            track_id="sub_6",
            detected_actions=["FIGHTING", "WEAPON_THREAT", "SNATCHING"],
            timestamp_sec=1.0,
        )
        soc_state = TwelveBehaviorAndThreatEngine.get_soc_action_state(curr)
        assert soc_state == "AWAITING_OPERATOR_VERIFICATION"
        assert soc_state != "OPERATOR_CONFIRMED"


# ==============================================================================
# 4. FIVE-FACTOR BLIND-SPOT REASONING TESTS
# ==============================================================================

class TestFiveFactorBlindSpotReasoner:
    @pytest.fixture
    def registry(self) -> NamedCameraRegistry:
        return NamedCameraRegistry()

    @pytest.fixture
    def reasoner(self, registry: NamedCameraRegistry) -> FiveFactorBlindSpotReasoner:
        return FiveFactorBlindSpotReasoner(registry)

    def test_factor_1_biomechanics_hand_and_gait(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        profile = reasoner.infer_subject_tactical_profile(
            detected_action="SNATCHING",
            bbox_norm=(0.6, 0.4, 0.8, 0.8),
            velocity_vector=(2.5, 0.5),
            exit_velocity_mps=5.0,
        )
        assert profile.dominant_hand in ("RIGHT", "LEFT")
        assert profile.active_holding_hand in ("RIGHT_HAND", "LEFT_HAND")
        assert "bảo vệ tay giữ vật" in profile.gait_and_biomechanics or "sải chân" in profile.gait_and_biomechanics.lower()
        assert profile.exit_velocity_mps == 5.0

    def test_factor_2_psychological_state_panic(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        profile = reasoner.infer_subject_tactical_profile(
            detected_action="FLEEING",
            bbox_norm=(0.7, 0.3, 0.9, 0.7),
            velocity_vector=(3.0, 0.0),
            exit_velocity_mps=6.2,
        )
        assert profile.psychological_state == "HIGH_PANIC"
        assert "bộc phát" in profile.psychological_evidence.lower()

    def test_factor_2_psychological_state_calm(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        profile = reasoner.infer_subject_tactical_profile(
            detected_action="LOITERING",
            bbox_norm=(0.4, 0.4, 0.6, 0.8),
            velocity_vector=(0.2, 0.1),
            dwell_time_sec=45.0,
            pre_crime_loitering=True,
            exit_velocity_mps=2.0,
        )
        assert profile.psychological_state == "PREMEDITATED_CALM"
        assert "quan sát" in profile.psychological_evidence.lower()

    def test_factor_3_hidden_actions_prediction_panic(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        actions = reasoner.predict_hidden_actions(
            psychological_state="HIGH_PANIC",
            held_object="Túi xách cướp giật",
            detected_action="SNATCHING",
        )
        assert "EVIDENCE_DUMPING" in actions
        assert "CLOTHING_CHANGE" in actions or "FOOT_PURSUIT_SPRINT" in actions

    def test_factor_3_hidden_actions_prediction_weapon(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        actions = reasoner.predict_hidden_actions(
            psychological_state="PREMEDITATED_CALM",
            held_object="Dao găm / hung khí",
            detected_action="WEAPON_BRANDISHING",
        )
        assert "WEAPON_STASHING" in actions

    def test_factor_4_and_5_route_ranking_and_eta(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        result = reasoner.analyze_blind_spot_trajectory(
            origin_camera_id="CAM_01",
            detected_action="SNATCHING",
            bbox_norm=(0.85, 0.45, 0.95, 0.85),
            velocity_vector=(1.0, 0.0),  # heading East
            exit_velocity_mps=4.5,
        )
        assert result["is_triggered"] is True
        assert result["origin_camera_name"] == "CAM_01 - Cổng Trường Chu Văn An"
        assert result["exit_gate_on_origin_cam"] == "EAST_ALLEY_GATE"

        targets = result["predicted_next_cameras"]
        assert len(targets) > 0
        top = targets[0]
        assert top["target_camera_id"] == "CAM_02"
        assert top["expected_entry_gate_on_target_cam"] == "WEST_ALLEY_ENTRY"
        # ETA window verification
        eta_min, eta_max = top["estimated_arrival_seconds"]
        assert 0 < eta_min < eta_max
        assert len(top["expected_arrival_timestamp_window"]) == 2

    def test_probability_normalization_sums_to_one(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        result = reasoner.analyze_blind_spot_trajectory(
            origin_camera_id="CAM_01",
            detected_action="FLEEING",
            bbox_norm=(0.85, 0.45, 0.95, 0.85),
            velocity_vector=(1.0, 0.0),
        )
        targets = result["predicted_next_cameras"]
        prob_sum = sum(t["probability"] for t in targets)
        assert abs(prob_sum - 1.0) < 0.05

    def test_reid_handover_token_generation(
        self, reasoner: FiveFactorBlindSpotReasoner
    ) -> None:
        result = reasoner.analyze_blind_spot_trajectory(
            origin_camera_id="CAM_02",
            detected_action="FLEEING",
            bbox_norm=(0.1, 0.3, 0.3, 0.8),
            velocity_vector=(-1.0, 0.0),
            visual_description="Đối tượng nam áo khoác đen, nón bảo hiểm đỏ",
        )
        token = result["cross_camera_reid_handover_token"]
        assert token["global_subject_tag"].startswith("SUBJECT_")
        assert "áo khoác đen" in token["visual_appearance_signature"]
        assert len(token["post_blind_spot_watch_notes"]) > 0


# ==============================================================================
# 5. NVIDIA VLM INTEGRATION & STRICT JSON SCHEMA (SECTION 6) TESTS
# ==============================================================================

class TestNvidiaVlmAndSectionSixSchema:
    @pytest.fixture
    def client(self) -> NvidiaVisionClient:
        return NvidiaVisionClient(api_key="")

    def test_strict_section_six_root_keys(self, client: NvidiaVisionClient) -> None:
        dummy = np.zeros((120, 160, 3), dtype=np.uint8)
        output = client.analyze_frame(
            frame=dummy,
            camera_id="CAM_01",
            action_hint="SNATCHING",
            bbox_norm=(0.80, 0.40, 0.90, 0.80),
            velocity_vector=(1.5, 0.0),
        )

        # Mandatory Section 6 Top-Level Keys
        assert "frame_id" in output
        assert "timestamp" in output
        assert "active_camera" in output
        assert "evaluated_subjects" in output
        assert "operator_dashboard_directives" in output

        # Active camera structure
        cam = output["active_camera"]
        assert cam["camera_id"] == "CAM_01"
        assert cam["camera_name"] == "CAM_01 - Cổng Trường Chu Văn An"
        assert "lat" in cam["gps_coordinates"]
        assert "lng" in cam["gps_coordinates"]

        # Evaluated subjects structure
        subs = output["evaluated_subjects"]
        assert len(subs) >= 1
        s = subs[0]
        assert s["track_id"] == "1"
        assert s["false_positive_suppressed"] is False
        assert s["soc_action_state"] in ("MONITORING_ONLY", "ENHANCED_TRACKING", "AWAITING_OPERATOR_VERIFICATION")
        assert s["soc_action_state"] != "OPERATOR_CONFIRMED"

        # Multi-camera blind spot reasoning structure
        bs = s["multi_camera_blind_spot_reasoning"]
        assert bs["is_triggered"] is True
        assert bs["origin_camera_name"] == "CAM_01 - Cổng Trường Chu Văn An"
        assert bs["exit_gate_on_origin_cam"] == "EAST_ALLEY_GATE"
        assert len(bs["predicted_next_cameras"]) > 0
        assert "cross_camera_reid_handover_token" in bs

        # Operator directives structure
        directives = output["operator_dashboard_directives"]
        assert "highlight_camera_names_on_map" in directives
        assert "suggested_operator_focus" in directives

    def test_vlm_suppression_flow_via_analyze_frame(self, client: NvidiaVisionClient) -> None:
        dummy = np.zeros((120, 160, 3), dtype=np.uint8)
        # Coordinates matching FP_RULE_001
        output = client.analyze_frame(
            frame=dummy,
            camera_id="CAM_01",
            action_hint="RESTRAINING",
            bbox_norm=(0.16, 0.41, 0.34, 0.74),
        )

        s = output["evaluated_subjects"][0]
        assert s["false_positive_suppressed"] is True
        assert s["applied_memory_rule_id"] == "FP_RULE_001"
        assert s["current_threat_level"] == "Low"
        assert s["soc_action_state"] == "MONITORING_ONLY"
        assert output["threat_score"] == 0.0

    def test_backward_compatibility_fields_preserved(self, client: NvidiaVisionClient) -> None:
        dummy = np.zeros((80, 80, 3), dtype=np.uint8)
        output = client.analyze_frame(
            frame=dummy,
            camera_id="CAM_02",
            action_hint="FIGHTING",
        )

        assert "severity" in output
        assert "action_type" in output
        assert "threat_score" in output
        assert "confidence" in output
        assert "is_urgent" in output
        assert "situation_assessment" in output
        assert "intent_prediction" in output
        assert "recommended_action" in output
        assert "actors" in output
        assert "visual_cues" in output
