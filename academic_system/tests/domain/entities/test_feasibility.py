"""Tests for feasibility analysis domain entities."""

import pytest
from datetime import datetime
from app.domain.entities.feasibility import (
    FeasibilityStatus,
    Recoverability,
    ConstraintSeverity,
    RiskLevel,
    SuggestionType,
    SuggestionPriority,
    ConstraintScore,
    LocalWarning,
    GlobalWarning,
    WarningCollection,
    Suggestion,
    FeasibilityTelemetry,
    GenerationTelemetry,
    FeasibilityReport,
)


class TestFeasibilityStatusEnum:
    """Tests for FeasibilityStatus enum."""

    def test_feasibility_status_enum_values(self):
        """Test FeasibilityStatus enum has correct values."""
        assert FeasibilityStatus.PASS.value == "PASS"
        assert FeasibilityStatus.WARNING.value == "WARNING"
        assert FeasibilityStatus.FAIL.value == "FAIL"

    def test_feasibility_status_enum_is_string(self):
        """Test FeasibilityStatus inherits from str."""
        assert isinstance(FeasibilityStatus.PASS, str)


class TestRecoverabilityEnum:
    """Tests for Recoverability enum."""

    def test_recoverability_enum_values(self):
        """Test Recoverability enum has correct values."""
        assert Recoverability.RECOVERABLE.value == "RECOVERABLE"
        assert Recoverability.DIFFICULT.value == "DIFFICULT"
        assert Recoverability.NEAR_IMPOSSIBLE.value == "NEAR_IMPOSSIBLE"


class TestConstraintSeverityEnum:
    """Tests for ConstraintSeverity enum."""

    def test_constraint_severity_enum_values(self):
        """Test ConstraintSeverity enum has correct values."""
        assert ConstraintSeverity.COMFORTABLE.value == "COMFORTABLE"
        assert ConstraintSeverity.MODERATE.value == "MODERATE"
        assert ConstraintSeverity.TIGHT.value == "TIGHT"
        assert ConstraintSeverity.CRITICAL.value == "CRITICAL"


class TestRiskLevelEnum:
    """Tests for RiskLevel enum."""

    def test_risk_level_enum_values(self):
        """Test RiskLevel enum has correct values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


class TestSuggestionTypeEnum:
    """Tests for SuggestionType enum."""

    def test_suggestion_type_enum_values(self):
        """Test SuggestionType enum has correct values."""
        assert SuggestionType.ADD_SLOTS.value == "ADD_SLOTS"
        assert SuggestionType.DIVERSIFY_SLOTS.value == "DIVERSIFY_SLOTS"
        assert SuggestionType.ADD_AFTERNOON.value == "ADD_AFTERNOON"
        assert SuggestionType.ADD_CONSECUTIVE.value == "ADD_CONSECUTIVE"
        assert SuggestionType.AVOID_LUNCH.value == "AVOID_LUNCH"


class TestSuggestionPriorityEnum:
    """Tests for SuggestionPriority enum."""

    def test_suggestion_priority_enum_values(self):
        """Test SuggestionPriority enum has correct values."""
        assert SuggestionPriority.LOW.value == "LOW"
        assert SuggestionPriority.MEDIUM.value == "MEDIUM"
        assert SuggestionPriority.HIGH.value == "HIGH"


class TestConstraintScore:
    """Tests for ConstraintScore dataclass."""

    def test_constraint_score_creation(self):
        """Test ConstraintScore can be created with required fields."""
        score = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Mathematics",
            faculty_name="Dr. Smith",
            required_slots=5,
            unique_available_slots=10,
        )
        assert score.subject_id == "SUB001"
        assert score.faculty_id == "FAC001"
        assert score.subject_name == "Mathematics"
        assert score.faculty_name == "Dr. Smith"
        assert score.required_slots == 5
        assert score.unique_available_slots == 10
        assert score.score == 0.5
        assert score.severity == ConstraintSeverity.MODERATE

    def test_constraint_score_calculation(self):
        """Test score calculation equals required / unique_available_slots."""
        # Test with various values
        score1 = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=3,
            unique_available_slots=10,
        )
        assert score1.score == 0.3

        score2 = ConstraintScore(
            subject_id="SUB002",
            faculty_id="FAC002",
            subject_name="Physics",
            faculty_name="Dr. B",
            required_slots=10,
            unique_available_slots=5,
        )
        assert score2.score == 2.0

    def test_constraint_score_with_consecutive_pairs(self):
        """Test ConstraintScore with consecutive_pairs_available."""
        score = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=5,
            unique_available_slots=8,
            consecutive_pairs_available=3,
        )
        assert score.consecutive_pairs_available == 3

    def test_constraint_score_severity_comfortable(self):
        """Test severity is COMFORTABLE when score < 0.5."""
        score = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=2,
            unique_available_slots=10,
        )
        assert score.score == 0.2
        assert score.severity == ConstraintSeverity.COMFORTABLE

    def test_constraint_score_severity_moderate(self):
        """Test severity is MODERATE when score is 0.5-0.79."""
        # Lower bound
        score1 = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=5,
            unique_available_slots=10,
        )
        assert score1.score == 0.5
        assert score1.severity == ConstraintSeverity.MODERATE

        # Upper bound
        score2 = ConstraintScore(
            subject_id="SUB002",
            faculty_id="FAC002",
            subject_name="Physics",
            faculty_name="Dr. B",
            required_slots=79,
            unique_available_slots=100,
        )
        assert score2.score == 0.79
        assert score2.severity == ConstraintSeverity.MODERATE

    def test_constraint_score_severity_tight(self):
        """Test severity is TIGHT when score is 0.8-0.99."""
        # Lower bound
        score1 = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=8,
            unique_available_slots=10,
        )
        assert score1.score == 0.8
        assert score1.severity == ConstraintSeverity.TIGHT

        # Upper bound
        score2 = ConstraintScore(
            subject_id="SUB002",
            faculty_id="FAC002",
            subject_name="Physics",
            faculty_name="Dr. B",
            required_slots=99,
            unique_available_slots=100,
        )
        assert score2.score == 0.99
        assert score2.severity == ConstraintSeverity.TIGHT

    def test_constraint_score_severity_critical(self):
        """Test severity is CRITICAL only when required slots exceed availability."""
        # Exact 1.0 is tight, not critical: there are enough slots, but no buffer.
        score1 = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=10,
            unique_available_slots=10,
        )
        assert score1.score == 1.0
        assert score1.severity == ConstraintSeverity.TIGHT

        # Greater than 1.0
        score2 = ConstraintScore(
            subject_id="SUB002",
            faculty_id="FAC002",
            subject_name="Physics",
            faculty_name="Dr. B",
            required_slots=15,
            unique_available_slots=10,
        )
        assert score2.score == 1.5
        assert score2.severity == ConstraintSeverity.CRITICAL

    def test_constraint_score_get_severity_classmethod(self):
        """Test get_severity classmethod for all ranges."""
        assert ConstraintScore.get_severity(0.0) == ConstraintSeverity.COMFORTABLE
        assert ConstraintScore.get_severity(0.49) == ConstraintSeverity.COMFORTABLE
        assert ConstraintScore.get_severity(0.5) == ConstraintSeverity.MODERATE
        assert ConstraintScore.get_severity(0.79) == ConstraintSeverity.MODERATE
        assert ConstraintScore.get_severity(0.8) == ConstraintSeverity.TIGHT
        assert ConstraintScore.get_severity(0.99) == ConstraintSeverity.TIGHT
        assert ConstraintScore.get_severity(1.0) == ConstraintSeverity.TIGHT
        assert ConstraintScore.get_severity(2.0) == ConstraintSeverity.CRITICAL

    def test_constraint_score_is_tightly_constrained_property(self):
        """Test is_tightly_constrained returns True for TIGHT or CRITICAL."""
        # COMFORTABLE - should be False
        score1 = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=2,
            unique_available_slots=10,
        )
        assert score1.is_tightly_constrained is False

        # MODERATE - should be False
        score2 = ConstraintScore(
            subject_id="SUB002",
            faculty_id="FAC002",
            subject_name="Physics",
            faculty_name="Dr. B",
            required_slots=5,
            unique_available_slots=10,
        )
        assert score2.is_tightly_constrained is False

        # TIGHT - should be True
        score3 = ConstraintScore(
            subject_id="SUB003",
            faculty_id="FAC003",
            subject_name="Chemistry",
            faculty_name="Dr. C",
            required_slots=8,
            unique_available_slots=10,
        )
        assert score3.is_tightly_constrained is True

        # CRITICAL - should be True
        score4 = ConstraintScore(
            subject_id="SUB004",
            faculty_id="FAC004",
            subject_name="Biology",
            faculty_name="Dr. D",
            required_slots=12,
            unique_available_slots=10,
        )
        assert score4.is_tightly_constrained is True


class TestLocalWarning:
    """Tests for LocalWarning dataclass."""

    def test_local_warning_creation(self):
        """Test LocalWarning can be created with all fields."""
        warning = LocalWarning(
            faculty_id="FAC001",
            faculty_name="Dr. Smith",
            subject_id="SUB001",
            subject_name="Mathematics",
            risk_level=RiskLevel.HIGH,
            constraint_score=0.85,
            severity=ConstraintSeverity.TIGHT,
            message="Limited availability for this subject.",
            suggestion="Consider adding more afternoon slots.",
        )
        assert warning.faculty_id == "FAC001"
        assert warning.faculty_name == "Dr. Smith"
        assert warning.subject_id == "SUB001"
        assert warning.subject_name == "Mathematics"
        assert warning.risk_level == RiskLevel.HIGH
        assert warning.constraint_score == 0.85
        assert warning.severity == ConstraintSeverity.TIGHT
        assert warning.message == "Limited availability for this subject."
        assert warning.suggestion == "Consider adding more afternoon slots."


class TestGlobalWarning:
    """Tests for GlobalWarning dataclass."""

    def test_global_warning_creation(self):
        """Test GlobalWarning can be created with all fields."""
        warning = GlobalWarning(
            slot_number=1,
            time_range="09:00 - 09:55",
            competing_subjects=["Math", "Physics", "Chemistry"],
            competing_faculty=["Dr. A", "Dr. B", "Dr. C"],
            supply_demand_ratio=0.5,
            risk_level=RiskLevel.CRITICAL,
            message="High competition for first slot.",
        )
        assert warning.slot_number == 1
        assert warning.time_range == "09:00 - 09:55"
        assert warning.competing_subjects == ["Math", "Physics", "Chemistry"]
        assert warning.competing_faculty == ["Dr. A", "Dr. B", "Dr. C"]
        assert warning.supply_demand_ratio == 0.5
        assert warning.risk_level == RiskLevel.CRITICAL
        assert warning.message == "High competition for first slot."


class TestWarningCollection:
    """Tests for WarningCollection dataclass."""

    def test_warning_collection_creation(self):
        """Test WarningCollection can be created."""
        collection = WarningCollection(local=[], global_warnings=[])
        assert collection.local == []
        assert collection.global_warnings == []

    def test_warning_collection_with_warnings(self):
        """Test WarningCollection with actual warnings."""
        local_warning = LocalWarning(
            faculty_id="FAC001",
            faculty_name="Dr. A",
            subject_id="SUB001",
            subject_name="Math",
            risk_level=RiskLevel.HIGH,
            constraint_score=0.85,
            severity=ConstraintSeverity.TIGHT,
            message="Limited availability.",
            suggestion="Add more slots.",
        )
        global_warning = GlobalWarning(
            slot_number=1,
            time_range="09:00 - 09:55",
            competing_subjects=["Math"],
            competing_faculty=["Dr. A"],
            supply_demand_ratio=0.5,
            risk_level=RiskLevel.CRITICAL,
            message="High competition.",
        )
        collection = WarningCollection(local=[local_warning], global_warnings=[global_warning])
        assert len(collection.local) == 1
        assert len(collection.global_warnings) == 1

    def test_warning_collection_has_local_property(self):
        """Test has_local property."""
        collection_empty = WarningCollection(local=[], global_warnings=[])
        assert collection_empty.has_local is False

        collection_with_local = WarningCollection(
            local=[
                LocalWarning(
                    faculty_id="FAC001",
                    faculty_name="Dr. A",
                    subject_id="SUB001",
                    subject_name="Math",
                    risk_level=RiskLevel.HIGH,
                    constraint_score=0.85,
                    severity=ConstraintSeverity.TIGHT,
                    message="Limited availability.",
                    suggestion="Add more slots.",
                )
            ],
            global_warnings=[],
        )
        assert collection_with_local.has_local is True

    def test_warning_collection_has_global_property(self):
        """Test has_global property."""
        collection_empty = WarningCollection(local=[], global_warnings=[])
        assert collection_empty.has_global is False

        collection_with_global = WarningCollection(
            local=[],
            global_warnings=[
                GlobalWarning(
                    slot_number=1,
                    time_range="09:00 - 09:55",
                    competing_subjects=["Math"],
                    competing_faculty=["Dr. A"],
                    supply_demand_ratio=0.5,
                    risk_level=RiskLevel.CRITICAL,
                    message="High competition.",
                )
            ],
        )
        assert collection_with_global.has_global is True

    def test_warning_collection_all_messages(self):
        """Test all_messages method returns all warning messages."""
        local_warning = LocalWarning(
            faculty_id="FAC001",
            faculty_name="Dr. A",
            subject_id="SUB001",
            subject_name="Math",
            risk_level=RiskLevel.HIGH,
            constraint_score=0.85,
            severity=ConstraintSeverity.TIGHT,
            message="Local warning message.",
            suggestion="Add more slots.",
        )
        global_warning = GlobalWarning(
            slot_number=1,
            time_range="09:00 - 09:55",
            competing_subjects=["Math"],
            competing_faculty=["Dr. A"],
            supply_demand_ratio=0.5,
            risk_level=RiskLevel.CRITICAL,
            message="Global warning message.",
        )
        collection = WarningCollection(local=[local_warning], global_warnings=[global_warning])
        messages = collection.all_messages()
        assert len(messages) == 2
        assert "Local warning message." in messages
        assert "Global warning message." in messages


class TestSuggestion:
    """Tests for Suggestion dataclass."""

    def test_suggestion_creation(self):
        """Test Suggestion can be created with all fields."""
        suggestion = Suggestion(
            target_faculty_id="FAC001",
            target_subject_id="SUB001",
            suggestion_type=SuggestionType.ADD_SLOTS,
            message="Consider adding additional slots on Monday afternoon.",
            priority=SuggestionPriority.HIGH,
            expected_impact="Could reduce constraint score by 20%.",
        )
        assert suggestion.target_faculty_id == "FAC001"
        assert suggestion.target_subject_id == "SUB001"
        assert suggestion.suggestion_type == SuggestionType.ADD_SLOTS
        assert suggestion.message == "Consider adding additional slots on Monday afternoon."
        assert suggestion.priority == SuggestionPriority.HIGH
        assert suggestion.expected_impact == "Could reduce constraint score by 20%."


class TestFeasibilityTelemetry:
    """Tests for FeasibilityTelemetry dataclass."""

    def test_feasibility_telemetry_creation(self):
        """Test FeasibilityTelemetry can be created."""
        telemetry = FeasibilityTelemetry(
            analysis_timestamp=datetime(2026, 5, 10, 10, 30),
            semester=5,
            section="A",
            total_faculty=20,
            total_subjects=30,
            total_theory=25,
            total_labs=5,
            bottleneck_slots=[1, 2],
            tightly_constrained_faculty=["FAC001", "FAC002"],
            low_diversity_faculty=["FAC003"],
            lab_feasible=True,
            estimated_generation_time_ms=5000,
        )
        assert telemetry.analysis_timestamp == datetime(2026, 5, 10, 10, 30)
        assert telemetry.semester == 5
        assert telemetry.section == "A"
        assert telemetry.total_faculty == 20
        assert telemetry.total_subjects == 30
        assert telemetry.total_theory == 25
        assert telemetry.total_labs == 5
        assert telemetry.bottleneck_slots == [1, 2]
        assert telemetry.tightly_constrained_faculty == ["FAC001", "FAC002"]
        assert telemetry.low_diversity_faculty == ["FAC003"]
        assert telemetry.lab_feasible is True
        assert telemetry.estimated_generation_time_ms == 5000


class TestGenerationTelemetry:
    """Tests for GenerationTelemetry dataclass."""

    def test_generation_telemetry_creation(self):
        """Test GenerationTelemetry can be created."""
        telemetry = GenerationTelemetry(
            generation_timestamp=datetime(2026, 5, 10, 11, 0),
            semester=5,
            section="A",
            feasibility_confidence=85,
            generation_seed="random_seed_123",
            actual_attempts_used=3,
            success=True,
            duration_ms=2000,
            bottleneck_subjects=["SUB001", "SUB002"],
            total_backtracks=5,
            backtrack_by_reason={"slot_conflict": 3, "faculty_unavailable": 2},
            conflict_hotspots=[{"slot": 1, "day": "MON", "conflicts": 5}],
        )
        assert telemetry.generation_timestamp == datetime(2026, 5, 10, 11, 0)
        assert telemetry.semester == 5
        assert telemetry.section == "A"
        assert telemetry.feasibility_confidence == 85
        assert telemetry.generation_seed == "random_seed_123"
        assert telemetry.actual_attempts_used == 3
        assert telemetry.success is True
        assert telemetry.duration_ms == 2000
        assert telemetry.bottleneck_subjects == ["SUB001", "SUB002"]
        assert telemetry.total_backtracks == 5
        assert telemetry.backtrack_by_reason == {"slot_conflict": 3, "faculty_unavailable": 2}
        assert telemetry.conflict_hotspots == [{"slot": 1, "day": "MON", "conflicts": 5}]


class TestFeasibilityReport:
    """Tests for FeasibilityReport dataclass."""

    def test_feasibility_report_minimal(self):
        """Test FeasibilityReport can be created with minimal fields."""
        report = FeasibilityReport(
            status=FeasibilityStatus.PASS,
            confidence_score=95,
            recoverability=Recoverability.RECOVERABLE,
            errors=[],
            warnings=WarningCollection(local=[], global_warnings=[]),
            constraint_scores={},
            suggestions=[],
            telemetry_snapshot=None,
        )
        assert report.status == FeasibilityStatus.PASS
        assert report.confidence_score == 95
        assert report.recoverability == Recoverability.RECOVERABLE
        assert report.errors == []
        assert report.warnings.local == []
        assert report.warnings.global_warnings == []
        assert report.constraint_scores == {}
        assert report.suggestions == []
        assert report.telemetry_snapshot is None

    def test_feasibility_report_full(self):
        """Test FeasibilityReport can be created with all fields."""
        score = ConstraintScore(
            subject_id="SUB001",
            faculty_id="FAC001",
            subject_name="Math",
            faculty_name="Dr. A",
            required_slots=5,
            unique_available_slots=10,
        )
        warning = LocalWarning(
            faculty_id="FAC001",
            faculty_name="Dr. A",
            subject_id="SUB001",
            subject_name="Math",
            risk_level=RiskLevel.MEDIUM,
            constraint_score=0.5,
            severity=ConstraintSeverity.MODERATE,
            message="Moderate constraint.",
            suggestion="Consider diversifying.",
        )
        suggestion = Suggestion(
            target_faculty_id="FAC001",
            target_subject_id="SUB001",
            suggestion_type=SuggestionType.DIVERSIFY_SLOTS,
            message="Try adding afternoon slots.",
            priority=SuggestionPriority.MEDIUM,
            expected_impact="May improve diversity.",
        )
        telemetry = FeasibilityTelemetry(
            analysis_timestamp=datetime(2026, 5, 10, 10, 30),
            semester=5,
            section="A",
            total_faculty=20,
            total_subjects=30,
            total_theory=25,
            total_labs=5,
            bottleneck_slots=[],
            tightly_constrained_faculty=[],
            low_diversity_faculty=[],
            lab_feasible=True,
            estimated_generation_time_ms=5000,
        )
        report = FeasibilityReport(
            status=FeasibilityStatus.WARNING,
            confidence_score=75,
            recoverability=Recoverability.DIFFICULT,
            errors=[],
            warnings=WarningCollection(local=[warning], global_warnings=[]),
            constraint_scores={"FAC001_SUB001": score},
            suggestions=[suggestion],
            telemetry_snapshot=telemetry,
        )
        assert report.status == FeasibilityStatus.WARNING
        assert report.confidence_score == 75
        assert report.recoverability == Recoverability.DIFFICULT
        assert len(report.warnings.local) == 1
        assert len(report.constraint_scores) == 1
        assert len(report.suggestions) == 1
        assert report.telemetry_snapshot is not None
