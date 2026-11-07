# KẾ HOẠCH TRIỂN KHAI: HỆ THỐNG QUY TẮC NHẬN DIỆN HÀNH VI (RULE) & ĐỘNG CƠ ĐÁNH DẤU MỨC ĐỘ ĐE DỌA (ENGINE)
**Mã tài liệu:** `PLAN-URBAN-RULE-ENGINE-01`  
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Phân hệ:** Tầng 2 (AI/Pose & Behavior Analytics) & Tầng 3 (Tracking & Dynamic Threat Scoring)  
**Căn cứ pháp lý & quy trình:** Tuân thủ `AGENTS.md` (Stage 2 SDD) và `SPEC-URBAN-RULE-ENGINE-01`.  
**Trạng thái:** Chờ phê duyệt từ Lead Architect (`[WAITING FOR PLAN APPROVAL]`)

---

## 1. DANH MỤC TỆP TIN THỰC HIỆN (FILE MANIFEST)

| Thao tác | Đường dẫn tệp | Trách nhiệm chính / Nội dung thực hiện |
| :--- | :--- | :--- |
| **Tạo mới** | `Rule/base_rule.py` | Lớp cơ sở trừu tượng `BaseBehaviorRule` và các schema kết quả đánh giá quy tắc `RuleEvaluationResult`. |
| **Tạo mới** | `Rule/single_rules.py` | Triển khai 6 quy tắc đơn cá thể: `FallenCollapseRule`, `HandsUpDistressRule`, `SuddenFleeingRule`, `CrouchingProwlingRule`, `LoiteringRule`, `ConcealedReachRule`. |
| **Tạo mới** | `Rule/multi_rules.py` | Triển khai 4 quy tắc tương tác đa cá thể: `FightingStrikeRule`, `GrapplingStruggleRule`, `ChasingPursuitRule`, `SurroundedVictimRule`. |
| **Tạo mới** | `Rule/registry.py` | Lớp `RuleRegistry` tập trung quản lý việc nạp, kích hoạt, vô hiệu hóa và phân phối đánh giá các rules. |
| **Tạo mới** | `Rule/__init__.py` | Export module công khai cho phân hệ `Rule/`. |
| **Tạo mới** | `Engine/threat_models.py` | Định nghĩa Enums (`ThreatLevel`, `BehaviorType`, `BehaviorCategory`) và Pydantic Models (`SubjectKinematicsSnapshot`, `SubjectThreatMark`, `SOCEngineOutput`). |
| **Tạo mới** | `Engine/scoring.py` | Triển khai thuật toán chấm điểm rủi ro động theo chuỗi thời gian (`DynamicThreatScorer`) với hệ số suy giảm $\lambda$ và tích lũy dwell time. |
| **Tạo mới** | `Engine/state_machine.py` | Triển khai máy trạng thái trễ chống nhảy nhãn (`HysteresisDebounceStateMachine`) với ngưỡng $N_{\text{enter}}=8$, $N_{\text{exit}}=12$, và Fast-track $5$ frames cho CRITICAL. |
| **Tạo mới** | `Engine/threat_engine.py` | Lớp điều phối chính `ThreatMarkingEngine` kết hợp Rule Registry + Scorer + State Machine, trả về `SOCEngineOutput` và xuất log kiểm toán. |
| **Tạo mới** | `Engine/__init__.py` | Export module công khai cho phân hệ `Engine/`. |
| **Tạo mới** | `test_rules_and_engine.py` | Kịch bản kiểm thử tự động toàn diện kiểm chứng 10 rules, chống nhảy mark, fast-track và tương thích JSON contract. |

---

## 2. CHỮ KÝ HÀM & THIẾT KẾ CHI TIẾT (FUNCTION SIGNATURES)

### 2.1. Phân hệ Quy tắc (`Rule/`)

#### `Rule/base_rule.py`
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from Engine.threat_models import (
    BehaviorType,
    BehaviorCategory,
    SubjectKinematicsSnapshot,
    RuleEvaluationResult
)

class BaseBehaviorRule(ABC):
    def __init__(self, name: str, behavior_type: BehaviorType, category: BehaviorCategory, enabled: bool = True) -> None:
        self.name: str = name
        self.behavior_type: BehaviorType = behavior_type
        self.category: BehaviorCategory = category
        self.enabled: bool = enabled

    @abstractmethod
    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        """Đánh giá dữ liệu sinh trắc học và trả về RuleEvaluationResult."""
        pass
```

#### `Rule/single_rules.py`
```python
from Rule.base_rule import BaseBehaviorRule

class FallenCollapseRule(BaseBehaviorRule):
    def __init__(self, angle_thresh: float = 55.0, aspect_ratio_thresh: float = 0.90) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class HandsUpDistressRule(BaseBehaviorRule):
    def __init__(self) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class SuddenFleeingRule(BaseBehaviorRule):
    def __init__(self, speed_multiplier: float = 1.85, accel_threshold: float = 1.2) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class CrouchingProwlingRule(BaseBehaviorRule):
    def __init__(self, aspect_ratio_thresh: float = 1.30, spine_angle_range: tuple = (25.0, 50.0)) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class LoiteringRule(BaseBehaviorRule):
    def __init__(self, dwell_thresh_med: float = 10.0, dwell_thresh_high: float = 20.0, max_net_disp: float = 120.0) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class ConcealedReachRule(BaseBehaviorRule):
    def __init__(self, min_dwell_seconds: float = 3.0) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...
```

#### `Rule/multi_rules.py`
```python
from Rule.base_rule import BaseBehaviorRule

class FightingStrikeRule(BaseBehaviorRule):
    def __init__(self, proximity_ratio: float = 1.35, wrist_energy_thresh: float = 1200.0) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class GrapplingStruggleRule(BaseBehaviorRule):
    def __init__(self, iou_thresh: float = 0.35, spine_velocity_thresh: float = 35.0) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class ChasingPursuitRule(BaseBehaviorRule):
    def __init__(self, speed_thresh: float = 1.6, cos_sim_thresh: float = 0.85) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...

class SurroundedVictimRule(BaseBehaviorRule):
    def __init__(self, min_surrounders: int = 2, distance_ratio: float = 1.8) -> None: ...
    def evaluate(self, subject, history, all_subjects) -> RuleEvaluationResult: ...
```

#### `Rule/registry.py`
```python
class RuleRegistry:
    def __init__(self) -> None:
        self._rules: Dict[str, BaseBehaviorRule] = {}
        self._register_default_rules()

    def register(self, rule: BaseBehaviorRule) -> None: ...
    def set_enabled(self, rule_name: str, enabled: bool) -> None: ...
    def evaluate_all(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> List[RuleEvaluationResult]: ...
```

---

### 2.2. Phân hệ Động cơ Đánh dấu Mức độ (`Engine/`)

#### `Engine/threat_models.py`
- Cung cấp toàn bộ các schemas định nghĩa tại Mục 2 của `SPEC.md`:
  - `ThreatLevel` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `BehaviorType`, `BehaviorCategory`
  - `KeypointData`, `SubjectKinematicsSnapshot`
  - `RuleEvaluationResult`, `SubjectThreatMark`, `SOCEngineOutput`

#### `Engine/scoring.py`
```python
class DynamicThreatScorer:
    def __init__(
        self,
        inertia_lambda: float = 0.70,
        dwell_penalty_beta: float = 0.05,
        max_dwell_penalty: float = 0.15,
        interaction_bonus: float = 0.10
    ) -> None: ...

    def compute_score(
        self,
        prev_score: float,
        matched_evaluations: List[RuleEvaluationResult],
        state_dwell_seconds: float,
        has_hostile_interaction: bool
    ) -> float:
        """Tính điểm đe dọa động St = lambda * S_{t-1} + (1 - lambda) * S_max + Dwell + Interaction."""
        ...
```

#### `Engine/state_machine.py`
```python
class HysteresisDebounceStateMachine:
    def __init__(
        self,
        enter_debounce_frames: int = 8,
        exit_debounce_frames: int = 12,
        fast_track_critical_frames: int = 5
    ) -> None:
        self._tracks_state: Dict[int, Dict[str, Any]] = {}

    def update_track_state(
        self,
        track_id: int,
        raw_threat_level: ThreatLevel,
        raw_score: float,
        raw_behavior: BehaviorType,
        raw_category: BehaviorCategory,
        timestamp: float
    ) -> Tuple[ThreatLevel, float, BehaviorType, BehaviorCategory, float, bool]:
        """
        Khử rung giật nhãn qua máy trạng thái trễ.
        Trả về: (confirmed_level, confirmed_score, confirmed_behavior, confirmed_category, state_dwell, is_escalated)
        """
        ...
```

#### `Engine/threat_engine.py`
```python
class ThreatMarkingEngine:
    def __init__(
        self,
        history_window_size: int = 30,
        output_dir: str = "output"
    ) -> None:
        self.registry: RuleRegistry = RuleRegistry()
        self.scorer: DynamicThreatScorer = DynamicThreatScorer()
        self.state_machine: HysteresisDebounceStateMachine = HysteresisDebounceStateMachine()
        self.history_buffers: Dict[int, List[SubjectKinematicsSnapshot]] = {}

    def process_frame(
        self,
        frame_index: int,
        subjects: List[SubjectKinematicsSnapshot],
        timestamp: Optional[float] = None
    ) -> SOCEngineOutput:
        """
        Hàm trung tâm điều phối toàn bộ luồng:
        1. Nhận danh sách snapshot đối tượng
        2. Chạy RuleRegistry.evaluate_all()
        3. Chấm điểm qua DynamicThreatScorer
        4. Làm mịn và ổn định qua HysteresisDebounceStateMachine
        5. Gán Threat Mark (màu sắc, chốt chặn HITL)
        6. Đóng gói SOCEngineOutput tương thích API contract
        """
        ...
```

---

## 3. DANH SÁCH THƯ VIỆN & GIẢI TRÌNH (DEPENDENCIES)

Hệ thống sử dụng các thư viện chuẩn, gọn nhẹ, đã có sẵn trong môi trường Python và không yêu cầu cài thêm các gói nặng độc quyền:
- **`pydantic>=2.0.0`**: Định nghĩa Data Schema nghiêm ngặt, tự động xác thực kiểu dữ liệu và hỗ trợ serialize sang JSON trực tiếp cho API Dashboard.
- **`numpy>=1.24.0`**: Tính toán đại số tuyến tính, khoảng cách Euclidean, tính góc nghiêng vector cột sống và tích vô hướng (cosine similarity).

---

## 4. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION & TEST PLAN)

Tệp kiểm thử tự động `test_rules_and_engine.py` sẽ thực hiện 6 giai đoạn xác minh độc lập:

1. **Test Phase 1: Kiểm thử Đơn vị 6 Single-Person Rules**
   - Giả lập dữ liệu khung xương tổng hợp (Synthetic Skeleton) cho từng tư thế: Đứng thẳng (`NORMAL`), Ngã quỵ (`FALLEN`), Giơ 2 tay quá đầu (`HANDS_UP`), Bỏ chạy tốc độ cao (`SUDDEN_FLEEING`), Cúi khom (`CROUCHING`), Lảng vảng (`LOITERING`).
   - *Kỳ vọng:* Từng Rule phải kích hoạt chính xác loại hành vi (`behavior_type`) và `base_threat_score` tương ứng.
2. **Test Phase 2: Kiểm thử Đơn vị 4 Multi-Person Rules**
   - Giả lập cặp đối tượng tương tác: Ẩu đả vung tay cận chiến (`FIGHTING_STRIKE`), Giằng co vật lộn (`GRAPPLING`), Truy đuổi rượt nhau (`CHASING`), Bao vây hội đồng (`SURROUNDED_VICTIM`).
   - *Kỳ vọng:* Rule ghép cặp chính xác và trả về `interacting_with_track_ids`.
3. **Test Phase 3: Kiểm thử Khử Nhảy Mark (Anti-Flapping Debounce)**
   - Bơm chuỗi 15 frames: 5 frames `LOW` $\to$ 2 frames nhiễu bất chợt `HIGH` $\to$ 8 frames `LOW`.
   - *Kỳ vọng:* Engine vẫn giữ vững Mark `LOW`, lọc bỏ hoàn toàn 2 frames nhiễu.
4. **Test Phase 4: Kiểm thử Fast-Track Bạo lực khẩn cấp**
   - Bơm chuỗi 6 frames `FIGHTING_STRIKE` liên tiếp.
   - *Kỳ vọng:* Tại frame thứ 5 ($N_{\text{enter}}=5$), Engine lập tức xác nhận Mark `CRITICAL` và kích hoạt cờ `requires_operator_attention = True`.
5. **Test Phase 5: Kiểm thử Leo thang theo Dwell Time**
   - Giả lập đối tượng duy trì `LOITERING` từ $0\text{s} \to 25\text{s}$.
   - *Kỳ vọng:* Điểm số tự động leo thang từ `MEDIUM` ($S \approx 0.52$) lên `HIGH` ($S > 0.60$) khi vượt ngưỡng 20 giây.
6. **Test Phase 6: Kiểm thử Tương thích Schema API Dashboard**
   - Serialize `SOCEngineOutput` thành JSON string và parse lại.
   - *Kỳ vọng:* Cấu trúc JSON tuân thủ 100% các trường quy định trong `Dashboard/Back End/standard.md`.

---

[WAITING FOR PLAN APPROVAL]
