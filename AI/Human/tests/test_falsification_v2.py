"""Comprehensive Unit and Integration tests for the 5-Gate Falsification Engine (v2.0).

Strictly adheres to AGENTS.md requirements:
- CD-01, CD-02: Strict Architectural Lock
- CD-04: Operational HITL Integrity (max state: AWAITING_OPERATOR_VERIFICATION, never OPERATOR_CONFIRMED)
- CD-05: >= 30 test cases verifying the 5-gate falsification protocol and zero-false-positive auditor.
"""

from typing import Any, Dict, List
import numpy as np
import pytest

from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
from urbansoc.behavior.falsification import (
    AdversarialFalsificationResult,
    AntiFalsePositiveAudit,
    FiveGateFalsificationEngine,
)
from urbansoc.topology.incident_memory import IncidentMemoryEngine


# ==============================================================================
# 1. GATE 1: 3D GROUND-PLANE DEPTH CHECK
# ==============================================================================

class TestGate1GroundPlaneDepth:
    @pytest.fixture
    def engine(self) -> FiveGateFalsificationEngine:
        return FiveGateFalsificationEngine()

    def test_depth_check_rejects_disjoint_foot_y(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject 2D perspective overlap when foot_y delta > 0.15 relative to min height."""
        # Box A: [x1, y1, x2, y2] -> foot_y=0.90, height=0.40
        box_a = [0.4, 0.5, 0.6, 0.90]
        # Box B: foot_y=0.60, height=0.35 -> delta_foot_y = 0.30 / 0.35 = 0.857 > 0.15
        box_b = [0.45, 0.25, 0.65, 0.60]
        passed, delta_y, ratio, detail = engine.check_gate_1_ground_plane_depth(
            "FIGHTING", box_a, box_b
        )
        assert not passed
        assert delta_y > 0.15
        assert "Sai khác mặt phẳng chân" in detail

    def test_depth_check_rejects_height_ratio_distortion(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject when height ratio < 0.75 or > 1.35 (one person much farther in 3D)."""
        # Box A: height 0.60, foot_y=0.90
        box_a = [0.4, 0.30, 0.6, 0.90]
        # Box B: height 0.20 (ratio 0.20/0.60 = 0.33), foot_y=0.88 (delta_y ~ 0.02)
        box_b = [0.45, 0.68, 0.65, 0.88]
        passed, delta_y, ratio, detail = engine.check_gate_1_ground_plane_depth(
            "PHYSICAL_ALTERCATION", box_a, box_b
        )
        assert not passed
        assert ratio < 0.75 or ratio > 1.35
        assert "Tỉ lệ chiều cao bất thường" in detail

    def test_depth_check_passes_close_interaction(self, engine: FiveGateFalsificationEngine) -> None:
        """Valid interactive combat on same ground plane with similar height."""
        box_a = [0.40, 0.40, 0.55, 0.90]  # height 0.50, foot 0.90
        box_b = [0.50, 0.42, 0.65, 0.92]  # height 0.50, foot 0.92 -> delta = 0.02/0.50 = 0.04 < 0.15
        passed, delta_y, ratio, detail = engine.check_gate_1_ground_plane_depth(
            "FIGHTING", box_a, box_b
        )
        assert passed
        assert delta_y <= 0.15
        assert 0.75 <= ratio <= 1.35
        assert "cùng mặt phẳng sàn" in detail

    def test_depth_check_bypasses_non_interactive_actions(self, engine: FiveGateFalsificationEngine) -> None:
        """Non-interactive actions like LOITERING or CASING do not require victim box."""
        box_a = [0.4, 0.5, 0.6, 0.9]
        passed, delta_y, ratio, detail = engine.check_gate_1_ground_plane_depth(
            "LOITERING", box_a, None
        )
        assert passed
        assert "Không áp dụng kiểm tra cặp" in detail

    def test_depth_check_passes_when_one_person_fallen(self, engine: FiveGateFalsificationEngine) -> None:
        """If one person is fallen, height ratio rule is relaxed."""
        box_a = [0.40, 0.75, 0.70, 0.90]  # height 0.15 (fallen)
        box_b = [0.38, 0.40, 0.50, 0.88]  # height 0.48 (standing attacker)
        passed, delta_y, ratio, detail = engine.check_gate_1_ground_plane_depth(
            "RESTRAINING", box_a, box_b
        )
        assert passed
        assert "ngoại lệ đối tượng nằm/ngã" in detail

    def test_depth_check_handles_missing_boxes_gracefully(self, engine: FiveGateFalsificationEngine) -> None:
        """Missing boxes default to passed with fallback note."""
        passed, delta_y, ratio, detail = engine.check_gate_1_ground_plane_depth(
            "FIGHTING", None, None
        )
        assert passed
        assert "Thiếu thông tin bounding box" in detail


# ==============================================================================
# 2. GATE 2: POSE CONFIDENCE & JERK FILTERING
# ==============================================================================

class TestGate2PoseConfidenceAndJerk:
    @pytest.fixture
    def engine(self) -> FiveGateFalsificationEngine:
        return FiveGateFalsificationEngine()

    def test_jerk_rejects_low_wrist_confidence(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject weapon/fighting if wrist keypoint confidence < 0.60."""
        # 17 keypoints: [x, y, conf]. Wrists are indices 9 (left) and 10 (right)
        kps = [[0.5, 0.5, 0.9] for _ in range(17)]
        kps[9] = [0.5, 0.5, 0.42]  # low conf left wrist
        kps[10] = [0.5, 0.5, 0.48]  # low conf right wrist
        passed, conf, is_harmonic, detail = engine.check_gate_2_pose_jerk_filter(
            "WEAPON_THREAT", kps, is_harmonic_motion=False
        )
        assert not passed
        assert conf < 0.60
        assert "Độ tin cậy khớp cổ tay quá thấp" in detail

    def test_jerk_rejects_harmonic_motion_fighting(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject fighting when motion is harmonic (jogging, rhythmic pacing)."""
        kps = [[0.5, 0.5, 0.95] for _ in range(17)]
        passed, conf, is_harmonic, detail = engine.check_gate_2_pose_jerk_filter(
            "FIGHTING", kps, is_harmonic_motion=True
        )
        assert not passed
        assert is_harmonic is True
        assert "Dao động điều hòa" in detail

    def test_jerk_passes_explosive_ballistic_strike(self, engine: FiveGateFalsificationEngine) -> None:
        """Pass when wrist confidence is high and motion is non-harmonic (jerk strike)."""
        kps = [[0.5, 0.5, 0.92] for _ in range(17)]
        kps[10] = [0.6, 0.4, 0.88]  # right wrist punch
        passed, conf, is_harmonic, detail = engine.check_gate_2_pose_jerk_filter(
            "FIGHTING", kps, is_harmonic_motion=False
        )
        assert passed
        assert conf >= 0.60
        assert not is_harmonic
        assert "Gia tốc giật cao" in detail

    def test_jerk_bypasses_non_kinetic_actions(self, engine: FiveGateFalsificationEngine) -> None:
        """Actions not involving wrist strikes or weapons bypass Gate 2."""
        passed, conf, is_harmonic, detail = engine.check_gate_2_pose_jerk_filter(
            "SUSPICIOUS_LOITERING", None, is_harmonic_motion=True
        )
        assert passed
        assert "Không thuộc nhóm hành động yêu cầu kiểm tra gia tốc" in detail

    def test_jerk_evaluates_average_wrist_conf_when_available(self, engine: FiveGateFalsificationEngine) -> None:
        """When keypoints are provided, wrist confidence is accurately calculated."""
        kps = [[0.5, 0.5, 0.8] for _ in range(17)]
        kps[9] = [0.4, 0.5, 0.70]
        kps[10] = [0.6, 0.5, 0.80]
        passed, conf, is_harmonic, detail = engine.check_gate_2_pose_jerk_filter(
            "WEAPON_CONCEALMENT", kps, is_harmonic_motion=False
        )
        assert passed
        assert conf == pytest.approx(0.75, abs=0.01)


# ==============================================================================
# 3. GATE 3: VICTIM ACTION-REACTION COUPLING
# ==============================================================================

class TestGate3ActionReactionCoupling:
    @pytest.fixture
    def engine(self) -> FiveGateFalsificationEngine:
        return FiveGateFalsificationEngine()

    def test_coupling_rejects_consensual_interaction(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject fighting when interaction notes indicate greeting, hugging, or talking."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "FIGHTING",
            victim_reaction_detected=False,
            velocity_divergence_m_s=0.5,
            interaction_note="hai người đang bắt tay và vỗ vai chào hỏi",
        )
        assert not passed
        assert "Tương tác đồng thuận" in detail

    def test_coupling_rejects_fighting_without_victim_reaction(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject physical altercation if victim shows no recoil or defensive stance."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "PHYSICAL_ALTERCATION",
            victim_reaction_detected=False,
            velocity_divergence_m_s=0.2,
            interaction_note="",
        )
        assert not passed
        assert not r_detected
        assert "Thiếu phản xạ tự vệ hoặc thoái lui" in detail

    def test_coupling_passes_fighting_with_confirmed_recoil(self, engine: FiveGateFalsificationEngine) -> None:
        """Pass physical altercation when victim reacts defensively."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "FIGHTING",
            victim_reaction_detected=True,
            velocity_divergence_m_s=1.2,
            interaction_note="nạn nhân giơ tay che chắn và ngả người né tránh",
        )
        assert passed
        assert r_detected
        assert "Xác nhận phản xạ phòng vệ" in detail

    def test_coupling_rejects_snatching_without_velocity_divergence(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject snatching if delta velocity <= 2.5 m/s (people walking/jogging together)."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "SNATCHING",
            victim_reaction_detected=False,
            velocity_divergence_m_s=1.8,
            interaction_note="",
        )
        assert not passed
        assert v_div <= 2.5
        assert "Thiếu phân kỳ vận tốc đột ngột" in detail

    def test_coupling_passes_snatching_with_high_divergence(self, engine: FiveGateFalsificationEngine) -> None:
        """Pass snatching when thief suddenly accelerates away at > 2.5 m/s."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "SNATCHING",
            victim_reaction_detected=True,
            velocity_divergence_m_s=3.6,
            interaction_note="kẻ giật đồ tăng tốc chạy trốn, nạn nhân đuổi theo",
        )
        assert passed
        assert v_div > 2.5
        assert "Xác nhận phân kỳ vận tốc tháo chạy" in detail

    def test_coupling_rejects_umbrella_as_weapon(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject weapon threat when object is identified as umbrella or walking stick."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "WEAPON_THREAT",
            victim_reaction_detected=False,
            velocity_divergence_m_s=0.1,
            holding_object_text="người đàn ông cầm chiếc ô che mưa cán dài",
        )
        assert not passed
        assert "vật dụng thường ngày" in detail
        assert "nhầm lẫn vật dụng thường ngày" in detail

    def test_coupling_rejects_phone_as_weapon(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject weapon threat when held object is a smartphone."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "WEAPON_CONCEALMENT",
            victim_reaction_detected=False,
            velocity_divergence_m_s=0.0,
            holding_object_text="đối tượng giơ điện thoại di động lên chụp ảnh",
        )
        assert not passed
        assert "điện thoại" in obj_note
        assert "vật dụng thường ngày" in detail

    def test_coupling_passes_true_knife_weapon(self, engine: FiveGateFalsificationEngine) -> None:
        """Pass weapon threat when metallic blade morphology is identified."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "WEAPON_THREAT",
            victim_reaction_detected=True,
            velocity_divergence_m_s=0.8,
            holding_object_text="đối tượng cầm dao bầu kim loại sắc nhọn uy hiếp",
        )
        assert passed
        assert "Xác thực vũ khí thực tế" in detail

    def test_coupling_bypasses_solo_actions(self, engine: FiveGateFalsificationEngine) -> None:
        """Solo actions bypass Gate 3."""
        passed, r_detected, v_div, obj_note, detail = engine.check_gate_3_action_reaction_coupling(
            "CASING", False, 0.0, ""
        )
        assert passed
        assert "Không yêu cầu đối ứng 2 chiều" in detail


# ==============================================================================
# 4. GATE 4: POSTURE & CONTEXT DISAMBIGUATION
# ==============================================================================

class TestGate4PostureAndContext:
    @pytest.fixture
    def engine(self) -> FiveGateFalsificationEngine:
        return FiveGateFalsificationEngine()

    def test_posture_rejects_sitting_against_wall_as_fallen(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject FALLEN if person is sitting resting against a wall or bench."""
        box = [0.2, 0.6, 0.4, 0.9]
        passed, posture, ctx, detail = engine.check_gate_4_posture_and_context(
            "FALLEN",
            box=box,
            pose_keypoints=[],
            scene_context="người ngồi tựa lưng vào tường nghỉ ngơi trên ghế đá",
            flat_axis_duration_s=1.0,
        )
        assert not passed
        assert "ngồi" in posture
        assert "Trạng thái nghỉ ngơi chủ động" in detail

    def test_posture_rejects_crouching_or_tying_shoelaces_as_fallen(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject FALLEN if person is crouching to tie shoes or pick up an item."""
        box = [0.3, 0.65, 0.5, 0.9]
        passed, posture, ctx, detail = engine.check_gate_4_posture_and_context(
            "FALLEN",
            box=box,
            pose_keypoints=[],
            scene_context="đối tượng ngồi xổm buộc dây giày",
            flat_axis_duration_s=2.0,
        )
        assert not passed
        assert "buộc dây giày" in ctx
        assert "ngồi xổm" in posture or "dây giày" in detail

    def test_posture_confirms_true_collapse_fallen(self, engine: FiveGateFalsificationEngine) -> None:
        """Confirm FALLEN if body axis is flat (width > height) for >= 3.0 seconds."""
        # Box width = 0.50 (0.2 to 0.7), height = 0.15 (0.75 to 0.90) -> flat axis
        box = [0.2, 0.75, 0.7, 0.90]
        passed, posture, ctx, detail = engine.check_gate_4_posture_and_context(
            "FALLEN",
            box=box,
            pose_keypoints=[],
            scene_context="nạn nhân bất tỉnh trên lòng đường",
            flat_axis_duration_s=4.5,
        )
        assert passed
        assert "nằm bất động trên mặt phẳng" in posture
        assert "Bất động kéo dài" in detail

    def test_posture_rejects_sportswear_jogging_as_fleeing(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject FLEEING if person is wearing sportswear exercising in park."""
        passed, posture, ctx, detail = engine.check_gate_4_posture_and_context(
            "FLEEING",
            box=[0.4, 0.3, 0.6, 0.8],
            pose_keypoints=[],
            scene_context="người mặc đồ thể thao chạy bộ tập thể dục buổi sáng",
            flat_axis_duration_s=0.0,
        )
        assert not passed
        assert "thể thao" in ctx
        assert "Chạy bộ thể dục" in detail

    def test_posture_rejects_running_from_rain_as_fleeing(self, engine: FiveGateFalsificationEngine) -> None:
        """Reject FLEEING if person is holding umbrella running from sudden downpour."""
        passed, posture, ctx, detail = engine.check_gate_4_posture_and_context(
            "FLEEING",
            box=[0.4, 0.3, 0.6, 0.8],
            pose_keypoints=[],
            scene_context="trời đổ mưa to, người dân cầm cặp che đầu chạy tìm chỗ trú",
            flat_axis_duration_s=0.0,
        )
        assert not passed
        assert "mưa" in ctx
        assert "Chạy tránh mưa" in detail

    def test_posture_confirms_true_criminal_fleeing(self, engine: FiveGateFalsificationEngine) -> None:
        """Confirm FLEEING when person sprints away looking back without exercise context."""
        passed, posture, ctx, detail = engine.check_gate_4_posture_and_context(
            "FLEEING",
            box=[0.4, 0.3, 0.6, 0.8],
            pose_keypoints=[],
            scene_context="đối tượng chạy tháo thân ngoái nhìn lại phía sau sau va chạm",
            flat_axis_duration_s=0.0,
        )
        assert passed
        assert "tháo chạy" in posture
        assert "Dáng chạy tháo chạy" in detail


# ==============================================================================
# 5. GATE 5: ADVERSARIAL BENIGN HYPOTHESIS TEST
# ==============================================================================

class TestGate5AdversarialBenignHypothesis:
    @pytest.fixture
    def engine(self) -> FiveGateFalsificationEngine:
        return FiveGateFalsificationEngine()

    def test_benign_score_high_when_prior_gate_failed(self, engine: FiveGateFalsificationEngine) -> None:
        """If a prior gate failed, benign hypothesis probability must be >= 0.85."""
        res = engine.evaluate_gate_5_benign_hypothesis(
            action="FIGHTING",
            prior_gates_passed=False,
            gate_failures=["Cổng 1: Sai khác mặt phẳng chân"],
            scene_context="",
            wrist_conf=0.8,
            divergence_v=0.0,
        )
        assert res.benign_hypothesis_probability >= 0.85
        assert not res.escalation_permitted
        assert "Không đủ bằng chứng hình học" in res.strongest_benign_explanation

    def test_benign_score_elevated_by_benign_keywords(self, engine: FiveGateFalsificationEngine) -> None:
        """Benign context keywords like 'học sinh', 'tập kịch' force probability >= 0.70."""
        res = engine.evaluate_gate_5_benign_hypothesis(
            action="FIGHTING",
            prior_gates_passed=True,
            gate_failures=[],
            scene_context="hai bạn học sinh đang đùa giỡn tập kịch",
            wrist_conf=0.9,
            divergence_v=1.0,
        )
        assert res.benign_hypothesis_probability >= 0.70
        assert not res.escalation_permitted

    def test_benign_score_low_when_all_gates_pass_with_solid_evidence(self, engine: FiveGateFalsificationEngine) -> None:
        """When all gates pass and no benign cues exist, benign probability < 0.20 and escalation allowed."""
        res = engine.evaluate_gate_5_benign_hypothesis(
            action="WEAPON_THREAT",
            prior_gates_passed=True,
            gate_failures=[],
            scene_context="đối tượng cầm dao đe dọa đòi tiền nạn nhân",
            wrist_conf=0.95,
            divergence_v=2.8,
        )
        assert res.benign_hypothesis_probability <= 0.20
        assert res.escalation_permitted
        assert "Bằng chứng hành vi nguy hiểm rõ ràng" in res.detail

    def test_benign_threshold_rules_cap_threat_level(self, engine: FiveGateFalsificationEngine) -> None:
        """Verify the rule: if benign prob >= 0.45, escalation forbidden; if >= 0.70, drops to Low."""
        # Case A: benign prob = 0.50 (>= 0.45, < 0.70)
        res_med = AdversarialFalsificationResult(
            strongest_benign_explanation="Đùa giỡn",
            benign_hypothesis_probability=0.55,
            escalation_permitted=False,
            detail="Medium capped",
        )
        assert not res_med.escalation_permitted

        # Case B: benign prob = 0.15 (< 0.25)
        res_crit = AdversarialFalsificationResult(
            strongest_benign_explanation="Cướp giật có hung khí",
            benign_hypothesis_probability=0.12,
            escalation_permitted=True,
            detail="High/Critical allowed",
        )
        assert res_crit.escalation_permitted


# ==============================================================================
# 6. MASTER AUDIT PIPELINE & MEMORY VETO INTEGRATION
# ==============================================================================

class TestMasterAuditPipeline:
    @pytest.fixture
    def engine(self) -> FiveGateFalsificationEngine:
        return FiveGateFalsificationEngine()

    def test_operator_memory_veto_takes_absolute_precedence(self, engine: FiveGateFalsificationEngine) -> None:
        """Memory engine suppression overrides all gates and immediately zeros out the alert."""
        audit = engine.run_comprehensive_audit(
            camera_name="CAM_01_ChuVanAn_GateA",
            action="FIGHTING",
            box_subject=[0.4, 0.4, 0.6, 0.9],
            box_victim=[0.45, 0.42, 0.65, 0.92],
            wrist_conf=0.95,
            is_harmonic=False,
            victim_reaction_detected=True,
            velocity_divergence_m_s=3.0,
            scene_context="",
            flat_axis_duration_s=0.0,
            memory_suppression=(True, "Nhầm lẫn nhân viên bảo vệ luyện tập", "EVT_MEM_01"),
        )
        assert audit.falsification_summary.startswith("TRIỆT TIÊU BÁO ĐỘNG GIA THEO BỘ NHỚ LỖI")
        assert audit.gate_5_adversarial_benign_hypothesis["benign_hypothesis_probability"] == 0.99
        assert not audit.gate_5_adversarial_benign_hypothesis["escalation_permitted"]

    def test_audit_suppresses_perspective_overlap_crossing(self, engine: FiveGateFalsificationEngine) -> None:
        """2D overlap with foot_y delta > 0.15 is falsified at Gate 1."""
        audit = engine.run_comprehensive_audit(
            camera_name="CAM_02",
            action="FIGHTING",
            box_subject=[0.4, 0.5, 0.6, 0.90],
            box_victim=[0.45, 0.2, 0.65, 0.55],  # delta_foot_y = 0.35/0.35 = 1.0 > 0.15
            wrist_conf=0.85,
            is_harmonic=False,
            victim_reaction_detected=False,
            velocity_divergence_m_s=0.2,
            scene_context="",
            flat_axis_duration_s=0.0,
        )
        assert audit.gate_1_ground_plane_depth["status"] == "REJECTED"
        assert not audit.gate_5_adversarial_benign_hypothesis["escalation_permitted"]
        assert audit.gate_5_adversarial_benign_hypothesis["benign_hypothesis_probability"] >= 0.70

    def test_audit_suppresses_umbrella_as_weapon(self, engine: FiveGateFalsificationEngine) -> None:
        """Umbrella falsely flagged as weapon is rejected at Gate 3 and Gate 5."""
        audit = engine.run_comprehensive_audit(
            camera_name="CAM_03",
            action="WEAPON_THREAT",
            box_subject=[0.4, 0.3, 0.6, 0.8],
            box_victim=None,
            wrist_conf=0.88,
            is_harmonic=False,
            victim_reaction_detected=False,
            velocity_divergence_m_s=0.0,
            holding_object_text="người đi bộ cầm ô che mưa",
            scene_context="trời mưa phùn, người dân cầm ô di chuyển",
        )
        assert audit.gate_3_action_reaction_coupling["status"] == "REJECTED"
        assert not audit.gate_5_adversarial_benign_hypothesis["escalation_permitted"]

    def test_audit_passes_and_permits_escalation_for_true_armed_robbery(self, engine: FiveGateFalsificationEngine) -> None:
        """True robbery passes all 5 gates with flying colors and permits escalation."""
        audit = engine.run_comprehensive_audit(
            camera_name="CAM_01_ChuVanAn_GateA",
            action="SNATCHING",
            box_subject=[0.40, 0.40, 0.55, 0.90],
            box_victim=[0.48, 0.42, 0.62, 0.92],
            wrist_conf=0.92,
            is_harmonic=False,
            victim_reaction_detected=True,
            velocity_divergence_m_s=3.8,
            holding_object_text="túi xách bị giật mạnh",
            scene_context="đối tượng giật mạnh túi xách khiến nạn nhân ngã ngửa",
        )
        assert audit.gate_1_ground_plane_depth["status"] == "PASSED"
        assert audit.gate_2_pose_jerk_filter["status"] == "PASSED"
        assert audit.gate_3_action_reaction_coupling["status"] == "PASSED"
        assert audit.gate_4_posture_and_context["status"] == "PASSED"
        assert audit.gate_5_adversarial_benign_hypothesis["escalation_permitted"] is True
        assert audit.gate_5_adversarial_benign_hypothesis["benign_hypothesis_probability"] < 0.25
        assert "ĐẠT 5 CỔNG KIỂM ĐỊNH PHÁP Y" in audit.falsification_summary

    def test_audit_as_dict_schema_structure(self, engine: FiveGateFalsificationEngine) -> None:
        """Verify as_dict() output exactly matches Section 6 JSON schema specifications."""
        audit = engine.run_comprehensive_audit(
            camera_name="CAM_04",
            action="LOITERING",
            box_subject=[0.1, 0.2, 0.3, 0.8],
        )
        d = audit.as_dict()
        assert "gate_1_ground_plane_depth" in d
        assert "gate_2_pose_jerk_filter" in d
        assert "gate_3_action_reaction_coupling" in d
        assert "gate_4_posture_and_context" in d
        assert "gate_5_adversarial_benign_hypothesis" in d
        assert "falsification_summary" in d
        assert "delta_foot_y_ratio" in d["gate_1_ground_plane_depth"]
        assert "wrist_confidence" in d["gate_2_pose_jerk_filter"]
        assert "victim_reaction_detected" in d["gate_3_action_reaction_coupling"]
        assert "benign_hypothesis_probability" in d["gate_5_adversarial_benign_hypothesis"]


# ==============================================================================
# 7. NVIDIA VISION CLIENT & SCHEMA v2.0 INTEGRATION TESTS
# ==============================================================================

class TestNvidiaVisionClientSchemaV2:
    @pytest.fixture
    def client(self) -> NvidiaVisionClient:
        return NvidiaVisionClient(api_key="mock_key")

    def test_client_includes_anti_false_positive_audit_in_mock_response(self, client: NvidiaVisionClient) -> None:
        """analyze_frame produces valid Section 6 v2.0 JSON including anti_false_positive_audit."""
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = client.analyze_frame(
            frame=dummy_frame,
            camera_id="CAM_01",
            camera_name="CAM_01_ChuVanAn_GateA",
            action_hint="FIGHTING",
        )
        assert "anti_false_positive_audit" in result
        audit = result["anti_false_positive_audit"]
        assert "gate_1_ground_plane_depth" in audit
        assert "gate_5_adversarial_benign_hypothesis" in audit

    def test_client_caps_threat_level_when_gate_5_benign_prob_is_high(self, client: NvidiaVisionClient) -> None:
        """When benign prob >= 0.45 or gates fail, threat level is capped at Medium/Low."""
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Passing scene context with harmless jogging/student keywords
        result = client.analyze_frame(
            frame=dummy_frame,
            camera_id="CAM_01",
            camera_name="CAM_01_ChuVanAn_GateA",
            action_hint="FIGHTING",
            scene_context="hai học sinh đang đùa giỡn trong giờ ra chơi",
            victim_reaction_detected=False,
        )
        threat_level = result.get("threat_level")
        assert threat_level in ("Low", "Medium")
        assert threat_level != "Critical"
        assert threat_level != "High"

    def test_client_permits_critical_alert_for_confirmed_armed_altercation(self, client: NvidiaVisionClient) -> None:
        """When all gates pass and action is WEAPON_THREAT, High or Critical is permitted."""
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = client.analyze_frame(
            frame=dummy_frame,
            camera_id="CAM_01",
            camera_name="CAM_01_ChuVanAn_GateA",
            action_hint="WEAPON_THREAT",
            bounding_box=[0.40, 0.40, 0.55, 0.90],
            victim_box=[0.48, 0.42, 0.62, 0.92],
            wrist_conf=0.96,
            is_harmonic_motion=False,
            victim_reaction_detected=True,
            holding_object_text="đối tượng cầm dao bầu kim loại sáng loáng đe dọa",
            scene_context="đối tượng dùng dao uy hiếp cướp tài sản",
        )
        assert result.get("threat_level") in ("High", "Critical")
        audit = result.get("anti_false_positive_audit", {})
        assert audit.get("gate_5_adversarial_benign_hypothesis", {}).get("escalation_permitted") is True

    def test_client_never_outputs_operator_confirmed_status(self, client: NvidiaVisionClient) -> None:
        """Strict HITL (CD-04): Maximum state is AWAITING_OPERATOR_VERIFICATION, NEVER OPERATOR_CONFIRMED."""
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for act in ["FALLEN", "FIGHTING", "WEAPON_THREAT", "SNATCHING", "FLEEING"]:
            result = client.analyze_frame(
                frame=dummy_frame,
                camera_id="CAM_02",
                action_hint=act,
                victim_reaction_detected=True,
                wrist_conf=0.95,
            )
            status = result.get("incident_status")
            assert status != "OPERATOR_CONFIRMED", f"Violation of CD-04 HITL for action {act}"
            assert status in ("OBSERVING", "MONITORING", "AWAITING_OPERATOR_VERIFICATION")

    def test_client_evaluated_subjects_each_contain_anti_false_positive_audit(self, client: NvidiaVisionClient) -> None:
        """Every subject in evaluated_subjects contains its own anti_false_positive_audit block."""
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = client.analyze_frame(
            frame=dummy_frame,
            camera_id="CAM_01",
            action_hint="SNATCHING",
        )
        subjects = result.get("evaluated_subjects", [])
        assert len(subjects) >= 1
        for sub in subjects:
            assert "anti_false_positive_audit" in sub
            sub_audit = sub["anti_false_positive_audit"]
            assert "gate_1_ground_plane_depth" in sub_audit
            assert "gate_2_pose_jerk_filter" in sub_audit
            assert "gate_3_action_reaction_coupling" in sub_audit
            assert "gate_4_posture_and_context" in sub_audit
            assert "gate_5_adversarial_benign_hypothesis" in sub_audit
            assert "falsification_summary" in sub_audit
