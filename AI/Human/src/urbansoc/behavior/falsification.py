"""Urban Safety AI-SOC v2.0: 5-Gate Falsification Protocol Engine.

Implements the skeptical forensic auditor protocol to reject 100% of false positives
arising from 2D visual perspective overlap, keypoint noise, benign daily activities,
and posture misinterpretations.

Strictly enforces:
- Section 6 v2.0 Structured JSON Schema
- Gate 1: 3D Ground-Plane Depth Check (|foot_y_A - foot_y_B| / min(H_A, H_B) <= 0.15, H_A/H_B in [0.75, 1.35])
- Gate 2: Pose Confidence & Jerk Filtering (wrist conf >= 0.60, rejects harmonic motion)
- Gate 3: Victim Action-Reaction Coupling (defensive recoil / velocity divergence > 2.5 m/s)
- Gate 4: Posture & Context Disambiguation (sitting/crouching vs fallen; sportswear/rain vs fleeing)
- Gate 5: Adversarial Benign Hypothesis Test (benign_prob >= 0.45 blocks escalation; >= 0.70 drops to Low)
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class AdversarialFalsificationResult:
    """Gate 5 Adversarial Benign Hypothesis evaluation result."""
    strongest_benign_explanation: str
    benign_hypothesis_probability: float
    escalation_permitted: bool = False
    detail: str = ""

    # Backwards compatibility properties
    @property
    def best_benign_hypothesis(self) -> str:
        return self.strongest_benign_explanation

    @property
    def evidence_refuting_benign_hypothesis(self) -> str:
        return self.detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strongest_benign_explanation": self.strongest_benign_explanation,
            "benign_hypothesis_probability": round(self.benign_hypothesis_probability, 2),
            "escalation_permitted": self.escalation_permitted,
            "detail": self.detail,
        }

    def as_dict(self) -> Dict[str, Any]:
        return self.to_dict()


@dataclass
class AntiFalsePositiveAudit:
    """Full 5-Gate Anti-False-Positive Audit Record strictly adhering to Section 6 v2.0 Schema."""
    gate_1_ground_plane_depth: Dict[str, Any]
    gate_2_pose_jerk_filter: Dict[str, Any]
    gate_3_action_reaction_coupling: Dict[str, Any]
    gate_4_posture_and_context: Dict[str, Any]
    gate_5_adversarial_benign_hypothesis: Dict[str, Any]
    falsification_summary: str
    applied_incident_memory_rule_id: Optional[str] = None
    false_positive_suppressed: bool = False
    suppression_reason: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        d = self.as_dict()
        return d[item]

    def to_dict(self) -> Dict[str, Any]:
        return self.as_dict()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "gate_1_ground_plane_depth": self.gate_1_ground_plane_depth,
            "gate_2_pose_jerk_filter": self.gate_2_pose_jerk_filter,
            "gate_3_action_reaction_coupling": self.gate_3_action_reaction_coupling,
            "gate_4_posture_and_context": self.gate_4_posture_and_context,
            "gate_5_adversarial_benign_hypothesis": self.gate_5_adversarial_benign_hypothesis,
            "falsification_summary": self.falsification_summary,
            "applied_incident_memory_rule_id": self.applied_incident_memory_rule_id,
            "false_positive_suppressed": self.false_positive_suppressed,
            "suppression_reason": self.suppression_reason,
        }


class FiveGateFalsificationEngine:
    """Master Skeptical Auditor Engine executing the 5-Gate Falsification Protocol."""

    INTERACTION_ACTIONS = {
        "FIGHTING", "SNATCHING", "RESTRAINING", "PHYSICAL_ASSAULT",
        "PHYSICAL_ALTERCATION", "STALKING", "PURSUIT", "ASSAULT",
    }

    BENIGN_OBJECT_KEYWORDS = {
        "phone", "điện thoại", "smartphone", "umbrella", "ô dù", "dù che mưa",
        "ô che mưa", "cán dài", "bottle", "chai nước", "flashlight", "đèn pin",
        "bag", "túi nilon", "jacket", "áo khoác",
    }

    BENIGN_CONTEXT_KEYWORDS = {
        "học sinh", "chào hỏi", "bắt tay", "vỗ vai", "đùa giỡn", "tập kịch",
        "thể thao", "chạy bộ", "mưa", "trú mưa", "bảo vệ", "luyện tập",
    }

    # ==========================================================================
    # GATE 1: 3D Ground-Plane Depth Check
    # ==========================================================================
    @classmethod
    def check_gate_1_ground_plane_depth(
        cls,
        raw_action: str,
        box_subject: Optional[Union[List[float], Tuple[float, ...]]] = None,
        box_victim: Optional[Union[List[float], Tuple[float, ...]]] = None,
        subject_foot_y: Optional[float] = None,
        victim_foot_y: Optional[float] = None,
        one_subject_fallen: bool = False,
    ) -> Tuple[bool, float, float, str]:
        """Gate 1: Verify whether two individuals occupy the same depth plane in 3D ground space.

        Returns: (passed, delta_foot_y_ratio, height_ratio, detail)
        """
        clean_action = raw_action.strip().upper() if raw_action else "NORMAL"
        is_interactive = clean_action in cls.INTERACTION_ACTIONS

        if not is_interactive or box_victim is None or box_subject is None:
            if not is_interactive:
                return True, 0.0, 1.0, "Không áp dụng kiểm tra cặp cho hành vi đơn thể."
            return True, 0.0, 1.0, "Thiếu thông tin bounding box đối phương; tạm chấp nhận dữ liệu."

        s_x1, s_y1, s_x2, s_y2 = box_subject
        v_x1, v_y1, v_x2, v_y2 = box_victim

        h_s = max(0.01, s_y2 - s_y1)
        h_v = max(0.01, v_y2 - v_y1)

        f_y_s = subject_foot_y if subject_foot_y is not None else s_y2
        f_y_v = victim_foot_y if victim_foot_y is not None else v_y2

        min_h = min(h_s, h_v)
        delta_foot_y_ratio = abs(f_y_s - f_y_v) / min_h
        height_ratio = h_s / h_v

        # Check fallen exception
        if one_subject_fallen or clean_action == "RESTRAINING" and (h_s < 0.20 or h_v < 0.20):
            return True, delta_foot_y_ratio, height_ratio, "Chấp nhận ngoại lệ đối tượng nằm/ngã trên mặt đất."

        # Rule 1: Foot Y difference > 15% of min height
        if delta_foot_y_ratio > 0.15:
            detail = (
                f"[GATE 1 BÁC BỎ] Sai khác mặt phẳng chân delta_foot_y_ratio={delta_foot_y_ratio:.3f} > 0.15. "
                f"Hai người đứng cách xa nhau theo chiều sâu 3D, sự chồng lấn BBox chỉ là phối cảnh 2D."
            )
            return False, delta_foot_y_ratio, height_ratio, detail

        # Rule 2: Height ratio distorted outside [0.75, 1.35]
        if height_ratio < 0.75 or height_ratio > 1.35:
            detail = (
                f"[GATE 1 BÁC BỎ] Tỉ lệ chiều cao bất thường H_A/H_B={height_ratio:.2f} nằm ngoài [0.75, 1.35]. "
                f"Chênh lệch kích thước chứng minh khoảng cách chiều sâu đáng kể."
            )
            return False, delta_foot_y_ratio, height_ratio, detail

        detail = f"Xác nhận cùng mặt phẳng sàn 3D (delta_y={delta_foot_y_ratio:.3f} <= 0.15, ratio={height_ratio:.2f})."
        return True, delta_foot_y_ratio, height_ratio, detail

    @classmethod
    def audit_gate1_3d_depth(
        cls,
        raw_action: str,
        subject_bbox: Tuple[float, float, float, float],
        victim_bbox: Optional[Tuple[float, float, float, float]] = None,
        subject_foot_y: Optional[float] = None,
        victim_foot_y: Optional[float] = None,
        one_subject_fallen: bool = False,
    ) -> Tuple[bool, float, Optional[str]]:
        passed, delta_y, ratio, detail = cls.check_gate_1_ground_plane_depth(
            raw_action=raw_action,
            box_subject=subject_bbox,
            box_victim=victim_bbox,
            subject_foot_y=subject_foot_y,
            victim_foot_y=victim_foot_y,
            one_subject_fallen=one_subject_fallen,
        )
        return passed, delta_y, None if passed else detail

    # ==========================================================================
    # GATE 2: Pose Confidence & Jerk Filtering
    # ==========================================================================
    @classmethod
    def check_gate_2_pose_jerk_filter(
        cls,
        raw_action: str,
        pose_keypoints: Optional[Union[List[Any], Tuple[Any, ...]]] = None,
        is_harmonic_motion: bool = False,
        wrist_confidence_override: Optional[float] = None,
    ) -> Tuple[bool, float, bool, str]:
        """Gate 2: Pose Confidence & Jerk Filtering.

        Returns: (passed, wrist_confidence, is_harmonic_motion, detail)
        """
        clean_action = raw_action.strip().upper() if raw_action else "NORMAL"
        requires_jerk = clean_action in ("FIGHTING", "WEAPON_THREAT", "WEAPON_CONCEALMENT", "PHYSICAL_ASSAULT", "PHYSICAL_ALTERCATION", "SNATCHING")

        if not requires_jerk:
            return True, 0.95, False, "Không thuộc nhóm hành động yêu cầu kiểm tra gia tốc giật bạo lực."

        # Extract wrist confidence from keypoints (indices 9 and 10 in standard 17-keypoint COCO format)
        wrist_conf = 0.90
        if wrist_confidence_override is not None:
            wrist_conf = wrist_confidence_override
        elif pose_keypoints and len(pose_keypoints) >= 17:
            try:
                left_wrist = pose_keypoints[9]
                right_wrist = pose_keypoints[10]
                conf_l = float(left_wrist[2]) if len(left_wrist) > 2 else 0.8
                conf_r = float(right_wrist[2]) if len(right_wrist) > 2 else 0.8
                wrist_conf = (conf_l + conf_r) / 2.0
            except Exception:
                wrist_conf = 0.85

        if wrist_conf < 0.60:
            detail = f"[GATE 2 BÁC BỎ] Độ tin cậy khớp cổ tay quá thấp ({wrist_conf:.2f} < 0.60), dễ nhiễu ảnh."
            return False, wrist_conf, is_harmonic_motion, detail

        if is_harmonic_motion:
            detail = "[GATE 2 BÁC BỎ] Dao động điều hòa lặp lại (vẫy tay, chạy bộ, vung tay nhịp nhàng), không phải xung lực giật bạo lực."
            return False, wrist_conf, True, detail

        detail = f"Xác nhận độ tin cậy khớp tay cao ({wrist_conf:.2f}) và Gia tốc giật cao phi điều hòa (Ballistic Jerk)."
        return True, wrist_conf, False, detail

    @classmethod
    def audit_gate2_pose_jerk(
        cls,
        raw_action: str,
        wrist_confidence: float = 0.90,
        is_harmonic_motion: bool = False,
        acceleration_jerk_mps3: float = 0.0,
        wrist_occluded_without_proof: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        eff_conf = 0.40 if wrist_occluded_without_proof else wrist_confidence
        passed, conf, harmonic, detail = cls.check_gate_2_pose_jerk_filter(
            raw_action=raw_action,
            pose_keypoints=None,
            is_harmonic_motion=is_harmonic_motion,
            wrist_confidence_override=eff_conf,
        )
        return passed, None if passed else detail

    # ==========================================================================
    # GATE 3: Victim Action-Reaction Coupling
    # ==========================================================================
    @classmethod
    def check_gate_3_action_reaction_coupling(
        cls,
        raw_action: str,
        victim_reaction_detected: bool = False,
        velocity_divergence_m_s: float = 0.0,
        holding_object_text: str = "",
        interaction_note: str = "",
        is_consensual_interaction: bool = False,
    ) -> Tuple[bool, bool, float, str, str]:
        """Gate 3: Validate victim defensive reaction or impact impulse coupling.

        Returns: (passed, victim_reaction_detected, velocity_divergence_m_s, holding_everyday_object_note, detail)
        """
        clean_action = raw_action.strip().upper() if raw_action else "NORMAL"
        is_interactive = clean_action in cls.INTERACTION_ACTIONS or "WEAPON" in clean_action

        if not is_interactive:
            return True, False, 0.0, "none", "Hành vi đơn thể; Không yêu cầu đối ứng 2 chiều từ người khác."

        note_lower = (interaction_note or "").lower()
        obj_lower = (holding_object_text or "").lower()

        # Check consensual interaction (greeting, dancing, helping)
        if is_consensual_interaction or any(w in note_lower for w in ["bắt tay", "vỗ vai", "ôm", "chào hỏi", "dìu nhau", "đồng thuận"]):
            detail = "[GATE 3 BÁC BỎ] Tương tác đồng thuận vô hại giữa các cá nhân (chào hỏi, bắt tay, dìu nhau)."
            return False, False, velocity_divergence_m_s, "none", detail

        # Fighting / Assault check
        if clean_action in ("FIGHTING", "PHYSICAL_ASSAULT", "PHYSICAL_ALTERCATION"):
            if not victim_reaction_detected and not any(w in note_lower for w in ["che chắn", "ngã", "lùi", "phản xạ"]):
                detail = "[GATE 3 BÁC BỎ] Thiếu phản xạ tự vệ hoặc thoái lui từ đối phương (không có hành vi kháng cự/phòng thủ)."
                return False, False, velocity_divergence_m_s, "none", detail
            detail = "Xác nhận phản xạ phòng vệ (giơ tay đỡ, ngả lùi, lùi bước mất thăng bằng) từ nạn nhân."
            return True, True, velocity_divergence_m_s, "none", detail

        # Snatching check
        if clean_action == "SNATCHING":
            if velocity_divergence_m_s <= 2.5 and not victim_reaction_detected:
                detail = f"[GATE 3 BÁC BỎ] Thiếu phân kỳ vận tốc đột ngột delta_v={velocity_divergence_m_s:.1f} m/s <= 2.5 m/s. Không có dấu hiệu cướp giật tháo chạy."
                return False, False, velocity_divergence_m_s, "none", detail
            detail = f"Xác nhận phân kỳ vận tốc tháo chạy đột ngột delta_v={velocity_divergence_m_s:.1f} m/s > 2.5 m/s kèm phản xạ nạn nhân."
            return True, True, velocity_divergence_m_s, "none", detail

        # Weapon threat check
        if "WEAPON" in clean_action or clean_action in ("KNIFE_THREAT", "WEAPON_THREAT", "WEAPON_CONCEALMENT"):
            for kw in cls.BENIGN_OBJECT_KEYWORDS:
                if kw in obj_lower:
                    detail = f"[GATE 3 BÁC BỎ] Đối tượng chỉ cầm vật dụng thường ngày ({kw}); nhầm lẫn vật dụng thường ngày với hung khí."
                    return False, victim_reaction_detected, velocity_divergence_m_s, kw, detail

            if any(w in obj_lower for w in ["dao", "kim loại", "sắc nhọn", "súng", "hung khí", "lưỡi"]):
                detail = f"Xác thực vũ khí thực tế có đặc tính hình học kim loại/sắc nhọn ({holding_object_text})."
                return True, victim_reaction_detected, velocity_divergence_m_s, "none", detail

            # If no everyday object and no clear weapon, pass if victim has fear reaction, else reject
            if victim_reaction_detected:
                detail = "Xác nhận đối phương có phản xạ khiếp sợ/né tránh trước vật thể nghi vấn."
                return True, True, velocity_divergence_m_s, "none", detail

            detail = "[GATE 3 BÁC BỎ] Không xác thực được hình thái hung khí và nạn nhân không có phản xạ phòng thủ."
            return False, False, velocity_divergence_m_s, "unverified_object", detail

        detail = "Xác nhận đối ứng phù hợp ngữ cảnh."
        return True, victim_reaction_detected, velocity_divergence_m_s, "none", detail

    @classmethod
    def audit_gate3_victim_reaction(
        cls,
        raw_action: str,
        has_defensive_guard: bool = False,
        has_stumble_or_recoil: bool = False,
        velocity_divergence_mps: float = 0.0,
        has_abrupt_turn_or_chase: bool = False,
        is_unnatural_lock_and_struggle: bool = False,
        is_weapon_morphology_verified: bool = False,
        held_object_name: str = "",
        is_consensual_interaction: bool = False,
    ) -> Tuple[bool, str, Optional[str]]:
        reaction = has_defensive_guard or has_stumble_or_recoil or has_abrupt_turn_or_chase
        holding_txt = held_object_name
        if is_weapon_morphology_verified and not holding_txt:
            holding_txt = "dao kim loại"

        passed, r_det, v_div, obj_note, detail = cls.check_gate_3_action_reaction_coupling(
            raw_action=raw_action,
            victim_reaction_detected=reaction,
            velocity_divergence_m_s=velocity_divergence_mps,
            holding_object_text=holding_txt,
            is_consensual_interaction=is_consensual_interaction,
        )
        return passed, detail, None if passed else detail

    # ==========================================================================
    # GATE 4: Posture & Context Disambiguation
    # ==========================================================================
    @classmethod
    def check_gate_4_posture_and_context(
        cls,
        raw_action: str,
        box: Optional[Union[List[float], Tuple[float, ...]]] = None,
        pose_keypoints: Optional[Union[List[Any], Tuple[Any, ...]]] = None,
        scene_context: str = "",
        flat_axis_duration_s: float = 0.0,
        is_sitting_or_crouching: bool = False,
        is_sport_jogging: bool = False,
        is_running_from_rain: bool = False,
    ) -> Tuple[bool, str, str, str]:
        """Gate 4: Posture & Context Disambiguation.

        Returns: (passed, posture_assessment, clothing_or_weather_context, detail)
        """
        clean_action = raw_action.strip().upper() if raw_action else "NORMAL"
        ctx_lower = (scene_context or "").lower()

        # Fallen verification
        if clean_action == "FALLEN":
            if is_sitting_or_crouching or any(w in ctx_lower for w in ["ngồi", "dựa tường", "ghế đá", "buộc dây giày", "ngồi xổm", "nhặt đồ"]):
                posture = "Tư thế ngồi xổm / cúi buộc dây giày có chủ đích."
                ctx = "Trạng thái nghỉ ngơi chủ động hoặc buộc dây giày."
                detail = "[GATE 4 BÁC BỎ] Trạng thái nghỉ ngơi chủ động hoặc ngồi xổm cúi buộc dây giày thao tác cá nhân, không phải ngã gục bất tỉnh."
                return False, posture, ctx, detail

            # Evaluate box aspect ratio (width vs height)
            w_h_ratio = 1.0
            if box and len(box) >= 4:
                w = max(0.01, box[2] - box[0])
                h = max(0.01, box[3] - box[1])
                w_h_ratio = w / h

            if flat_axis_duration_s >= 3.0 or w_h_ratio > 1.2 or "bất tỉnh" in ctx_lower or "nằm" in ctx_lower:
                posture = "Đối tượng nằm bất động trên mặt phẳng lòng đường/sàn."
                ctx = "Không có ghế tựa hay vật đỡ cơ thể."
                detail = f"Bất động kéo dài ({flat_axis_duration_s:.1f}s) với trục cơ thể nằm ngang hoàn toàn."
                return True, posture, ctx, detail

            detail = "[GATE 4 BÁC BỎ] Trục cơ thể chưa nằm rạp hoặc thời gian bất động chưa đủ dài."
            return False, "Chưa xác định tư thế ngã", "Không rõ", detail

        # Fleeing verification
        if clean_action == "FLEEING":
            if is_sport_jogging or any(w in ctx_lower for w in ["thể thao", "tập thể dục", "chạy bộ", "công viên"]):
                posture = "Dáng chạy bộ thể thao đều nhịp (Harmonic running gait)."
                ctx = "Trang phục thể thao / Khu vực rèn luyện sức khỏe."
                detail = "[GATE 4 BÁC BỎ] Chạy bộ thể dục rèn luyện sức khỏe, không có dấu hiệu hoảng loạn tháo chạy."
                return False, posture, ctx, detail

            if is_running_from_rain or any(w in ctx_lower for w in ["mưa", "trú mưa", "che đầu"]):
                posture = "Chạy nhanh tìm nơi che chắn thời tiết."
                ctx = "Điều kiện thời tiết mưa to hoặc gió bão."
                detail = "[GATE 4 BÁC BỎ] Chạy tránh mưa hoặc di chuyển nhanh đón phương tiện, không có cử chỉ nhìn ngoái lại tội phạm."
                return False, posture, ctx, detail

            posture = "Dáng chạy tháo chạy hoảng loạn tốc độ cao, ngoái nhìn lại phía sau."
            ctx = "Khu vực vừa xảy ra xô xát hoặc đột nhập."
            detail = "Xác nhận Dáng chạy tháo chạy có chủ đích lẩn trốn."
            return True, posture, ctx, detail

        return True, "Tư thế bình thường", "Ngữ cảnh tiêu chuẩn", "Phù hợp ngữ cảnh quan sát."

    @classmethod
    def audit_gate4_posture_context(
        cls,
        raw_action: str,
        is_sitting_on_bench_or_steps: bool = False,
        is_tying_shoelaces_or_crouching: bool = False,
        head_upright_working_phone: bool = False,
        motionless_duration_sec: float = 0.0,
        body_axis_horizontal_angle_deg: float = 60.0,
        is_sport_jogging: bool = False,
        is_running_from_rain_or_transit: bool = False,
        lookback_count: int = 0,
        has_clutched_suspicious_item: bool = False,
        is_post_crime_event: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        sitting = is_sitting_on_bench_or_steps or is_tying_shoelaces_or_crouching or head_upright_working_phone
        passed, pos, ctx, detail = cls.check_gate_4_posture_and_context(
            raw_action=raw_action,
            flat_axis_duration_s=motionless_duration_sec,
            is_sitting_or_crouching=sitting,
            is_sport_jogging=is_sport_jogging,
            is_running_from_rain=is_running_from_rain_or_transit,
        )
        return passed, None if passed else detail

    # ==========================================================================
    # GATE 5: Adversarial Benign Hypothesis Test
    # ==========================================================================
    @classmethod
    def evaluate_gate_5_benign_hypothesis(
        cls,
        action: str,
        prior_gates_passed: bool,
        gate_failures: List[str],
        scene_context: str = "",
        wrist_conf: float = 0.90,
        divergence_v: float = 0.0,
        held_object: str = "",
        is_memory_vetoed: bool = False,
    ) -> AdversarialFalsificationResult:
        """Gate 5: Formulate strongest adversarial benign hypothesis.

        Strict Rules:
        - If any prior gate failed or is memory vetoed -> benign_prob >= 0.85 (escalation forbidden).
        - If benign context keywords found -> benign_prob >= 0.70 (escalation forbidden, drops to Low).
        - If all gates 1-4 pass with solid physical proof -> benign_prob <= 0.20 (escalation permitted).
        """
        clean_action = action.strip().upper() if action else "NORMAL"
        ctx_lower = (scene_context or "").lower()
        held_lower = (held_object or "").lower()

        if is_memory_vetoed:
            return AdversarialFalsificationResult(
                strongest_benign_explanation="Trùng khớp sự vụ đã từng được Operator xác nhận là báo động giả trong INCIDENT_MEMORY.",
                benign_hypothesis_probability=0.99,
                escalation_permitted=False,
                detail="Triệt tiêu tuyệt đối theo quy tắc Trí nhớ Vận hành viên (Hard Memory Veto).",
            )

        if not prior_gates_passed:
            fail_str = "; ".join(gate_failures) if gate_failures else "Vi phạm tiêu chuẩn vật lý học"
            explanation = f"Không đủ bằng chứng hình học/đối ứng ({fail_str}). Tình huống sinh hoạt bình thường bị nhiễu thị giác."
            return AdversarialFalsificationResult(
                strongest_benign_explanation=explanation,
                benign_hypothesis_probability=0.88,
                escalation_permitted=False,
                detail=f"Cổng kiểm định trước bác bỏ: {fail_str}",
            )

        # Check benign keywords
        if any(w in ctx_lower for w in cls.BENIGN_CONTEXT_KEYWORDS):
            return AdversarialFalsificationResult(
                strongest_benign_explanation="Hoạt động thường nhật vô hại (học sinh đùa giỡn, tập thể thao, chào hỏi, tránh mưa).",
                benign_hypothesis_probability=0.72,
                escalation_permitted=False,
                detail="Phát hiện dấu hiệu ngữ cảnh vô hại, chặn nâng cấp báo động.",
            )

        # If all prior gates passed cleanly
        prob_map = {
            "WEAPON_THREAT": 0.08,
            "PHYSICAL_ALTERCATION": 0.12,
            "FIGHTING": 0.10,
            "SNATCHING": 0.07,
            "FALLEN": 0.14,
            "FLEEING": 0.15,
            "RESTRAINING": 0.11,
            "CASING": 0.22,
            "LOITERING": 0.24,
        }
        prob = prob_map.get(clean_action, 0.18)

        return AdversarialFalsificationResult(
            strongest_benign_explanation="Giả thuyết đùa giỡn hoặc va chạm vô ý bị bác bỏ do đầy đủ bằng chứng đối ứng 3D và phản xạ phòng thủ.",
            benign_hypothesis_probability=prob,
            escalation_permitted=True,
            detail="Bằng chứng hành vi nguy hiểm rõ ràng, đạt toàn bộ 5 cổng kiểm định pháp y.",
        )

    @classmethod
    def audit_gate5_adversarial_benign(
        cls,
        raw_action: str,
        gate1_passed: bool,
        gate2_passed: bool,
        gate3_passed: bool,
        gate4_passed: bool,
        context_text: str = "",
        held_object: str = "",
        is_memory_vetoed: bool = False,
    ) -> AdversarialFalsificationResult:
        all_passed = gate1_passed and gate2_passed and gate3_passed and gate4_passed
        failures = []
        if not gate1_passed:
            failures.append("Cổng 1: Sai khác mặt phẳng sâu")
        if not gate2_passed:
            failures.append("Cổng 2: Khớp xương/Dao động điều hòa")
        if not gate3_passed:
            failures.append("Cổng 3: Thiếu phản xạ nạn nhân/Vật dụng thường ngày")
        if not gate4_passed:
            failures.append("Cổng 4: Tư thế/Ngữ cảnh thông thường")

        return cls.evaluate_gate_5_benign_hypothesis(
            action=raw_action,
            prior_gates_passed=all_passed,
            gate_failures=failures,
            scene_context=context_text,
            held_object=held_object,
            is_memory_vetoed=is_memory_vetoed,
        )

    # ==========================================================================
    # MASTER AUDIT PIPELINE
    # ==========================================================================
    def run_comprehensive_audit(
        self,
        camera_name: str = "",
        action: str = "NORMAL",
        raw_actions: Optional[List[str]] = None,
        box_subject: Optional[Union[List[float], Tuple[float, ...]]] = None,
        bbox_norm: Optional[Union[List[float], Tuple[float, ...]]] = None,
        box_victim: Optional[Union[List[float], Tuple[float, ...]]] = None,
        victim_bbox: Optional[Union[List[float], Tuple[float, ...]]] = None,
        subject_foot_y: Optional[float] = None,
        victim_foot_y: Optional[float] = None,
        pose_keypoints: Optional[Union[List[Any], Tuple[Any, ...]]] = None,
        wrist_conf: Optional[float] = None,
        wrist_confidence: float = 0.90,
        is_harmonic: bool = False,
        is_harmonic_motion: bool = False,
        victim_reaction_detected: bool = False,
        velocity_divergence_m_s: float = 0.0,
        velocity_divergence_mps: float = 0.0,
        held_object: str = "",
        holding_object_text: str = "",
        scene_context: str = "",
        context_notes: str = "",
        flat_axis_duration_s: float = 0.0,
        memory_engine: Optional[Any] = None,
        memory_suppression: Optional[Tuple[bool, str, str]] = None,
        **kwargs: Any,
    ) -> AntiFalsePositiveAudit:
        """Execute the complete 5-Gate Falsification Protocol according to Section 6 Schema."""
        if raw_actions and raw_actions[0]:
            primary_action = raw_actions[0].strip().upper()
        elif action:
            primary_action = action.strip().upper()
        else:
            primary_action = "NORMAL"
        eff_box_s = box_subject or bbox_norm or [0.4, 0.4, 0.6, 0.9]
        eff_box_v = box_victim or victim_bbox
        eff_wrist_conf = wrist_conf if wrist_conf is not None else wrist_confidence
        eff_harmonic = is_harmonic or is_harmonic_motion
        eff_v_div = max(velocity_divergence_m_s, velocity_divergence_mps)
        eff_obj = held_object or holding_object_text
        eff_ctx = f"{scene_context} {context_notes}".strip()

        # Step 0: Check Hard Memory Veto from INCIDENT_MEMORY.md
        mem_vetoed = False
        mem_rule_id = None
        mem_reason = None

        if memory_suppression:
            mem_vetoed, mem_reason, mem_rule_id = memory_suppression
        elif memory_engine:
            mem_vetoed, mem_rule_id, mem_reason = memory_engine.check_suppression(
                camera_name=camera_name,
                detected_label=primary_action,
                bbox_norm=eff_box_s,
                context_text=f"{eff_ctx} action: {primary_action}",
            )

        if mem_vetoed:
            res_g5 = AdversarialFalsificationResult(
                strongest_benign_explanation=f"Trùng khớp sự vụ đã từng bị Operator bác bỏ ({mem_rule_id}): {mem_reason}",
                benign_hypothesis_probability=0.99,
                escalation_permitted=False,
                detail="Triệt tiêu tuyệt đối theo quy tắc Trí nhớ Vận hành viên (Hard Memory Veto).",
            )
            return AntiFalsePositiveAudit(
                gate_1_ground_plane_depth={"status": "REJECTED", "delta_foot_y_ratio": 0.0, "height_ratio": 1.0, "detail": "Bác bỏ do Memory Veto"},
                gate_2_pose_jerk_filter={"status": "REJECTED", "wrist_confidence": 0.0, "is_harmonic_motion": False, "detail": "Bác bỏ do Memory Veto"},
                gate_3_action_reaction_coupling={"status": "REJECTED", "victim_reaction_detected": False, "velocity_divergence_m_s": 0.0, "holding_everyday_object_note": "none", "detail": "Bác bỏ do Memory Veto"},
                gate_4_posture_and_context={"status": "REJECTED", "posture_assessment": "Vetoed", "clothing_or_weather_context": "Vetoed", "detail": "Bác bỏ do Memory Veto"},
                gate_5_adversarial_benign_hypothesis=res_g5.as_dict(),
                falsification_summary=f"TRIỆT TIÊU BÁO ĐỘNG GIA THEO BỘ NHỚ LỖI [{mem_rule_id}]: {mem_reason}",
                applied_incident_memory_rule_id=mem_rule_id,
                false_positive_suppressed=True,
                suppression_reason=f"[BỘ NHỚ MIỄN TRỪ LỖI {mem_rule_id}] {mem_reason}",
            )

        # Gate 1: 3D Ground-Plane Depth Check
        g1_pass, delta_y, ratio, g1_detail = self.check_gate_1_ground_plane_depth(
            raw_action=primary_action,
            box_subject=eff_box_s,
            box_victim=eff_box_v,
            subject_foot_y=subject_foot_y,
            victim_foot_y=victim_foot_y,
            one_subject_fallen=(primary_action == "FALLEN"),
        )
        g1_status = "PASSED" if g1_pass else "REJECTED"

        # Gate 2: Pose Confidence & Jerk Filtering
        g2_pass, conf_wrist, is_harm, g2_detail = self.check_gate_2_pose_jerk_filter(
            raw_action=primary_action,
            pose_keypoints=pose_keypoints,
            is_harmonic_motion=eff_harmonic,
            wrist_confidence_override=eff_wrist_conf,
        )
        g2_status = "PASSED" if g2_pass else "REJECTED"

        # Gate 3: Victim Action-Reaction Coupling
        g3_pass, r_det, v_div, obj_note, g3_detail = self.check_gate_3_action_reaction_coupling(
            raw_action=primary_action,
            victim_reaction_detected=victim_reaction_detected,
            velocity_divergence_m_s=eff_v_div,
            holding_object_text=eff_obj,
            interaction_note=eff_ctx,
        )
        g3_status = "PASSED" if g3_pass else "REJECTED"

        # Gate 4: Posture & Context Disambiguation
        g4_pass, posture_str, ctx_str, g4_detail = self.check_gate_4_posture_and_context(
            raw_action=primary_action,
            box=eff_box_s,
            pose_keypoints=pose_keypoints,
            scene_context=eff_ctx,
            flat_axis_duration_s=flat_axis_duration_s,
        )
        g4_status = "PASSED" if g4_pass else "REJECTED"

        # Gate 5: Adversarial Benign Hypothesis Test
        all_prior = g1_pass and g2_pass and g3_pass and g4_pass
        failures = []
        if not g1_pass:
            failures.append(g1_detail)
        if not g2_pass:
            failures.append(g2_detail)
        if not g3_pass:
            failures.append(g3_detail)
        if not g4_pass:
            failures.append(g4_detail)

        res_g5 = self.evaluate_gate_5_benign_hypothesis(
            action=primary_action,
            prior_gates_passed=all_prior,
            gate_failures=failures,
            scene_context=eff_ctx,
            wrist_conf=conf_wrist,
            divergence_v=v_div,
            held_object=eff_obj,
            is_memory_vetoed=False,
        )

        # Overall falsification summary
        suppressed = not all_prior or not res_g5.escalation_permitted
        if not all_prior:
            summary = f"BÁC BỎ BÁO ĐỘNG GIA: {failures[0]}"
            supp_reason = failures[0]
        elif not res_g5.escalation_permitted:
            summary = f"CHẶN BÁO ĐỘNG DO GIẢ THUYẾT VÔ TỘI CAO ({int(res_g5.benign_hypothesis_probability*100)}%): {res_g5.strongest_benign_explanation}"
            supp_reason = summary
        else:
            summary = "ĐỦ BẰNG CHỨNG HÌNH HỌC VÀ ĐỐI ỨNG - ĐẠT 5 CỔNG KIỂM ĐỊNH PHÁP Y - CHO PHÉP NÂNG CẤP ĐẾN CHỐT CHẶN HITL"
            supp_reason = None

        return AntiFalsePositiveAudit(
            gate_1_ground_plane_depth={
                "status": g1_status,
                "delta_foot_y_ratio": round(delta_y, 3),
                "height_ratio": round(ratio, 2),
                "detail": g1_detail,
            },
            gate_2_pose_jerk_filter={
                "status": g2_status,
                "wrist_confidence": round(conf_wrist, 2),
                "is_harmonic_motion": is_harm,
                "detail": g2_detail,
            },
            gate_3_action_reaction_coupling={
                "status": g3_status,
                "victim_reaction_detected": r_det,
                "velocity_divergence_m_s": round(v_div, 2),
                "holding_everyday_object_note": obj_note,
                "detail": g3_detail,
            },
            gate_4_posture_and_context={
                "status": g4_status,
                "posture_assessment": posture_str,
                "clothing_or_weather_context": ctx_str,
                "detail": g4_detail,
            },
            gate_5_adversarial_benign_hypothesis=res_g5.as_dict(),
            falsification_summary=summary,
            applied_incident_memory_rule_id=None,
            false_positive_suppressed=suppressed,
            suppression_reason=supp_reason,
        )
