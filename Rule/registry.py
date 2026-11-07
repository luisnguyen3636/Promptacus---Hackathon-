"""
Rule Registry for Urban Safety AI-SOC Rule System.
Manages rule lifecycle, activation/deactivation, and centralized evaluation.
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01.
"""

from typing import List, Dict, Optional
from Rule.base_rule import BaseBehaviorRule
from Rule.single_rules import (
    FallenCollapseRule,
    HandsUpDistressRule,
    SuddenFleeingRule,
    CrouchingProwlingRule,
    LoiteringRule,
    ConcealedReachRule
)
from Rule.multi_rules import (
    FightingStrikeRule,
    GrapplingStruggleRule,
    ChasingPursuitRule,
    SurroundedVictimRule
)
from Engine.threat_models import (
    SubjectKinematicsSnapshot,
    RuleEvaluationResult
)


class RuleRegistry:
    """
    Central repository of behavior rules.
    Allows dynamic registration, enabling/disabling, and batched execution.
    """

    def __init__(self, register_defaults: bool = True) -> None:
        self._rules: Dict[str, BaseBehaviorRule] = {}
        if register_defaults:
            self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Registers the 10 core urban safety rules."""
        # Single-subject rules
        self.register(FallenCollapseRule())
        self.register(HandsUpDistressRule())
        self.register(SuddenFleeingRule())
        self.register(CrouchingProwlingRule())
        self.register(LoiteringRule())
        self.register(ConcealedReachRule())

        # Multi-subject interaction rules
        self.register(FightingStrikeRule())
        self.register(GrapplingStruggleRule())
        self.register(ChasingPursuitRule())
        self.register(SurroundedVictimRule())

    def register(self, rule: BaseBehaviorRule) -> None:
        """Registers a new behavior rule into the system."""
        self._rules[rule.name] = rule

    def unregister(self, rule_name: str) -> Optional[BaseBehaviorRule]:
        """Removes a rule by name."""
        return self._rules.pop(rule_name, None)

    def set_enabled(self, rule_name: str, enabled: bool) -> bool:
        """Enables or disables an existing rule."""
        if rule_name in self._rules:
            self._rules[rule_name].enabled = enabled
            return True
        return False

    def get_rule(self, rule_name: str) -> Optional[BaseBehaviorRule]:
        """Retrieves a rule by name."""
        return self._rules.get(rule_name)

    @property
    def registered_rules(self) -> List[str]:
        """Returns names of all registered rules."""
        return list(self._rules.keys())

    def evaluate_all(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> List[RuleEvaluationResult]:
        """
        Executes all enabled rules against the given subject snapshot.
        Returns a list of all matched evaluations.
        """
        matched_results: List[RuleEvaluationResult] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            try:
                res = rule.evaluate(subject, history, all_subjects)
                if res.matched:
                    matched_results.append(res)
            except Exception as e:
                # Log without silent crash
                print(f"[RuleRegistry] Warning: Error evaluating rule '{rule.name}' ({e})")

        return matched_results
