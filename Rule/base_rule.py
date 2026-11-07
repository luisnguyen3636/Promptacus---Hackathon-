"""
Base Behavior Rule Interface for Urban Safety AI-SOC Rule System.
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from Engine.threat_models import (
    BehaviorType,
    BehaviorCategory,
    SubjectKinematicsSnapshot,
    RuleEvaluationResult
)


class BaseBehaviorRule(ABC):
    """
    Abstract Base Class for all individual and interaction behavior rules.
    Follows Plugin / Strategy pattern for modularity and hot-swappable rules.
    """

    def __init__(
        self,
        name: str,
        behavior_type: BehaviorType,
        category: BehaviorCategory,
        enabled: bool = True
    ) -> None:
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
        """
        Evaluates biomechanical features of the subject against the rule.

        Args:
            subject: Instantaneous kinematics snapshot of the target subject.
            history: Sliding window history of recent snapshots for this subject.
            all_subjects: Dictionary mapping track_id to snapshot for all active subjects.

        Returns:
            RuleEvaluationResult indicating whether the rule matched, confidence, and reasoning.
        """
        pass
