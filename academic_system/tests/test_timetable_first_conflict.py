"""Tests for stop-at-first-conflict timetable generation behavior."""

import pytest
from app.adapters.services.timetable_generator import TimetableGenerator
from app.domain.entities.subject import Subject, SubjectType
from app.domain.entities.timetable import DayOfWeek


@pytest.mark.asyncio
async def test_stops_at_first_lab_conflict():
    """Should stop immediately when a lab subject cannot be scheduled."""
    # Create subjects: one lab that requires 2 consecutive slots
    subjects = [
        Subject(
            id="lab1",
            code="CS101L",
            name="CS Lab",
            semester=1,
            subject_type=SubjectType.LAB,
            credits=2,
            classes_per_week=2
        ),
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=4,
            classes_per_week=4
        )
    ]

    generator = TimetableGenerator(subjects)

    # Faculty availability: only single slots, no consecutive pairs for lab
    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 3, 7],
            DayOfWeek.TUESDAY: [1, 3, 7],
            DayOfWeek.WEDNESDAY: [1, 3, 7],
            DayOfWeek.THURSDAY: [1, 3, 7],
            DayOfWeek.FRIDAY: [1, 3, 7]
        }
    }

    subject_faculty_map = {
        "lab1": "f1",
        "theory1": "f1"
    }

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["lab1", "theory1"],
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map
        )

    error_msg = str(exc_info.value)
    # Should mention the lab conflict
    assert "Conflict" in error_msg
    assert "CS Lab" in error_msg or "CS101L" in error_msg
    assert "lab" in error_msg.lower() or "consecutive" in error_msg.lower()
    # Should NOT mention the theory subject - we stopped at the lab conflict
    assert "CS Theory" not in error_msg
    # Should be a single conflict message, not a long report
    assert "CONFLICT ANALYSIS REPORT" not in error_msg


@pytest.mark.asyncio
async def test_stops_at_first_theory_conflict():
    """Should stop immediately when a theory subject cannot be scheduled."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=5,
            classes_per_week=5
        ),
        Subject(
            id="theory2",
            code="CS102",
            name="CS Theory 2",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=4,
            classes_per_week=4
        )
    ]

    generator = TimetableGenerator(subjects)

    # Faculty has only 3 slots but needs 5 for first subject
    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 2, 3],
        }
    }

    subject_faculty_map = {
        "theory1": "f1",
        "theory2": "f1"
    }

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["theory1", "theory2"],
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map
        )

    error_msg = str(exc_info.value)
    # Should mention the first theory conflict
    assert "Conflict" in error_msg
    assert "CS Theory" in error_msg or "CS101" in error_msg
    # Should NOT mention the second theory subject - we stopped at the first conflict
    assert "CS Theory 2" not in error_msg
    assert "CS102" not in error_msg
    # Should be a single conflict message, not a long report
    assert "CONFLICT ANALYSIS REPORT" not in error_msg


@pytest.mark.asyncio
async def test_successful_generation_no_conflicts():
    """Should successfully generate timetable when no conflicts exist."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=3,
            classes_per_week=3
        )
    ]

    generator = TimetableGenerator(subjects)

    # Plenty of slots available
    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.TUESDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.WEDNESDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.THURSDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.FRIDAY: [1, 2, 3, 4, 7, 8, 9]
        }
    }

    subject_faculty_map = {
        "theory1": "f1"
    }

    # Should succeed without raising
    timetable = await generator.generate(
        semester=1,
        sections=["A"],
        subject_ids=["theory1"],
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert timetable is not None
    assert timetable.semester == 1
    assert timetable.section == "A"
    assert len(timetable.schedule) == 5  # 5 working days


@pytest.mark.asyncio
async def test_reports_only_one_conflict():
    """Should report exactly one conflict, not multiple."""
    subjects = [
        Subject(
            id="lab1",
            code="CS101L",
            name="CS Lab",
            semester=1,
            subject_type=SubjectType.LAB,
            credits=2,
            classes_per_week=2
        ),
        Subject(
            id="lab2",
            code="CS102L",
            name="CS Lab 2",
            semester=1,
            subject_type=SubjectType.LAB,
            credits=2,
            classes_per_week=2
        ),
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=4,
            classes_per_week=4
        )
    ]

    generator = TimetableGenerator(subjects)

    # No consecutive slots for any lab
    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 3, 5, 7, 9],
            DayOfWeek.TUESDAY: [1, 3, 5, 7, 9],
        },
        "f2": {
            DayOfWeek.MONDAY: [1, 3, 5, 7, 9],
            DayOfWeek.TUESDAY: [1, 3, 5, 7, 9],
        }
    }

    subject_faculty_map = {
        "lab1": "f1",
        "lab2": "f2",
        "theory1": "f1"
    }

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["lab1", "lab2", "theory1"],
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map
        )

    error_msg = str(exc_info.value)
    # Should only contain one conflict
    # Count occurrences of "Conflict:" - should be exactly 1
    conflict_count = error_msg.count("Conflict:")
    assert conflict_count == 1, f"Expected exactly 1 conflict, but found {conflict_count}: {error_msg}"
    # Should not be the old comprehensive report format
    assert "CONFLICT ANALYSIS REPORT" not in error_msg
    # Should not contain slot-wise analysis
    assert "SLOT-LEVEL CONFLICTS" not in error_msg


@pytest.mark.asyncio
async def test_shows_faculty_name_and_slots_in_conflict():
    """Should show faculty name and specific slot details in conflict message."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=5,
            classes_per_week=5
        )
    ]

    generator = TimetableGenerator(subjects)

    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 2, 3],
        }
    }

    subject_faculty_map = {
        "theory1": "f1"
    }

    faculty_names = {
        "f1": "Dr. Smith"
    }

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["theory1"],
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map,
            faculty_names=faculty_names
        )

    error_msg = str(exc_info.value)
    # Should show the faculty name, not ID
    assert "Dr. Smith" in error_msg, f"Expected faculty name in error, got: {error_msg}"
    # Should show available slots
    assert "Available:" in error_msg, f"Expected available slots in error, got: {error_msg}"
    # Should show the subject
    assert "CS Theory" in error_msg, f"Expected subject name in error, got: {error_msg}"


@pytest.mark.asyncio
async def test_shows_faculty_name_and_slots_in_lab_conflict():
    """Should show faculty name and slot details in lab conflict message."""
    subjects = [
        Subject(
            id="lab1",
            code="CS101L",
            name="CS Lab",
            semester=1,
            subject_type=SubjectType.LAB,
            credits=2,
            classes_per_week=2
        )
    ]

    generator = TimetableGenerator(subjects)

    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 3, 5],
            DayOfWeek.TUESDAY: [2, 4, 6],
        }
    }

    subject_faculty_map = {
        "lab1": "f1"
    }

    faculty_names = {
        "f1": "Dr. Johnson"
    }

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["lab1"],
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map,
            faculty_names=faculty_names
        )

    error_msg = str(exc_info.value)
    # Should show the faculty name, not ID
    assert "Dr. Johnson" in error_msg, f"Expected faculty name in error, got: {error_msg}"
    # Should show available slots
    assert "Available:" in error_msg, f"Expected available slots in error, got: {error_msg}"
    # Should show the subject code
    assert "CS101L" in error_msg, f"Expected subject code in error, got: {error_msg}"


@pytest.mark.asyncio
async def test_shows_assignment_phase_conflict_with_slot_details():
    """Should show specific slot details when assignment fails after pre-validation passes."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=3,
            classes_per_week=3
        ),
        Subject(
            id="theory2",
            code="CS102",
            name="CS Theory 2",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=3,
            classes_per_week=3
        )
    ]

    generator = TimetableGenerator(subjects)

    # Both faculty have enough total slots (3 each = 6 needed, 6 available)
    # but they compete for the same slots
    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 2, 3],
        },
        "f2": {
            DayOfWeek.MONDAY: [1, 2, 3],
        }
    }

    subject_faculty_map = {
        "theory1": "f1",
        "theory2": "f2"
    }

    faculty_names = {
        "f1": "Dr. Smith",
        "f2": "Dr. Jones"
    }

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["theory1", "theory2"],
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map,
            faculty_names=faculty_names
        )

    error_msg = str(exc_info.value)
    # Should show the faculty name
    assert "Dr. Jones" in error_msg or "Dr. Smith" in error_msg, f"Expected faculty name in error, got: {error_msg}"
    # Should show slot details like "slot X/Y"
    assert "slot" in error_msg.lower(), f"Expected slot detail in error, got: {error_msg}"
    # Should show already assigned slots
    assert "Already assigned" in error_msg, f"Expected already assigned in error, got: {error_msg}"
