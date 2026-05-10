"""Base confidence calculator interface."""

from abc import ABC, abstractmethod
from typing import List


class ConfidenceCalculator(ABC):
    """Abstract base for confidence calculation strategies."""

    @abstractmethod
    def calculate(
        self,
        constraint_scores: List[float],
        bottleneck_count: int,
        total_faculty: int,
        lab_feasible: bool,
        low_diversity_count: int
    ) -> int:
        """
        Calculate confidence score 0-100.

        Args:
            constraint_scores: List of required/available ratios
            bottleneck_count: Number of slots with >=3 competitors
            total_faculty: Total faculty count
            lab_feasible: Whether lab constraints are satisfiable
            low_diversity_count: Faculty with <=3 unique slots

        Returns:
            Confidence score from 0 to 100
        """
        pass
