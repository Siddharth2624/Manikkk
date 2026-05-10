"""Timetable generation tests."""

import pytest
from datetime import datetime
from app.adapters.services.timetable_generator import TimetableGenerator
from app.domain.entities.subject import Subject, SubjectType
from app.domain.entities.timetable import DayOfWeek


@pytest.mark.asyncio
async def test_time_slots():
    """Test time slot configuration."""
    generator = TimetableGenerator([])
    slots = generator.get_time_slots()

    assert len(slots) == 10
    assert slots[0]["slot_number"] == 1
    assert "09:00" in slots[0]["display"]


@pytest.mark.asyncio
async def test_working_days():
    """Test working days configuration."""
    generator = TimetableGenerator([])
    days = generator.get_working_days()

    assert len(days) == 5
    assert DayOfWeek.MONDAY in days
    assert DayOfWeek.FRIDAY in days
    assert DayOfWeek.SATURDAY not in days
    assert DayOfWeek.SUNDAY not in days


@pytest.mark.asyncio
async def test_lunch_break_slots():
    """Test lunch break slots."""
    generator = TimetableGenerator([])
    lunch_slots = generator.get_lunch_break_slots()

    assert 5 in lunch_slots  # 12:20-13:10
    assert 6 in lunch_slots  # 13:10-14:00


@pytest.mark.asyncio
async def test_validate_constraints_success():
    """Test validation with valid inputs."""
    subjects = [
        Subject(
            id="s1",
            code="CS101",
            name="Intro to CS",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=4,
            classes_per_week=4
        )
    ]

    generator = TimetableGenerator(subjects)

    faculty_availability = {
        "f1": {
            DayOfWeek.MONDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.TUESDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.WEDNESDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.THURSDAY: [1, 2, 3, 4, 7, 8, 9],
            DayOfWeek.FRIDAY: [1, 2, 3, 4, 7, 8, 9]
        }
    }

    result = await generator.validate_constraints(
        semester=1,
        sections=["A"],
        subject_ids=["s1"],
        faculty_availability=faculty_availability
    )

    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_validate_constraints_invalid_semester():
    """Test validation with invalid semester."""
    generator = TimetableGenerator([])

    result = await generator.validate_constraints(
        semester=9,  # Invalid semester
        sections=["A"],
        subject_ids=[],
        faculty_availability={}
    )

    assert result["valid"] is False
    assert any("Semester must be between 1 and 8" in e for e in result["errors"])
