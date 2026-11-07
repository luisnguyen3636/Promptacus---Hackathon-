# BỘ NHỚ MIỄN TRỪ LỖI VẬN HÀNH VIÊN (INCIDENT_MEMORY.md)
# Dùng để triệt tiêu 100% các báo động giả đã từng bị Con người (Human Operator) bác bỏ

```json
[
  {
    "rule_id": "FP_RULE_001",
    "camera_name": "CAM_01 - Cổng Trường Chu Văn An",
    "target_label": "RESTRAINING",
    "bbox_normalized": [0.15, 0.40, 0.35, 0.75],
    "context_keywords": ["hugging", "students", "khoác vai", "học sinh"],
    "suppression_reason": "Hai học sinh khoác vai chào nhau bị mô hình nhận nhầm là khống chế kẹp cổ",
    "operator_id": "OPERATOR_HA_LE",
    "status": "DISMISS_FALSE_POSITIVE",
    "created_at": "2026-11-06T14:20:00Z"
  },
  {
    "rule_id": "FP_RULE_002",
    "camera_name": "CAM_02 - Hẻm 12 Đinh Bộ Lĩnh",
    "target_label": "WEAPON_THREAT",
    "bbox_normalized": [0.60, 0.20, 0.85, 0.65],
    "context_keywords": ["umbrella", "ô dù", "que gậy cầm tay"],
    "suppression_reason": "Người dân cầm dù che mưa màu đen vung tay chỉ đường bị nhận nhầm là hung khí gậy",
    "operator_id": "OPERATOR_TRAN_MINH",
    "status": "DISMISS_FALSE_POSITIVE",
    "created_at": "2026-11-06T16:45:00Z"
  },
  {
    "rule_id": "FP_RULE_003",
    "camera_name": "CAM_03 - Bãi Xe Khu B",
    "target_label": "LOITERING",
    "bbox_normalized": [0.05, 0.10, 0.40, 0.50],
    "context_keywords": ["security_guard", "bảo vệ trực", "đi tuần"],
    "suppression_reason": "Bảo vệ đi tuần kiểm tra vé xe định kỳ trong bãi xe không phải đối tượng lảng vảng tiền phạm tội",
    "operator_id": "OPERATOR_NGUYEN_AN",
    "status": "DISMISS_FALSE_POSITIVE",
    "created_at": "2026-11-07T09:10:00Z"
  }
]
```
