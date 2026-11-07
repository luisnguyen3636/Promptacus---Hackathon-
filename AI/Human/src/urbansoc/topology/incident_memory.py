"""Incident Memory Engine parsing INCIDENT_MEMORY.md to suppress 100% recurring false positives."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("urbansoc.topology.incident_memory")


def compute_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    """Compute Intersection over Union (IoU) between two normalized boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
    boxBArea = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])

    union = boxAArea + boxBArea - interArea
    if union <= 0.0:
        return 0.0
    return interArea / union


class IncidentMemoryEngine:
    """Engine responsible for loading human operator dismissals and suppressing recurring false alarms."""

    def __init__(self, memory_filepath: Optional[str] = None) -> None:
        self.memory_filepath = memory_filepath or self._find_default_memory_file()
        self.rules: List[Dict[str, Any]] = []
        self.load_memory()

    def _find_default_memory_file(self) -> str:
        candidates = [
            os.path.abspath("INCIDENT_MEMORY.md"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "INCIDENT_MEMORY.md")),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return os.path.abspath("INCIDENT_MEMORY.md")

    def load_memory(self) -> None:
        """Parse JSON blocks or structured markdown lists from INCIDENT_MEMORY.md."""
        if not os.path.exists(self.memory_filepath):
            logger.info("Incident memory file %s not found. Initializing with empty rules.", self.memory_filepath)
            self.rules = []
            return

        try:
            with open(self.memory_filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Attempt to extract JSON code block ```json ... ```
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                raw_json = match.group(1).strip()
                parsed = json.loads(raw_json)
                if isinstance(parsed, list):
                    self.rules = parsed
                    logger.info("Loaded %d false positive memory rules from %s", len(self.rules), self.memory_filepath)
                    return

            # Direct JSON parse attempt
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    self.rules = parsed
                    return
            except Exception:
                pass

        except Exception as e:
            logger.error("Error reading incident memory file %s: %e", self.memory_filepath, e)
            self.rules = []

    def check_suppression(
        self,
        camera_name: Optional[str],
        detected_label: str,
        bbox_norm: Tuple[float, float, float, float],
        context_text: str = "",
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Evaluate if detection matches any Operator dismissal rule.

        Returns:
            (is_suppressed, applied_rule_id, suppression_explanation)
        """
        clean_cam_name = (camera_name or "").strip().lower()
        clean_label = (detected_label or "").strip().upper()

        if not clean_cam_name:
            return False, None, None

        for rule in self.rules:
            rule_cam = str(rule.get("camera_name", "")).strip().lower()
            # Substring or camera ID token matching (e.g. CAM_01)
            cam_matched = (rule_cam in clean_cam_name) or (clean_cam_name in rule_cam)
            if not cam_matched:
                rule_cam_tokens = re.findall(r"cam[_\-\s]*\d+", rule_cam)
                clean_cam_tokens = re.findall(r"cam[_\-\s]*\d+", clean_cam_name)
                if rule_cam_tokens and clean_cam_tokens:
                    tok1 = re.sub(r"[\s\-]", "_", rule_cam_tokens[0])
                    tok2 = re.sub(r"[\s\-]", "_", clean_cam_tokens[0])
                    if tok1 == tok2:
                        cam_matched = True

            if not cam_matched:
                continue

            rule_label = str(rule.get("target_label", "")).strip().upper()
            if rule_label != "ALL" and rule_label != clean_label:
                continue

            # Check bounding box IoU overlap if coordinates provided
            rule_bbox = rule.get("bbox_normalized")
            iou_match = False
            if rule_bbox and len(rule_bbox) == 4:
                iou = compute_iou(bbox_norm, tuple(rule_bbox))
                if iou >= 0.70:
                    iou_match = True

            # Check contextual keyword match
            keywords = rule.get("context_keywords", [])
            keyword_match = False
            if context_text and keywords:
                for kw in keywords:
                    if kw.lower() in context_text.lower():
                        keyword_match = True
                        break

            # If either high spatial overlap (IoU > 0.70) or exact label + keyword match occurs
            if iou_match or keyword_match or (not rule_bbox and not keywords):
                rule_id = rule.get("rule_id", "FP_RULE_UNKNOWN")
                reason = rule.get("suppression_reason", "Suppressed by Operator Incident Memory")
                return True, rule_id, f"Triệt tiêu theo bộ nhớ {rule_id}: {reason}"

        return False, None, None
