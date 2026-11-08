"""Common Criminal Action Detection Rules Engine (AI-SOC Forensic Criminal Rules).

Comprehensive rule suite for detecting 10 high-priority criminal behaviors in urban surveillance:
1. WEAPON_BRANDISHING (Rút/cầm hung khí: súng, dao, gậy)
2. VIOLENT_ASSAULT (Ẩu đả, bạo lực thể xác, đấm đá)
3. ROBBERY_SNATCHING (Cướp giật tài sản rồi tẩu thoát)
4. FLEEING_HIGH_SPEED (Bỏ chạy tốc độ cao khỏi hiện trường)
5. LOITERING_SUSPICIOUS (Lảng vảng tiền phạm tội tại khu vực nhạy cảm)
6. PERIMETER_INTRUSION (Đột nhập trái phép vùng cấm, trèo tường/rào)
7. VANDALISM_TAMPERING (Phá hoại tài sản, làm hỏng camera/thiết bị)
8. VICTIM_COLLAPSED (Nạn nhân ngã quỵ bất động sau va chạm/tấn công)
9. HOSTAGE_CHOKEHOLD (Bắt giữ, khống chế, siết cổ con tin)
10. STALKING_PURSUIT (Bám đuôi, theo dõi nạn nhân cự ly gần khả nghi)
"""

from dataclasses import dataclass
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from urbansoc.mmaction2.models import CriminalActionCategory
from urbansoc.telemetry.debug_logger import debug_logger


@dataclass
class CriminalRuleEvaluation:
    """Evaluation result from criminal rule engine."""
    rule_id: str
    action_category: CriminalActionCategory
    is_triggered: bool
    confidence: float
    threat_score: float
    threat_level: str
    forensic_reasoning: str
    legal_basis: str
    falsification_gates_passed: bool
    suggested_operator_action: str


class CommonCriminalRulesEngine:
    """Master evaluator for 10 common criminal behaviors."""

    def __init__(self) -> None:
        self.rules_registry = {
            "CRIM-01": "WEAPON_BRANDISHING",
            "CRIM-02": "VIOLENT_ASSAULT",
            "CRIM-03": "ROBBERY_SNATCHING",
            "CRIM-04": "FLEEING_HIGH_SPEED",
            "CRIM-05": "LOITERING_SUSPICIOUS",
            "CRIM-06": "PERIMETER_INTRUSION",
            "CRIM-07": "VANDALISM_TAMPERING",
            "CRIM-08": "VICTIM_COLLAPSED",
            "CRIM-09": "HOSTAGE_CHOKEHOLD",
            "CRIM-10": "STALKING_PURSUIT",
        }

    # 1. Rút / Cầm hung khí
    def evaluate_weapon_brandishing(
        self,
        wrist_distance: float,
        arm_extension: float,
        is_firing_plane: bool,
        hand_velocity: float = 0.0,
        is_holding_sharp_object: bool = False,
    ) -> CriminalRuleEvaluation:
        """Evaluate brandishing firearms, blades, or blunt weapons."""
        triggered = (wrist_distance < 0.25 and arm_extension > 0.40 and is_firing_plane) or is_holding_sharp_object
        conf = 0.92 if triggered else 0.15
        score = 92.0 if triggered else 0.0
        level = "CRITICAL" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-01",
            action_category=CriminalActionCategory.WEAPON_BRANDISHING,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                "Phát hiện tư thế giương vũ khí hoặc cầm nắm hung khí hướng vào đối tượng/khu vực đông người."
                if triggered else "Không phát hiện tư thế đe dọa vũ khí."
            ),
            legal_basis="Điều 134/306 BLHS: Tàng trữ, sử dụng vũ khí, hung khí nguy hiểm đe dọa an toàn công cộng",
            falsification_gates_passed=triggered,
            suggested_operator_action="KÍCH HOẠT BÁO ĐỘNG ĐỎ - ĐIỀU PHỐI LỰC LƯỢNG ĐẶC NHIỆM",
        )

    # 2. Ẩu đả / Bạo lực thể xác
    def evaluate_violent_assault(
        self,
        num_subjects: int,
        inter_subject_distance: float,
        limb_acceleration_peak: float,
        posture_instability: bool,
    ) -> CriminalRuleEvaluation:
        """Evaluate physical brawl, strikes, kicks, and mutual combat."""
        triggered = (num_subjects >= 2) and (inter_subject_distance < 0.35) and (limb_acceleration_peak > 15.0 or posture_instability)
        conf = 0.88 if triggered else 0.10
        score = 90.0 if triggered else 0.0
        level = "CRITICAL" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-02",
            action_category=CriminalActionCategory.VIOLENT_ASSAULT,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                f"Phát hiện xô xát ẩu đả bạo lực giữa {num_subjects} đối tượng với gia tốc chi vượt ngưỡng tác chiến."
                if triggered else "Tương tác thể chất trong giới hạn hòa bình."
            ),
            legal_basis="Điều 134 BLHS: Cố ý gây thương tích hoặc gây tổn hại sức khỏe cho người khác",
            falsification_gates_passed=triggered,
            suggested_operator_action="ĐIỀU ĐỘNG TỔ TUẦN TRA ĐẾN NGĂN CHẶN XUNG ĐỘT",
        )

    # 3. Cướp giật tài sản
    def evaluate_robbery_snatching(
        self,
        proximity_duration_sec: float,
        sudden_divergence_speed: float,
        victim_arm_recoil: bool,
    ) -> CriminalRuleEvaluation:
        """Evaluate drive-by or pedestrian purse/phone snatching."""
        triggered = (proximity_duration_sec < 2.5) and (sudden_divergence_speed > 3.0) and victim_arm_recoil
        conf = 0.90 if triggered else 0.12
        score = 88.0 if triggered else 0.0
        level = "HIGH" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-03",
            action_category=CriminalActionCategory.ROBBERY_SNATCHING,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                "Phát hiện hành vi tiếp cận chớp nhoáng, giật đồ vật khiến nạn nhân giật lùi, sau đó tăng tốc tháo chạy."
                if triggered else "Không phát hiện động thái cướp giật."
            ),
            legal_basis="Điều 171 BLHS: Tội cướp giật tài sản",
            falsification_gates_passed=triggered,
            suggested_operator_action="KÍCH HOẠT TRUY VẾT CAMERA TRÊN HÀNH LANG TẨU THOÁT",
        )

    # 4. Bỏ chạy tốc độ cao
    def evaluate_fleeing_high_speed(
        self,
        normalized_speed: float,
        is_sportswear: bool = False,
        scene_type: str = "ALLEYWAY",
    ) -> CriminalRuleEvaluation:
        """Evaluate escaping scene after commission of an offense."""
        # Falsification: Sportswear on running track / park is NOT fleeing crime
        triggered = (normalized_speed >= 2.2) and not (is_sportswear and scene_type in ("PARK", "SPORTS_GROUND"))
        conf = 0.85 if triggered else 0.20
        score = 78.0 if triggered else 0.0
        level = "HIGH" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-04",
            action_category=CriminalActionCategory.FLEEING_HIGH_SPEED,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                f"Đối tượng di chuyển bỏ chạy tháo thân bất thường (tốc độ chuẩn hóa {normalized_speed:.2f} h/s) tại {scene_type}."
                if triggered else "Tốc độ di chuyển bình thường hoặc hoạt động thể dục."
            ),
            legal_basis="Dấu hiệu trốn tránh lực lượng chức năng hoặc tẩu thoát khỏi hiện trường phạm tội",
            falsification_gates_passed=triggered,
            suggested_operator_action="CẢNH BÁO ĐÓN LÕNG TẠI CÁC CAMERA TIẾP GIÁP",
        )

    # 5. Lảng vảng nghi vấn (Loitering)
    def evaluate_loitering_suspicious(
        self,
        dwell_time_seconds: float,
        zone_type: str = "RESTRICTED",
        frequent_direction_changes: bool = False,
    ) -> CriminalRuleEvaluation:
        """Evaluate pre-crime casing and suspicious loitering."""
        triggered = (dwell_time_seconds >= 60.0) and (zone_type in ("RESTRICTED", "VAULT", "BLIND_SPOT"))
        conf = 0.80 if triggered else 0.15
        score = 65.0 if triggered else 0.0
        level = "MEDIUM" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-05",
            action_category=CriminalActionCategory.LOITERING_SUSPICIOUS,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                f"Đối tượng lảng vảng bất thường {dwell_time_seconds:.0f}s tại khu vực {zone_type} có dấu hiệu do thám mục tiêu."
                if triggered else "Thời gian dừng đỗ trong giới hạn cho phép."
            ),
            legal_basis="Dấu hiệu chuẩn bị phạm tội hoặc thăm dò hệ thống an ninh",
            falsification_gates_passed=triggered,
            suggested_operator_action="THEO DÕI LIÊN TỤC VÀ NHẮC NHỞ QUA LOA AN NINH",
        )

    # 6. Đột nhập vùng cấm
    def evaluate_perimeter_intrusion(
        self,
        is_inside_restricted_polygon: bool,
        crossed_virtual_tripwire: bool,
    ) -> CriminalRuleEvaluation:
        """Evaluate restricted boundary breach or fence climbing."""
        triggered = is_inside_restricted_polygon or crossed_virtual_tripwire
        conf = 0.94 if triggered else 0.05
        score = 80.0 if triggered else 0.0
        level = "HIGH" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-06",
            action_category=CriminalActionCategory.PERIMETER_INTRUSION,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                "Phát hiện đối tượng xâm nhập trái phép vượt hàng rào điện tử hoặc đi vào vùng cấm an ninh."
                if triggered else "Vị trí đối tượng nằm trong hành lang công cộng."
            ),
            legal_basis="Điều 157 BLHS: Tội xâm phạm chỗ ở/cơ sở an ninh được pháp luật bảo vệ",
            falsification_gates_passed=triggered,
            suggested_operator_action="KÍCH HOẠT KHÓA CỬA TỰ ĐỘNG VÀ ĐẨY CẢNH BÁO LÊN BÀN ĐIỀU HÀNH",
        )

    # 7. Phá hoại tài sản / camera
    def evaluate_vandalism_tampering(
        self,
        abrupt_video_blindness: bool,
        high_kinetic_strike_on_asset: bool,
    ) -> CriminalRuleEvaluation:
        """Evaluate property destruction or camera tampering."""
        triggered = abrupt_video_blindness or high_kinetic_strike_on_asset
        conf = 0.89 if triggered else 0.10
        score = 82.0 if triggered else 0.0
        level = "HIGH" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-07",
            action_category=CriminalActionCategory.VANDALISM_TAMPERING,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                "Phát hiện tác động vật lý mạnh phá hoại tài sản công cộng hoặc làm mù camera quan sát."
                if triggered else "Không phát hiện hành vi phá hoại tài sản."
            ),
            legal_basis="Điều 178 BLHS: Tội hủy hoại hoặc cố ý làm hư hỏng tài sản",
            falsification_gates_passed=triggered,
            suggested_operator_action="ĐIỀU PHỐI BẢO VỆ HIỆN TRƯỜNG VÀ CHUYỂN CAMERA DỰ PHÒNG",
        )

    # 8. Nạn nhân ngã quỵ bất động
    def evaluate_victim_collapsed(
        self,
        aspect_ratio_w_over_h: float,
        vertical_centroid_norm: float,
        motion_energy: float,
        dwell_down_seconds: float,
    ) -> CriminalRuleEvaluation:
        """Evaluate incapacitated victim lying on the ground."""
        triggered = (aspect_ratio_w_over_h >= 1.30) and (vertical_centroid_norm >= 0.50) and (motion_energy < 0.15) and (dwell_down_seconds >= 2.0)
        conf = 0.93 if triggered else 0.08
        score = 85.0 if triggered else 0.0
        level = "CRITICAL" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-08",
            action_category=CriminalActionCategory.VIOLENT_ASSAULT,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                f"Nạn nhân nằm bất động dưới mặt đất {dwell_down_seconds:.1f}s với tỷ lệ ngang {aspect_ratio_w_over_h:.2f}, không có dấu hiệu cử động."
                if triggered else "Tư thế thẳng đứng bình thường hoặc cử động linh hoạt."
            ),
            legal_basis="Nghi vấn hậu quả cố ý gây thương tích hoặc tai nạn cần cứu trợ y tế khẩn cấp",
            falsification_gates_passed=triggered,
            suggested_operator_action="GỌI CẤP CỨU Y TẾ 115 VÀ ĐIỀU PHỐI ĐỘI AN NINH HIỆN TRƯỜNG",
        )

    # 9. Khống chế / Bắt giữ con tin
    def evaluate_hostage_chokehold(
        self,
        inter_subject_neck_proximity: float,
        victim_arm_pinned: bool,
    ) -> CriminalRuleEvaluation:
        """Evaluate hostage situation, rear chokehold, or abduction."""
        triggered = (inter_subject_neck_proximity < 0.18) and victim_arm_pinned
        conf = 0.95 if triggered else 0.05
        score = 95.0 if triggered else 0.0
        level = "CRITICAL" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-09",
            action_category=CriminalActionCategory.HOSTAGE_CHOKEHOLD,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                "Phát hiện tư thế siết cổ / khống chế nạn nhân từ phía sau cự ly sát, nạn nhân bị kẹp tay hạn chế phản kháng."
                if triggered else "Không có dấu hiệu khống chế bạo lực."
            ),
            legal_basis="Điều 157 BLHS: Bắt, giữ hoặc giam người trái pháp luật; Điều 301: Bắt cóc con tin",
            falsification_gates_passed=triggered,
            suggested_operator_action="KHẨN CẤP: KÍCH HOẠT TỔ PHẢN ỨNG NHANH VÀ CÔNG AN ĐỊA BÀN",
        )

    # 10. Bám đuôi theo dõi
    def evaluate_stalking_pursuit(
        self,
        trajectory_correlation: float,
        consistent_distance_m: float,
        duration_seconds: float,
    ) -> CriminalRuleEvaluation:
        """Evaluate covert trailing and stalking of target."""
        triggered = (trajectory_correlation >= 0.85) and (3.0 <= consistent_distance_m <= 15.0) and (duration_seconds >= 15.0)
        conf = 0.82 if triggered else 0.10
        score = 72.0 if triggered else 0.0
        level = "HIGH" if triggered else "LOW"

        return CriminalRuleEvaluation(
            rule_id="CRIM-10",
            action_category=CriminalActionCategory.STALKING_PURSUIT,
            is_triggered=triggered,
            confidence=conf,
            threat_score=score,
            threat_level=level,
            forensic_reasoning=(
                f"Phát hiện bám đuôi nạn nhân suốt {duration_seconds:.0f}s với cự ly duy trì {consistent_distance_m:.1f}m và tương quan quỹ đạo {trajectory_correlation*100:.1f}%."
                if triggered else "Quỹ đạo di chuyển ngẫu nhiên của người đi đường."
            ),
            legal_basis="Dấu hiệu tiền phạm tội: Chuẩn bị cướp giật, hành hung hoặc quấy rối nguy hiểm",
            falsification_gates_passed=triggered,
            suggested_operator_action="THEO DÕI QUA CÁC CAMERA TIẾP GIÁP VÀ ĐIỀU PHỐI TUẦN TRA",
        )


# Global singleton rules engine
criminal_rules_engine = CommonCriminalRulesEngine()
common_criminal_rules_engine = criminal_rules_engine
