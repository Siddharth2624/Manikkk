"""
Feasibility Analyzer - Core service for pre-generation feasibility analysis.

This service analyzes the feasibility of timetable generation before
attempting the actual generation process.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime

from app.domain.entities.feasibility import (
    FeasibilityReport,
    FeasibilityStatus,
    Recoverability,
    ConstraintScore,
    ConstraintSeverity,
    WarningCollection,
    LocalWarning,
    GlobalWarning,
    RiskLevel,
    Suggestion,
    SuggestionType,
    SuggestionPriority,
    FeasibilityTelemetry,
)
from app.domain.entities.subject import Subject, SubjectType
from app.domain.services.confidence import ConfidenceCalculator, DefaultConfidenceCalculator


# Constants
LUNCH_SLOTS = {5, 6}  # Lunch break slots
BOTTLENECK_THRESHOLD = 3  # Number of competing faculty to consider a slot a bottleneck
LOW_DIVERSITY_THRESHOLD = 3  # Number of unique slots to consider low diversity


class FeasibilityAnalyzer:
    """
    Core service for analyzing timetable generation feasibility.

    This service performs comprehensive analysis including:
    - Constraint score calculation (using unique day-slot pairs)
    - FAIL condition detection (critical constraints, no faculty, no consecutive lab pairs)
    - Bottleneck detection (slots with >=3 competing faculty)
    - Lab feasibility analysis (consecutive usable slot pairs)
    - Diversity checking (faculty with <=3 unique slots)
    - Local/Global warning generation
    - Confidence score calculation
    - Recoverability classification
    - Suggestion generation
    - Telemetry snapshot creation
    """

    def __init__(self, confidence_calculator: Optional[ConfidenceCalculator] = None):
        """
        Initialize the analyzer.

        Args:
            confidence_calculator: Optional custom calculator. Defaults to DefaultConfidenceCalculator.
        """
        self.confidence_calculator = confidence_calculator or DefaultConfidenceCalculator()

    async def analyze(
        self,
        semester: int,
        section: str,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str],
    ) -> FeasibilityReport:
        """
        Perform comprehensive feasibility analysis.

        Args:
            semester: Semester number
            section: Section identifier
            subjects: List of subjects to analyze
            faculty_availability: Faculty ID -> {Day -> [slots]}
            subject_faculty_map: Subject ID -> Faculty ID

        Returns:
            FeasibilityReport with complete analysis results
        """
        errors: List[str] = []
        local_warnings: List[LocalWarning] = []
        global_warnings: List[GlobalWarning] = []
        suggestions: List[Suggestion] = []

        # 1. Check for missing faculty assignments
        for subject in subjects:
            if subject.id not in subject_faculty_map:
                errors.append(f"Subject {subject.code} has no assigned faculty")

        # 2. Calculate constraint scores (using unique day-slot pairs)
        constraint_scores = self._calculate_constraint_scores(
            subjects, faculty_availability, subject_faculty_map
        )

        # 3. Detect FAIL conditions
        fail_errors = self._detect_fail_conditions(
            subjects, constraint_scores, faculty_availability, subject_faculty_map
        )
        errors.extend(fail_errors)

        # 4. Detect bottlenecks (slots with >=3 competing faculty)
        bottlenecks = self._detect_bottlenecks(faculty_availability, subject_faculty_map)
        global_warnings.extend(bottlenecks)

        # 5. Analyze lab feasibility (consecutive usable slot pairs)
        lab_feasible, lab_errors = self._analyze_lab_feasibility(
            subjects, faculty_availability, subject_faculty_map
        )
        errors.extend(lab_errors)

        # 6. Check diversity (faculty with <=3 unique slots)
        low_diversity_faculty = self._check_low_diversity(faculty_availability)

        # 7. Generate local warnings for tight/critical constraints
        local_warnings.extend(
            self._generate_local_warnings(constraint_scores, subjects, subject_faculty_map)
        )

        # 8. Calculate confidence score using injected calculator
        constraint_score_values = [cs.score for cs in constraint_scores.values()]
        bottleneck_count = len(bottlenecks)
        low_diversity_count = len(low_diversity_faculty)

        confidence_score = self.confidence_calculator.calculate(
            constraint_scores=constraint_score_values,
            bottleneck_count=bottleneck_count,
            total_faculty=len(faculty_availability),
            lab_feasible=lab_feasible,
            low_diversity_count=low_diversity_count,
        )

        # 9. Classify recoverability
        critical_count = sum(1 for cs in constraint_scores.values() if cs.severity == ConstraintSeverity.CRITICAL)
        recoverability = self._classify_recoverability(
            confidence_score, critical_count, bottleneck_count
        )

        # 10. Generate suggestions
        suggestions = self._generate_suggestions(
            constraint_scores, bottlenecks, lab_feasible, low_diversity_faculty, subject_faculty_map
        )

        # 11. Determine overall status
        status = self._determine_status(errors, local_warnings, global_warnings)

        # 12. Build telemetry snapshot
        telemetry = self._build_telemetry(
            semester=semester,
            section=section,
            total_faculty=len(faculty_availability),
            total_subjects=len(subjects),
            total_theory=sum(1 for s in subjects if s.is_theory()),
            total_labs=sum(1 for s in subjects if s.is_lab()),
            bottleneck_slots=[w.slot_number for w in bottlenecks],
            tightly_constrained_faculty=[
                cs.faculty_id for cs in constraint_scores.values() if cs.is_tightly_constrained
            ],
            low_diversity_faculty=low_diversity_faculty,
            lab_feasible=lab_feasible,
        )

        return FeasibilityReport(
            status=status,
            confidence_score=confidence_score,
            recoverability=recoverability,
            errors=errors,
            warnings=WarningCollection(local=local_warnings, global_warnings=global_warnings),
            constraint_scores={cs.subject_id: cs for cs in constraint_scores.values()},
            suggestions=suggestions,
            telemetry_snapshot=telemetry,
        )

    def _calculate_constraint_scores(
        self,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str],
    ) -> Dict[str, ConstraintScore]:
        """
        Calculate constraint scores for all subject-faculty pairs.

        Uses unique (day, slot) pairs for counting available slots.
        """
        constraint_scores: Dict[str, ConstraintScore] = {}

        for subject in subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                continue

            avail = faculty_availability.get(faculty_id, {})

            # Count unique (day, slot) pairs
            unique_pairs: Set[Tuple[str, int]] = set()
            for day, slots in avail.items():
                for slot in slots:
                    unique_pairs.add((day, slot))

            unique_available = len(unique_pairs)

            # Count consecutive pairs (excluding lunch slots 5, 6)
            all_slots = sorted(slot for slots in avail.values() for slot in slots)
            consecutive_pairs = self._count_consecutive_pairs(all_slots)

            constraint_score = ConstraintScore(
                subject_id=subject.id,
                faculty_id=faculty_id,
                subject_name=subject.name,
                faculty_name=self._get_faculty_name(faculty_id),
                required_slots=subject.classes_per_week,
                unique_available_slots=unique_available,
                consecutive_pairs_available=consecutive_pairs,
            )

            constraint_scores[subject.id] = constraint_score

        return constraint_scores

    def _count_consecutive_pairs(self, slots: List[int]) -> int:
        """
        Count consecutive slot pairs, excluding lunch slots.

        Args:
            slots: Sorted list of slot numbers

        Returns:
            Number of consecutive pairs that don't span lunch
        """
        if len(slots) < 2:
            return 0

        count = 0
        sorted_slots = sorted(set(slots))

        for i in range(len(sorted_slots) - 1):
            current = sorted_slots[i]
            next_slot = sorted_slots[i + 1]

            # Check if consecutive and neither is a lunch slot
            if (
                next_slot - current == 1
                and current not in LUNCH_SLOTS
                and next_slot not in LUNCH_SLOTS
            ):
                count += 1

        return count

    def _detect_fail_conditions(
        self,
        subjects: List[Subject],
        constraint_scores: Dict[str, ConstraintScore],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str],
    ) -> List[str]:
        """
        Detect critical FAIL conditions.

        Returns:
            List of error messages for fail conditions
        """
        errors: List[str] = []

        # Check for critical constraints (score >= 1.0)
        for subject_id, score in constraint_scores.items():
            if score.severity == ConstraintSeverity.CRITICAL:
                subject = next((s for s in subjects if s.id == subject_id), None)
                subject_code = subject.code if subject else subject_id
                errors.append(
                    f"Subject {subject_code} requires {score.required_slots} slots "
                    f"but faculty only has {score.unique_available_slots} unique slots available"
                )

        # Check for subjects with no faculty assigned
        for subject in subjects:
            if subject.id not in subject_faculty_map:
                errors.append(f"Subject {subject.code} has no faculty assigned")

        return errors

    def _detect_bottlenecks(
        self,
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str],
    ) -> List[GlobalWarning]:
        """
        Detect bottleneck slots (slots with >=3 competing faculty).

        Returns:
            List of GlobalWarning for bottleneck slots
        """
        warnings: List[GlobalWarning] = []

        # Count competition for each (day, slot) pair
        slot_competition: Dict[Tuple[str, int], Set[str]] = defaultdict(set)
        faculty_names: Dict[str, str] = {}

        for faculty_id, avail in faculty_availability.items():
            faculty_names[faculty_id] = self._get_faculty_name(faculty_id)
            for day, slots in avail.items():
                for slot in slots:
                    slot_competition[(day, slot)].add(faculty_id)

        # Find bottlenecks (>=3 competing faculty)
        for (day, slot), competing_faculty_set in slot_competition.items():
            if len(competing_faculty_set) >= BOTTLENECK_THRESHOLD:
                # Get subject codes for competing faculty
                subject_codes = [
                    subj_id
                    for subj_id, fac_id in subject_faculty_map.items()
                    if fac_id in competing_faculty_set
                ]

                competing_faculty_list = list(competing_faculty_set)

                warnings.append(
                    GlobalWarning(
                        slot_number=slot,
                        time_range=self._get_time_range(slot),
                        competing_subjects=subject_codes,
                        competing_faculty=competing_faculty_list,
                        supply_demand_ratio=1.0 / len(competing_faculty_set),
                        risk_level=RiskLevel.HIGH if len(competing_faculty_set) >= 4 else RiskLevel.MEDIUM,
                        message=f"Slot {slot} on {day} has {len(competing_faculty_set)} faculty competing",
                    )
                )

        return warnings

    def _analyze_lab_feasibility(
        self,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str],
    ) -> Tuple[bool, List[str]]:
        """
        Analyze lab feasibility (requires consecutive usable slot pairs).

        Returns:
            Tuple of (is_feasible, list of error messages)
        """
        errors: List[str] = []

        for subject in subjects:
            if not subject.is_lab():
                continue

            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                continue

            avail = faculty_availability.get(faculty_id, {})

            # Get all slots and count consecutive pairs (excluding lunch)
            all_slots = sorted(slot for slots in avail.values() for slot in slots)
            consecutive_pairs = self._count_consecutive_pairs(all_slots)

            # Labs need at least one consecutive pair
            if consecutive_pairs == 0:
                subject_code = subject.code
                errors.append(
                    f"Lab {subject_code} has no consecutive slot pairs available "
                    f"(excluding lunch slots {LUNCH_SLOTS})"
                )

        return len(errors) == 0, errors

    def _check_low_diversity(
        self, faculty_availability: Dict[str, Dict[str, List[int]]]
    ) -> List[str]:
        """
        Check for faculty with low diversity (<=3 unique slots).

        Returns:
            List of faculty IDs with low diversity
        """
        low_diversity: List[str] = []

        for faculty_id, avail in faculty_availability.items():
            unique_slots = set()
            for slots in avail.values():
                unique_slots.update(slots)

            if len(unique_slots) <= LOW_DIVERSITY_THRESHOLD:
                low_diversity.append(faculty_id)

        return low_diversity

    def _generate_local_warnings(
        self,
        constraint_scores: Dict[str, ConstraintScore],
        subjects: List[Subject],
        subject_faculty_map: Dict[str, str],
    ) -> List[LocalWarning]:
        """
        Generate local warnings for tight/critical constraints.

        Returns:
            List of LocalWarning entities
        """
        warnings: List[LocalWarning] = []

        for subject_id, score in constraint_scores.items():
            if score.severity in (ConstraintSeverity.TIGHT, ConstraintSeverity.CRITICAL):
                subject = next((s for s in subjects if s.id == subject_id), None)
                if not subject:
                    continue

                risk_level = RiskLevel.CRITICAL if score.severity == ConstraintSeverity.CRITICAL else RiskLevel.HIGH

                warnings.append(
                    LocalWarning(
                        faculty_id=score.faculty_id,
                        faculty_name=score.faculty_name,
                        subject_id=subject_id,
                        subject_name=subject.name,
                        risk_level=risk_level,
                        constraint_score=score.score,
                        severity=score.severity,
                        message=(
                            f"{subject.code} is {score.severity.value.lower()}: "
                            f"requires {score.required_slots} slots, has {score.unique_available_slots}"
                        ),
                        suggestion="Consider adding more available slots or diversifying across days",
                    )
                )

        return warnings

    def _classify_recoverability(
        self, confidence: int, critical_count: int, bottleneck_count: int
    ) -> Recoverability:
        """
        Classify recoverability based on analysis results.

        Rules:
        - NEAR_IMPOSSIBLE: critical constraints, confidence < 30, or >=3 bottlenecks
        - DIFFICULT: confidence < 70 or any bottlenecks
        - RECOVERABLE: otherwise
        """
        if critical_count > 0 or confidence < 30 or bottleneck_count >= 3:
            return Recoverability.NEAR_IMPOSSIBLE
        elif confidence < 70 or bottleneck_count > 0:
            return Recoverability.DIFFICULT
        else:
            return Recoverability.RECOVERABLE

    def _generate_suggestions(
        self,
        constraint_scores: Dict[str, ConstraintScore],
        bottlenecks: List[GlobalWarning],
        lab_feasible: bool,
        low_diversity_faculty: List[str],
        subject_faculty_map: Dict[str, str],
    ) -> List[Suggestion]:
        """
        Generate suggestions for improving feasibility.

        Returns:
            List of Suggestion entities
        """
        suggestions: List[Suggestion] = []

        # Suggestions for tight/critical constraints
        for subject_id, score in constraint_scores.items():
            if score.is_tightly_constrained:
                if score.unique_available_slots < 5:
                    suggestions.append(
                        Suggestion(
                            target_faculty_id=score.faculty_id,
                            target_subject_id=subject_id,
                            suggestion_type=SuggestionType.ADD_SLOTS,
                            message=f"Add more available slots for {score.subject_name}",
                            priority=SuggestionPriority.HIGH if score.severity == ConstraintSeverity.CRITICAL else SuggestionPriority.MEDIUM,
                            expected_impact="Increases flexibility for scheduling",
                        )
                    )

                # Check if slots are concentrated on few days
                suggestions.append(
                    Suggestion(
                        target_faculty_id=score.faculty_id,
                        target_subject_id=subject_id,
                        suggestion_type=SuggestionType.DIVERSIFY_SLOTS,
                        message=f"Diversify {score.faculty_name}'s availability across more days",
                        priority=SuggestionPriority.MEDIUM,
                        expected_impact="Reduces day-slot conflicts",
                    )
                )

        # Suggestions for bottlenecks
        for bottleneck in bottlenecks:
            for faculty_id in bottleneck.competing_faculty:
                # Find a subject taught by this faculty
                subject_id = next(
                    (sid for sid, fid in subject_faculty_map.items() if fid == faculty_id),
                    "unknown",
                )

                suggestions.append(
                    Suggestion(
                        target_faculty_id=faculty_id,
                        target_subject_id=subject_id,
                        suggestion_type=SuggestionType.ADD_AFTERNOON,
                        message=f"Consider afternoon availability for {self._get_faculty_name(faculty_id)}",
                        priority=SuggestionPriority.LOW,
                        expected_impact="Reduces competition for peak morning slots",
                    )
                )

        # Suggestions for lab feasibility
        if not lab_feasible:
            for subject_id, score in constraint_scores.items():
                if score.consecutive_pairs_available == 0:
                    suggestions.append(
                        Suggestion(
                            target_faculty_id=score.faculty_id,
                            target_subject_id=subject_id,
                            suggestion_type=SuggestionType.ADD_CONSECUTIVE,
                            message=f"Add consecutive slot pairs for {score.subject_name}",
                            priority=SuggestionPriority.HIGH,
                            expected_impact="Enables lab scheduling which requires consecutive slots",
                        )
                    )

                    suggestions.append(
                        Suggestion(
                            target_faculty_id=score.faculty_id,
                            target_subject_id=subject_id,
                            suggestion_type=SuggestionType.AVOID_LUNCH,
                            message=f"Avoid lunch break slots {LUNCH_SLOTS} for {score.faculty_name}",
                            priority=SuggestionPriority.MEDIUM,
                            expected_impact="Increases consecutive pair availability",
                        )
                    )

        # Suggestions for low diversity
        for faculty_id in low_diversity_faculty:
            subject_id = next(
                (sid for sid, fid in subject_faculty_map.items() if fid == faculty_id),
                "unknown",
            )
            suggestions.append(
                Suggestion(
                    target_faculty_id=faculty_id,
                    target_subject_id=subject_id,
                    suggestion_type=SuggestionType.DIVERSIFY_SLOTS,
                    message=f"Expand {self._get_faculty_name(faculty_id)}'s slot diversity",
                    priority=SuggestionPriority.MEDIUM,
                    expected_impact="Improves scheduling flexibility",
                )
            )

        return suggestions

    def _determine_status(
        self,
        errors: List[str],
        local_warnings: List[LocalWarning],
        global_warnings: List[GlobalWarning],
    ) -> FeasibilityStatus:
        """
        Determine overall feasibility status.

        Rules:
        - FAIL: Any critical errors
        - WARNING: No errors but has warnings
        - PASS: No errors and no warnings
        """
        if errors:
            return FeasibilityStatus.FAIL
        if local_warnings or global_warnings:
            return FeasibilityStatus.WARNING
        return FeasibilityStatus.PASS

    def _build_telemetry(
        self,
        semester: int,
        section: str,
        total_faculty: int,
        total_subjects: int,
        total_theory: int,
        total_labs: int,
        bottleneck_slots: List[int],
        tightly_constrained_faculty: List[str],
        low_diversity_faculty: List[str],
        lab_feasible: bool,
    ) -> FeasibilityTelemetry:
        """
        Build telemetry snapshot for the analysis.

        Returns:
            FeasibilityTelemetry entity
        """
        return FeasibilityTelemetry(
            analysis_timestamp=datetime.utcnow(),
            semester=semester,
            section=section,
            total_faculty=total_faculty,
            total_subjects=total_subjects,
            total_theory=total_theory,
            total_labs=total_labs,
            bottleneck_slots=bottleneck_slots,
            tightly_constrained_faculty=tightly_constrained_faculty,
            low_diversity_faculty=low_diversity_faculty,
            lab_feasible=lab_feasible,
            estimated_generation_time_ms=self._estimate_generation_time(
                total_subjects, total_faculty, len(bottleneck_slots)
            ),
        )

    def _estimate_generation_time(
        self, total_subjects: int, total_faculty: int, bottleneck_count: int
    ) -> int:
        """
        Estimate generation time in milliseconds.

        Simple heuristic based on complexity factors.
        """
        base_time = 500  # ms
        per_subject_time = 50
        per_faculty_factor = 10
        bottleneck_penalty = 200

        estimated = (
            base_time
            + (total_subjects * per_subject_time)
            + (total_faculty * per_faculty_factor)
            + (bottleneck_count * bottleneck_penalty)
        )

        return estimated

    # -------------------------------------------------------------------------
    # Helper methods (placeholder implementations for names/time ranges)
    # -------------------------------------------------------------------------

    def _get_faculty_name(self, faculty_id: str) -> str:
        """
        Get faculty name from ID (placeholder).

        In production, this would query a user repository.
        """
        return f"Faculty_{faculty_id}"

    def _get_time_range(self, slot_number: int) -> str:
        """
        Get time range for a slot number (placeholder).

        In production, this would use actual time slot configuration.
        """
        # Assuming 1-hour slots starting at 8 AM
        start_hour = 7 + slot_number
        return f"{start_hour:02d}:00-{start_hour + 1:02d}:00"
