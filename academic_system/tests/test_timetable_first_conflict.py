"""Tests for timetable generation conflict reporting behavior."""

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
async def test_collects_all_theory_conflicts():
    """Should collect every theory availability blocker before returning."""
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
    # Should mention every blocker so the admin can resolve them in one pass.
    assert "Conflict" in error_msg
    assert "CS Theory" in error_msg or "CS101" in error_msg
    assert "CS Theory 2" in error_msg
    assert "CS102" in error_msg
    assert len(generator.last_conflicts) == 3
    assert {conflict["type"] for conflict in generator.last_conflicts} == {
        "insufficient_subject_availability",
        "faculty_total_shortage",
    }
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
async def test_lab_uses_only_explicit_consecutive_availability():
    """A lab should occupy two slots only when both slots are available."""
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

    timetable = await generator.generate(
        semester=1,
        sections=["A"],
        subject_ids=["lab1"],
        faculty_availability={
            "f1": {
                DayOfWeek.MONDAY: [2, 3],
            }
        },
        subject_faculty_map={"lab1": "f1"}
    )

    monday = next(day for day in timetable.schedule if day.day == DayOfWeek.MONDAY)
    assigned_slots = {
        slot.slot
        for slot in monday.slots
        if slot.subject_id == "lab1"
    }

    assert assigned_slots == {2, 3}


@pytest.mark.asyncio
async def test_generation_avoids_same_semester_occupied_theory_slots():
    """A section must not use slots already occupied by another section in the same semester."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=2,
            classes_per_week=2
        )
    ]

    generator = TimetableGenerator(subjects)

    timetable = await generator.generate(
        semester=1,
        sections=["B"],
        subject_ids=["theory1"],
        faculty_availability={
            "f1": {
                DayOfWeek.MONDAY: [1, 2, 3],
            }
        },
        subject_faculty_map={"theory1": "f1"},
        occupied_slots=[
            {"day": DayOfWeek.MONDAY, "slot": 1, "section": "A"}
        ]
    )

    monday = next(day for day in timetable.schedule if day.day == DayOfWeek.MONDAY)
    assigned_slots = {
        slot.slot
        for slot in monday.slots
        if slot.subject_id == "theory1"
    }

    assert assigned_slots == {2, 3}


@pytest.mark.asyncio
async def test_generation_avoids_same_semester_occupied_lab_slots():
    """A lab pair must not overlap a slot already occupied by another section."""
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

    timetable = await generator.generate(
        semester=1,
        sections=["B"],
        subject_ids=["lab1"],
        faculty_availability={
            "f1": {
                DayOfWeek.MONDAY: [1, 2, 3],
            }
        },
        subject_faculty_map={"lab1": "f1"},
        occupied_slots=[
            {"day": "MON", "slot": 1, "section": "A", "subject_type": "lab"}
        ]
    )

    monday = next(day for day in timetable.schedule if day.day == DayOfWeek.MONDAY)
    assigned_slots = {
        slot.slot
        for slot in monday.slots
        if slot.subject_id == "lab1"
    }

    assert assigned_slots == {2, 3}


@pytest.mark.asyncio
async def test_lab_can_overlap_other_section_theory_slot():
    """A lab can run while another section uses the semester classroom for theory."""
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

    timetable = await generator.generate(
        semester=1,
        sections=["B"],
        subject_ids=["lab1"],
        faculty_availability={
            "f1": {
                DayOfWeek.THURSDAY: [3, 4],
            }
        },
        subject_faculty_map={"lab1": "f1"},
        occupied_slots=[
            {"day": "THU", "slot": 3, "section": "A", "subject_type": "theory"},
            {"day": "THU", "slot": 4, "section": "A", "subject_type": "theory"},
        ]
    )

    thursday = next(day for day in timetable.schedule if day.day == DayOfWeek.THURSDAY)
    assigned_slots = {
        slot.slot
        for slot in thursday.slots
        if slot.subject_id == "lab1"
    }

    assert assigned_slots == {3, 4}


@pytest.mark.asyncio
async def test_theory_can_overlap_other_section_lab_slot():
    """A theory class can use the classroom while another section has lab."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=1,
            classes_per_week=1
        )
    ]

    generator = TimetableGenerator(subjects)

    timetable = await generator.generate(
        semester=1,
        sections=["B"],
        subject_ids=["theory1"],
        faculty_availability={
            "f1": {
                DayOfWeek.THURSDAY: [3],
            }
        },
        subject_faculty_map={"theory1": "f1"},
        occupied_slots=[
            {"day": "THU", "slot": 3, "section": "A", "subject_type": "lab"},
        ]
    )

    thursday = next(day for day in timetable.schedule if day.day == DayOfWeek.THURSDAY)
    assigned_slots = {
        slot.slot
        for slot in thursday.slots
        if slot.subject_id == "theory1"
    }

    assert assigned_slots == {3}


@pytest.mark.asyncio
async def test_lab_conflict_reports_same_semester_section_blockers():
    """When lab pairs are blocked by another section, report those blockers clearly."""
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

    with pytest.raises(ValueError):
        await generator.generate(
            semester=1,
            sections=["B"],
            subject_ids=["lab1"],
            faculty_availability={
                "f1": {
                    DayOfWeek.MONDAY: [9, 10],
                    DayOfWeek.THURSDAY: [3, 4],
                }
            },
            subject_faculty_map={"lab1": "f1"},
            faculty_names={"f1": "Dr. Lab"},
            occupied_slots=[
                {
                    "day": "MON",
                    "slot": 9,
                    "section": "A",
                    "subject_type": "lab",
                    "subject_id": "other1",
                    "subject_name": "Other Subject",
                    "subject_code": "OS101",
                    "faculty_name": "Dr. Other",
                },
                {"day": "MON", "slot": 10, "section": "A", "subject_type": "lab"},
                {"day": "THU", "slot": 3, "section": "A", "subject_type": "lab"},
                {"day": "THU", "slot": 4, "section": "A", "subject_type": "lab"},
            ]
        )

    conflict = generator.last_conflicts[0]
    assert conflict["type"] == "lab_scheduling_conflict"
    assert conflict["usable_consecutive_pairs"] == []
    assert len(conflict["available_consecutive_pairs"]) == 2
    assert any(
        slot.get("source") == "same_semester_section" and slot.get("section") == "A"
        for slot in conflict["blocked_slots"]
    )
    assert "Section A" in conflict["issue"]


@pytest.mark.asyncio
async def test_generation_reserves_exactly_one_lunch_slot_each_day():
    """Every working day should have one lunch break in slot 5 or 6."""
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

    timetable = await generator.generate(
        semester=1,
        sections=["A"],
        subject_ids=["theory1"],
        faculty_availability={
            "f1": {
                DayOfWeek.MONDAY: [1, 2, 3, 4, 5, 6],
            }
        },
        subject_faculty_map={"theory1": "f1"}
    )

    for day_schedule in timetable.schedule:
        lunch_slots = [
            slot.slot
            for slot in day_schedule.slots
            if slot.is_lunch()
        ]
        assert len(lunch_slots) == 1
        assert lunch_slots[0] in {5, 6}

    monday = next(day for day in timetable.schedule if day.day == DayOfWeek.MONDAY)
    monday_lunch_classes = [
        slot
        for slot in monday.slots
        if slot.slot in {5, 6} and slot.subject_id == "theory1"
    ]
    assert len(monday_lunch_classes) == 1


@pytest.mark.asyncio
async def test_lunch_uses_other_slot_when_class_needs_lunch_window():
    """A class may use one lunch-window slot, but the other remains lunch."""
    subjects = [
        Subject(
            id="theory1",
            code="CS101",
            name="CS Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=1,
            classes_per_week=1
        )
    ]

    generator = TimetableGenerator(subjects)

    timetable = await generator.generate(
        semester=1,
        sections=["A"],
        subject_ids=["theory1"],
        faculty_availability={
            "f1": {
                DayOfWeek.MONDAY: [5],
            }
        },
        subject_faculty_map={"theory1": "f1"}
    )

    monday = next(day for day in timetable.schedule if day.day == DayOfWeek.MONDAY)
    slot_5 = monday.get_slot(5)
    slot_6 = monday.get_slot(6)

    assert slot_5.subject_id == "theory1"
    assert slot_6.is_lunch()


@pytest.mark.asyncio
async def test_lab_does_not_use_unavailable_neighbor_slot():
    """A lab must not use slot 2 just because slot 1 is available."""
    subjects = [
        Subject(
            id="blocker_lab",
            code="CS100L",
            name="Blocking Lab",
            semester=1,
            subject_type=SubjectType.LAB,
            credits=2,
            classes_per_week=2
        ),
        Subject(
            id="target_lab",
            code="CS101L",
            name="Target Lab",
            semester=1,
            subject_type=SubjectType.LAB,
            credits=2,
            classes_per_week=2
        )
    ]

    generator = TimetableGenerator(subjects)

    with pytest.raises(ValueError):
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["blocker_lab", "target_lab"],
            faculty_availability={
                "blocker_faculty": {
                    DayOfWeek.TUESDAY: [7, 8],
                },
                "target_faculty": {
                    DayOfWeek.MONDAY: [1, 3],
                    DayOfWeek.TUESDAY: [7, 8],
                },
            },
            subject_faculty_map={
                "blocker_lab": "blocker_faculty",
                "target_lab": "target_faculty",
            }
        )

    assert len(generator.last_conflicts) == 1
    conflict = generator.last_conflicts[0]
    assert conflict["type"] == "lab_scheduling_conflict"
    assert conflict["available_consecutive_pairs"]
    assert conflict["blocked_slots"]
    assert all(
        not (slot["day"] == "MON" and slot["slot"] == 2)
        for slot in conflict["available_slots"]
    )


@pytest.mark.asyncio
async def test_lab_conflict_reports_non_consecutive_available_slots():
    """When slots exist but are not consecutive, report those slots clearly."""
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

    with pytest.raises(ValueError) as exc_info:
        await generator.generate(
            semester=1,
            sections=["A"],
            subject_ids=["lab1"],
            faculty_availability={
                "f1": {
                    DayOfWeek.MONDAY: [1],
                    DayOfWeek.TUESDAY: [2],
                    DayOfWeek.WEDNESDAY: [4],
                }
            },
            subject_faculty_map={"lab1": "f1"}
        )

    assert "Available:" in str(exc_info.value)
    assert "Usable lab pairs: None" in str(exc_info.value)
    conflict = generator.last_conflicts[0]
    assert conflict["type"] == "missing_consecutive_slots"
    assert conflict["available_slots"]
    assert conflict["available_consecutive_pairs"] == []


@pytest.mark.asyncio
async def test_flexible_subject_does_not_consume_constrained_subject_slot():
    """A 3-credit subject with 4 slots should use the 3 non-conflicting slots."""
    subjects = [
        Subject(
            id="flexible",
            code="CS201",
            name="Flexible Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=3,
            classes_per_week=3
        ),
        Subject(
            id="constrained",
            code="CS202",
            name="Constrained Theory",
            semester=1,
            subject_type=SubjectType.THEORY,
            credits=1,
            classes_per_week=1
        )
    ]

    generator = TimetableGenerator(subjects)

    faculty_availability = {
        "flexible_faculty": {
            DayOfWeek.MONDAY: [1, 2, 3, 4],
        },
        "constrained_faculty": {
            DayOfWeek.MONDAY: [1],
        }
    }

    timetable = await generator.generate(
        semester=1,
        sections=["A"],
        subject_ids=["flexible", "constrained"],
        faculty_availability=faculty_availability,
        subject_faculty_map={
            "flexible": "flexible_faculty",
            "constrained": "constrained_faculty"
        }
    )

    monday = next(day for day in timetable.schedule if day.day == DayOfWeek.MONDAY)
    assigned_by_slot = {
        slot.slot: slot.subject_id
        for slot in monday.slots
        if slot.subject_id
    }

    assert assigned_by_slot[1] == "constrained"
    assert {assigned_by_slot[2], assigned_by_slot[3], assigned_by_slot[4]} == {"flexible"}


@pytest.mark.asyncio
async def test_reports_all_lab_conflicts():
    """Should report each lab conflict, not just the first one."""
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
    assert "CS Lab" in error_msg
    assert "CS Lab 2" in error_msg
    assert len(generator.last_conflicts) == 2
    assert all(conflict["type"] == "missing_consecutive_slots" for conflict in generator.last_conflicts)
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
    assert generator.last_conflicts[0]["available_slots"]


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
    assert generator.last_conflicts[0]["available_slots"]


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
    # Should show which available faculty slots were already consumed by the current attempt.
    assert "Blocked by current attempt" in error_msg, f"Expected blocked slot details in error, got: {error_msg}"
    assert generator.last_conflicts[0]["blocked_slots"]
