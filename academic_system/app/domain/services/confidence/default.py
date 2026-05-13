"""Default confidence calculator implementation."""

from typing import List

from .base import ConfidenceCalculator


class DefaultConfidenceCalculator(ConfidenceCalculator):
    """
    Base scoring starts at 100, deducts for issues.

    Deductions (in order):
    - Critical constraint (score > 1.0): -25 each (checked FIRST)
    - Tight constraint (0.8 <= score <= 1.0): -10 each
    - Bottleneck slot (>=3 competitors): -15 each
    - Lab infeasible: -40
    - Low diversity (<=3 slots): -5 each
    """

    def calculate(
        self,
        constraint_scores: List[float],
        bottleneck_count: int,
        total_faculty: int,
        lab_feasible: bool,
        low_diversity_count: int
    ) -> int:
        """Return confidence score 0-100."""
        score = 100

        # Check CRITICAL first (> 1.0), then TIGHT (>= 0.8).
        # A score of exactly 1.0 means every requested slot has a matching
        # availability slot. That is tight, but not impossible by itself.
        for cs in constraint_scores:
            if cs > 1.0:
                score -= 25
            elif cs >= 0.8:
                score -= 10

        score -= bottleneck_count * 15
        if not lab_feasible:
            score -= 40
        score -= low_diversity_count * 5

        return max(0, min(100, score))
