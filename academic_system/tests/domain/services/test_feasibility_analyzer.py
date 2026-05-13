# tests/domain/services/test_feasibility_analyzer.py
import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from app.domain.entities.feasibility import (
    FeasibilityReport, FeasibilityStatus, Recoverability,
    ConstraintScore, ConstraintSeverity, WarningCollection,
    LocalWarning, GlobalWarning, RiskLevel, Suggestion,
    SuggestionType, SuggestionPriority, FeasibilityTelemetry
)
from app.domain.entities.subject import Subject, SubjectType
from app.domain.services.feasibility_analyzer import FeasibilityAnalyzer


@pytest.mark.asyncio
async def test_analyze_perfect_case():
    """All constraints comfortable, no issues."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=3,
                 classes_per_week=3)
    ]

    faculty_availability = {
        "f1": {"MON": [1, 2, 3, 4, 7, 8], "TUE": [1, 2, 3, 4, 7, 8]}
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert report.status == FeasibilityStatus.PASS
    assert report.confidence_score == 100
    assert report.recoverability == Recoverability.RECOVERABLE
    assert len(report.errors) == 0


@pytest.mark.asyncio
async def test_analyze_critical_constraint():
    """Faculty has fewer slots than required."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=4,
                 classes_per_week=4)
    ]

    # Only 3 unique slots available, need 4
    faculty_availability = {
        "f1": {"MON": [1, 2, 3]}  # 3 < 4 required
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert report.status == FeasibilityStatus.FAIL
    assert report.recoverability == Recoverability.NEAR_IMPOSSIBLE
    assert len(report.errors) > 0
    assert any("4" in err for err in report.errors)


@pytest.mark.asyncio
async def test_exact_slot_count_is_warning_not_failure():
    """Exactly enough slots is tight, but should not block generation by itself."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=3,
                 classes_per_week=3)
    ]

    faculty_availability = {
        "f1": {"MON": [1, 2, 3]}
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map,
        faculty_names={"f1": "Dr. Exact Fit"}
    )

    assert report.status == FeasibilityStatus.WARNING
    assert report.errors == []
    assert report.constraint_scores["s1"].severity == ConstraintSeverity.TIGHT
    assert report.constraint_scores["s1"].faculty_name == "Dr. Exact Fit"
    assert any("Dr. Exact Fit" in warning.message for warning in report.warnings.local)


@pytest.mark.asyncio
async def test_detect_bottleneck():
    """Multiple faculty competing for same slot."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3),
        Subject(id="s2", code="PHY101", name="Physics", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3),
        Subject(id="s3", code="CS101", name="CS", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3)
    ]

    # All faculty want slot 1 on MONDAY, but have enough other slots
    # to avoid critical constraints
    faculty_availability = {
        "f1": {"MON": [1, 2, 3, 4, 7, 8]},  # 6 slots for 3 classes - comfortable
        "f2": {"MON": [1, 2, 4, 5, 7, 8]},  # 6 slots for 3 classes - comfortable
        "f3": {"MON": [1, 3, 6, 7, 8]}      # 5 slots for 3 classes - moderate
    }
    subject_faculty_map = {"s1": "f1", "s2": "f2", "s3": "f3"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert report.status == FeasibilityStatus.WARNING
    assert len(report.warnings.global_warnings) > 0
    # Should detect slot 1 as bottleneck
    slot_1_warnings = [w for w in report.warnings.global_warnings if w.slot_number == 1]
    assert len(slot_1_warnings) > 0


@pytest.mark.asyncio
async def test_bottleneck_warning_includes_faculty_names():
    """Global warnings should include readable faculty labels for the UI."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3),
        Subject(id="s2", code="PHY101", name="Physics", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3),
        Subject(id="s3", code="CS101", name="CS", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3)
    ]
    faculty_availability = {
        "f1": {"MON": [1, 2, 3, 4, 7, 8]},
        "f2": {"MON": [1, 2, 4, 5, 7, 8]},
        "f3": {"MON": [1, 3, 6, 7, 8]}
    }
    subject_faculty_map = {"s1": "f1", "s2": "f2", "s3": "f3"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map,
        faculty_names={"f1": "Dr. A", "f2": "Dr. B", "f3": "Dr. C"}
    )

    warning = next(w for w in report.warnings.global_warnings if w.slot_number == 1)
    assert warning.competing_faculty_names == ["Dr. A", "Dr. B", "Dr. C"]
    assert "Dr. A" in warning.message


@pytest.mark.asyncio
async def test_calculate_constraint_scores_with_day_slot_pairs():
    """Count unique (day, slot) pairs, not just slot numbers."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=4, classes_per_week=4)
    ]

    # Faculty has 6 unique opportunities: MON-1, MON-2, TUE-1, TUE-2, WED-1, WED-2
    # Even though slot numbers repeat, day+slot combinations are unique
    faculty_availability = {
        "f1": {
            "MON": [1, 2],  # 2 opportunities
            "TUE": [1, 2],  # 2 opportunities (different day)
            "WED": [1, 2]   # 2 opportunities (different day)
        }
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    # Score = 4 required / 6 available = 0.667 (MODERATE)
    score = report.constraint_scores["s1"]
    assert score.unique_available_slots == 6
    assert round(score.score, 2) == 0.67
    assert score.severity == ConstraintSeverity.MODERATE


@pytest.mark.asyncio
async def test_generate_suggestions_for_tight_constraint():
    """Should suggest adding slots when constraint is tight."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=4, classes_per_week=4)
    ]

    # Exactly 4 slots - tight, no room for error
    faculty_availability = {
        "f1": {"MON": [1, 2, 3, 4]}
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert len(report.suggestions) > 0
    # Should suggest diversifying or adding slots
    suggestion_types = [s.suggestion_type for s in report.suggestions]
    assert SuggestionType.ADD_SLOTS in suggestion_types or \
           SuggestionType.DIVERSIFY_SLOTS in suggestion_types
