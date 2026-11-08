"""Common Criminal Action Detection Rules Engine Export for Urban Safety AI-SOC."""

import sys
import os

# Ensure package import path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "AI", "Human", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from urbansoc.behavior.criminal_rules import (
    CommonCriminalRulesEngine,
    CriminalRuleEvaluation,
    criminal_rules_engine,
)

__all__ = [
    "CommonCriminalRulesEngine",
    "CriminalRuleEvaluation",
    "criminal_rules_engine",
]
