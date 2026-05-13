# tests/use_cases/test_timetable_feasibility_integration.py
"""Tests for feasibility integration in TimetableUseCase."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.use_cases.timetable import TimetableUseCase
from app.domain.entities.feasibility import FeasibilityStatus, Recoverability, WarningCollection
from app.domain.exceptions import FeasibilityError
from app.domain.entities.subject import Subject, SubjectType
from app.domain.entities.timetable import DayOfWeek, DaySchedule, Timetable, TimetableSlot
from datetime import datetime


@pytest.mark.asyncio
async def test_generate_blocks_on_feasibility_fail():
    """Should raise FeasibilityError when feasibility fails."""
    use_case = _create_use_case()

    # Mock detect_assignments_for_timetable to return data
    with patch.object(use_case, 'detect_assignments_for_timetable') as mock_detect:
        mock_detect.return_value = {
            "subject_ids": ["sub1"],
            "faculty_availability": {"fac1": {"MON": [1, 2]}},
            "subject_faculty_map": {"sub1": "fac1"}
        }

        # Mock subject_repository.find_by_id to return a subject
        mock_subject = MagicMock(spec=Subject)
        mock_subject.id = "sub1"
        mock_subject.code = "CS101"
        mock_subject.name = "Intro to CS"
        mock_subject.classes_per_week = 3
        mock_subject.subject_type = SubjectType.THEORY

        use_case.subject_repository.find_by_id = AsyncMock(return_value=mock_subject)

        # Mock feasibility analyzer to return FAIL
        with patch.object(use_case.feasibility_analyzer, 'analyze') as mock_analyze:
            from app.domain.entities.feasibility import FeasibilityReport

            mock_report = FeasibilityReport(
                status=FeasibilityStatus.FAIL,
                confidence_score=20,
                recoverability=Recoverability.NEAR_IMPOSSIBLE,
                errors=["Insufficient slots"],
                warnings=WarningCollection(),
                constraint_scores={},
                suggestions=[]
            )
            mock_analyze.return_value = mock_report

            with pytest.raises(FeasibilityError) as exc_info:
                await use_case.generate_timetable_simple(
                    semester=1,
                    section="A",
                    created_by="admin1"
                )

            assert exc_info.value.report == mock_report


@pytest.mark.asyncio
async def test_generate_proceeds_on_feasibility_warning():
    """Should attach warnings when feasibility has warnings."""
    use_case = _create_use_case()

    # Mock detect_assignments_for_timetable to return data
    with patch.object(use_case, 'detect_assignments_for_timetable') as mock_detect:
        mock_detect.return_value = {
            "subject_ids": ["sub1"],
            "faculty_availability": {"fac1": {"MON": [1, 2, 3, 4, 5]}},
            "subject_faculty_map": {"sub1": "fac1"}
        }

        # Mock subject_repository.find_by_id to return a subject
        mock_subject = MagicMock(spec=Subject)
        mock_subject.id = "sub1"
        mock_subject.code = "CS101"
        mock_subject.name = "Intro to CS"
        mock_subject.classes_per_week = 3
        mock_subject.subject_type = SubjectType.THEORY

        use_case.subject_repository.find_by_id = AsyncMock(return_value=mock_subject)

        with patch.object(use_case.feasibility_analyzer, 'analyze') as mock_analyze:
            from app.domain.entities.feasibility import FeasibilityReport

            mock_report = FeasibilityReport(
                status=FeasibilityStatus.WARNING,
                confidence_score=65,
                recoverability=Recoverability.DIFFICULT,
                errors=[],
                warnings=WarningCollection(),
                constraint_scores={},
                suggestions=[]
            )
            mock_analyze.return_value = mock_report

            # Mock generate_timetable to return response
            with patch.object(use_case, 'generate_timetable') as mock_generate:
                mock_response = MagicMock()
                mock_response.warnings = None
                mock_response.duration_ms = 1000
                mock_generate.return_value = mock_response

                response = await use_case.generate_timetable_simple(
                    semester=1,
                    section="A",
                    created_by="admin1"
                )

                # Should have feasibility_warnings attached
                assert response.feasibility_warnings is not None
                assert response.confidence_score == 65
                assert response.recoverability == "DIFFICULT"


@pytest.mark.asyncio
async def test_collects_same_semester_occupied_slots_excluding_current_section():
    """Generation should reserve class slots from other active sections in the semester."""
    use_case = _create_use_case()
    other_section_timetable = Timetable(
        id="tt-a",
        semester=1,
        section="A",
        version=1,
        is_active=True,
        schedule=[
            DaySchedule(
                day=DayOfWeek.MONDAY,
                slots=[
                    TimetableSlot(slot=1, subject_id="sub-a", faculty_id="fac-a"),
                    TimetableSlot(slot=2, subject_id=None, faculty_id=None, room="LUNCH"),
                    TimetableSlot(slot=3, subject_id=None, faculty_id=None),
                ]
            )
        ],
        created_by="admin",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    use_case.timetable_repository.find_active_by_semester = AsyncMock(
        return_value=[other_section_timetable]
    )
    use_case.subject_repository.find_by_id = AsyncMock(return_value=None)
    use_case.user_repo.find_by_id = AsyncMock(return_value=None)

    occupied = await use_case._get_semester_occupied_slots(
        semester=1,
        exclude_section="B"
    )

    assert occupied == [
        {
            "day": DayOfWeek.MONDAY,
            "slot": 1,
            "section": "A",
            "subject_id": "sub-a",
            "faculty_id": "fac-a",
            "subject_name": None,
            "subject_code": None,
            "subject_type": None,
            "faculty_name": None,
        }
    ]
    use_case.timetable_repository.find_active_by_semester.assert_awaited_once_with(
        semester=1,
        exclude_section="B"
    )


def _create_use_case():
    """Helper to create test use case."""
    from app.domain.services.feasibility_analyzer import FeasibilityAnalyzer

    mock_subject_repo = AsyncMock()
    mock_timetable_repo = AsyncMock()
    mock_assignment_repo = AsyncMock()
    mock_user_repo = AsyncMock()
    mock_availability_repo = AsyncMock()
    mock_availability_service = AsyncMock()
    mock_override_repo = AsyncMock()
    mock_telemetry_repo = AsyncMock()

    use_case = TimetableUseCase(
        subject_repository=mock_subject_repo,
        timetable_repository=mock_timetable_repo,
        assignment_repo=mock_assignment_repo,
        user_repo=mock_user_repo,
        faculty_availability_repo=mock_availability_repo,
        availability_service=mock_availability_service,
        override_repo=mock_override_repo,
        telemetry_repo=mock_telemetry_repo
    )

    use_case.feasibility_analyzer = FeasibilityAnalyzer()

    return use_case
