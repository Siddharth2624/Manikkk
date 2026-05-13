"""
Feasibility analysis domain entities.

This module contains all dataclasses and enums for pre-generation
feasibility analysis of timetable generation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# Enums
# =============================================================================


class FeasibilityStatus(str, Enum):
    """Overall feasibility status for timetable generation."""
    PASS = "PASS"          # Expected to generate successfully
    WARNING = "WARNING"    # Possible but may require multiple attempts
    FAIL = "FAIL"          # Highly unlikely to succeed without changes


class Recoverability(str, Enum):
    """Ease of recovering from a failed generation."""
    RECOVERABLE = "RECOVERABLE"           # Small adjustments likely sufficient
    DIFFICULT = "DIFFICULT"               # May require significant changes
    NEAR_IMPOSSIBLE = "NEAR_IMPOSSIBLE"   # Major constraints overhaul needed


class ConstraintSeverity(str, Enum):
    """
    Severity level of a constraint based on the score (required/available ratio).

    - COMFORTABLE: score < 0.5 (plenty of available slots)
    - MODERATE: 0.5 <= score < 0.8 (some constraints, workable)
    - TIGHT: 0.8 <= score <= 1.0 (very constrained, needs careful planning)
    - CRITICAL: score > 1.0 (not enough slots, impossible as-is)
    """
    COMFORTABLE = "COMFORTABLE"
    MODERATE = "MODERATE"
    TIGHT = "TIGHT"
    CRITICAL = "CRITICAL"


class RiskLevel(str, Enum):
    """Risk level for warnings."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SuggestionType(str, Enum):
    """Type of suggestion for improving feasibility."""
    ADD_SLOTS = "ADD_SLOTS"                   # Add more available slots
    DIVERSIFY_SLOTS = "DIVERSIFY_SLOTS"       # Spread slots across days/times
    ADD_AFTERNOON = "ADD_AFTERNOON"           # Add afternoon availability
    ADD_CONSECUTIVE = "ADD_CONSECUTIVE"       # Add consecutive slot pairs
    AVOID_LUNCH = "AVOID_LUNCH"               # Avoid lunch break slots


class SuggestionPriority(str, Enum):
    """Priority level for a suggestion."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =============================================================================
# Constraint Score
# =============================================================================


@dataclass
class ConstraintScore:
    """
    Score representing how tightly constrained a faculty-subject assignment is.

    The score is calculated as: required_slots / unique_available_slots

    unique_available_slots counts unique (day, slot) pairs, NOT just slot numbers.
    For example, if a faculty is available at slot 1 on Monday, Tuesday, and Wednesday,
    that's 3 unique slots, not 1.
    """
    subject_id: str
    faculty_id: str
    subject_name: str
    faculty_name: str
    required_slots: int
    unique_available_slots: int
    score: float = field(init=False)
    severity: ConstraintSeverity = field(init=False)
    consecutive_pairs_available: int = 0

    def __post_init__(self):
        """Calculate score and determine severity."""
        if self.unique_available_slots <= 0:
            self.score = float('inf')
        else:
            self.score = self.required_slots / self.unique_available_slots
        self.severity = self.get_severity(self.score)

    @property
    def is_tightly_constrained(self) -> bool:
        """Return True if this constraint is TIGHT or CRITICAL."""
        return self.severity in (ConstraintSeverity.TIGHT, ConstraintSeverity.CRITICAL)

    @classmethod
    def get_severity(cls, score: float) -> ConstraintSeverity:
        """
        Determine severity from constraint score.

        Args:
            score: The constraint score (required / available ratio)

        Returns:
            ConstraintSeverity based on threshold values
        """
        if score < 0.5:
            return ConstraintSeverity.COMFORTABLE
        elif score < 0.8:
            return ConstraintSeverity.MODERATE
        elif score <= 1.0:
            return ConstraintSeverity.TIGHT
        else:
            return ConstraintSeverity.CRITICAL


# =============================================================================
# Warnings
# =============================================================================


@dataclass
class LocalWarning:
    """
    Warning about a specific faculty-subject constraint.

    These are "local" because they pertain to a specific assignment
    rather than global slot competition.
    """
    faculty_id: str
    faculty_name: str
    subject_id: str
    subject_name: str
    risk_level: RiskLevel
    constraint_score: float
    severity: ConstraintSeverity
    message: str
    suggestion: str


@dataclass
class GlobalWarning:
    """
    Warning about global slot competition across all assignments.

    These warnings highlight time slots where many subjects/faculty
    are competing for limited availability.
    """
    slot_number: int
    time_range: str
    competing_subjects: List[str]
    competing_faculty: List[str]
    supply_demand_ratio: float
    risk_level: RiskLevel
    message: str
    competing_subject_names: List[str] = field(default_factory=list)
    competing_faculty_names: List[str] = field(default_factory=list)


@dataclass
class WarningCollection:
    """
    Collection of all local and global warnings.

    Note: `global_warnings` is used instead of `global` to avoid
    shadowing Python's built-in keyword.
    """
    local: List[LocalWarning] = field(default_factory=list)
    global_warnings: List[GlobalWarning] = field(default_factory=list)

    @property
    def has_local(self) -> bool:
        """Return True if there are local warnings."""
        return len(self.local) > 0

    @property
    def has_global(self) -> bool:
        """Return True if there are global warnings."""
        return len(self.global_warnings) > 0

    def all_messages(self) -> List[str]:
        """Return all warning messages from both local and global warnings."""
        messages = []
        messages.extend(w.message for w in self.local)
        messages.extend(w.message for w in self.global_warnings)
        return messages


# =============================================================================
# Suggestions
# =============================================================================


@dataclass
class Suggestion:
    """
    Suggestion for improving feasibility.

    The message should be guiding, not dictating - it provides
    context for human decision-makers.
    """
    target_faculty_id: str
    target_subject_id: str
    suggestion_type: SuggestionType
    message: str
    priority: SuggestionPriority
    expected_impact: str


# =============================================================================
# Telemetry
# =============================================================================


@dataclass
class FeasibilityTelemetry:
    """
    Snapshot of feasibility analysis metadata.

    Captured during feasibility analysis to provide context
    for the feasibility report and generation process.
    """
    analysis_timestamp: datetime
    semester: int
    section: str
    total_faculty: int
    total_subjects: int
    total_theory: int
    total_labs: int
    bottleneck_slots: List[int]
    tightly_constrained_faculty: List[str]
    low_diversity_faculty: List[str]
    lab_feasible: bool
    estimated_generation_time_ms: int


@dataclass
class GenerationTelemetry:
    """
    Metadata captured during/after timetable generation.

    Links back to the feasibility analysis via feasibility_confidence
    and provides actual generation metrics.
    """
    generation_timestamp: datetime
    semester: int
    section: str
    feasibility_confidence: int  # Links to FeasibilityReport.confidence_score
    generation_seed: str
    actual_attempts_used: int
    success: bool
    duration_ms: int
    bottleneck_subjects: List[str]
    total_backtracks: int
    backtrack_by_reason: Dict[str, int]
    conflict_hotspots: List[Dict[str, Any]]


# =============================================================================
# Main Report
# =============================================================================


@dataclass
class FeasibilityReport:
    """
    Complete feasibility analysis report.

    This is the main output of the feasibility analysis process,
    containing all information needed to assess whether timetable
    generation is likely to succeed.
    """
    status: FeasibilityStatus
    confidence_score: int  # Estimated feasibility score (0-100), not calibrated probability
    recoverability: Recoverability
    errors: List[str]
    warnings: WarningCollection
    constraint_scores: Dict[str, ConstraintScore]  # Key: "{faculty_id}_{subject_id}"
    suggestions: List[Suggestion]
    telemetry_snapshot: Optional[FeasibilityTelemetry] = None
