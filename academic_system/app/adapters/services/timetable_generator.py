"""
Timetable Generation Service - Updated for new single-document schema.

This service generates timetables using the new schema structure where
a Timetable contains a schedule (list of DaySchedule, each with slots).

Note: Since Subject no longer has faculty_id, this generator accepts
a subject_faculty_map parameter to map subjects to their assigned faculty.
"""

import os
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from app.domain.entities.timetable import (
    Timetable, TimetableSlot, DaySchedule, DayOfWeek, SlotType, TimeSlot
)
from app.domain.entities.subject import Subject, SubjectType
from app.domain.entities.feasibility import ConstraintScore
from app.domain.interfaces.timetable_generator import ITimetableGenerator


# =============================================================================
# Conflict Reporting Data Structures
# =============================================================================


@dataclass
class SlotConflict:
    """Represents a conflict at a specific time slot."""
    day: str
    slot_number: int
    time_range: str
    competing_faculty: List[Dict[str, str]]  # [{faculty_id, faculty_name}]
    competing_subjects: List[Dict[str, str]]  # [{subject_id, subject_name}]
    conflict_type: str  # "OVERBOOKED", "NO_AVAILABILITY", "INSUFFICIENT_SLOTS"
    description: str


@dataclass
class FacultyConflict:
    """Represents conflicts for a specific faculty member."""
    faculty_id: str
    faculty_name: str
    total_available_slots: int
    required_slots: int
    shortage: int
    subjects: List[Dict[str, Any]]  # [{subject_id, subject_name, required_slots}]
    conflicting_slots: List[str]  # ["MON-1", "TUE-2", etc.]


@dataclass
class SubjectConflict:
    """Represents a conflict for a specific subject."""
    subject_id: str
    subject_name: str
    subject_code: str
    subject_type: str  # "THEORY", "LAB", "ELECTIVE"
    required_slots: int
    faculty_id: str
    faculty_name: str
    faculty_available_slots: int
    conflict_reason: str  # "INSUFFICIENT_SLOTS", "NO_CONSECUTIVE_FOR_LAB", "FACULTY_OVERBOOKED"
    available_faculty_slots: List[Dict[str, Any]]  # [{day, slot}]


@dataclass
class ConflictReport:
    """Comprehensive conflict report for failed timetable generation."""
    total_attempts: int
    summary: str
    slot_conflicts: List[SlotConflict]
    faculty_conflicts: List[FacultyConflict]
    subject_conflicts: List[SubjectConflict]
    suggestions: List[str]

    def to_detailed_message(self) -> str:
        """Convert the conflict report to a detailed, human-readable message."""
        lines = []
        lines.append(f"Failed to generate timetable after {self.total_attempts} attempts.")
        lines.append("\n" + "="*70)
        lines.append("CONFLICT ANALYSIS REPORT")
        lines.append("="*70)

        if self.subject_conflicts:
            lines.append(f"\n### SUBJECT CONFLICTS ({len(self.subject_conflicts)}) ###")
            for i, conflict in enumerate(self.subject_conflicts, 1):
                lines.append(f"\n{i}. {conflict.subject_code} - {conflict.subject_name}")
                lines.append(f"   Type: {conflict.subject_type}")
                lines.append(f"   Faculty: {conflict.faculty_name} (ID: {conflict.faculty_id})")
                lines.append(f"   Required: {conflict.required_slots} slots | Available: {conflict.faculty_available_slots} slots")
                lines.append(f"   Issue: {conflict.conflict_reason}")

                if conflict.available_faculty_slots:
                    slots_str = ", ".join([f"{s['day']}-{s['slot']}" for s in conflict.available_faculty_slots[:10]])
                    if len(conflict.available_faculty_slots) > 10:
                        slots_str += f" ... ({len(conflict.available_faculty_slots)} total)"
                    lines.append(f"   Faculty's available slots: {slots_str}")

        if self.faculty_conflicts:
            lines.append(f"\n### FACULTY CONFLICTS ({len(self.faculty_conflicts)}) ###")
            for i, conflict in enumerate(self.faculty_conflicts, 1):
                lines.append(f"\n{i}. {conflict.faculty_name} (ID: {conflict.faculty_id})")
                lines.append(f"   Total required: {conflict.required_slots} slots | Available: {conflict.total_available_slots} slots")
                lines.append(f"   Shortage: {conflict.shortage} slots")
                lines.append(f"   Subjects assigned:")
                for subj in conflict.subjects:
                    lines.append(f"     - {subj['subject_code']}: {subj['subject_name']} ({subj['required_slots']} slots)")

                if conflict.conflicting_slots:
                    slots_str = ", ".join(conflict.conflicting_slots[:15])
                    if len(conflict.conflicting_slots) > 15:
                        slots_str += f" ... ({len(conflict.conflicting_slots)} total)"
                    lines.append(f"   Available slots: {slots_str}")

        if self.slot_conflicts:
            lines.append(f"\n### SLOT-LEVEL CONFLICTS ({len(self.slot_conflicts)}) ###")
            for i, conflict in enumerate(self.slot_conflicts, 1):
                lines.append(f"\n{i}. {conflict.day} Slot {conflict.slot_number} ({conflict.time_range})")
                lines.append(f"   Type: {conflict.conflict_type}")
                lines.append(f"   {conflict.description}")
                if conflict.competing_faculty:
                    faculty_list = ", ".join([f"{f['faculty_name']}" for f in conflict.competing_faculty[:5]])
                    if len(conflict.competing_faculty) > 5:
                        faculty_list += f" (+{len(conflict.competing_faculty) - 5} more)"
                    lines.append(f"   Competing faculty: {faculty_list}")
                if conflict.competing_subjects:
                    subject_list = ", ".join([f"{s['subject_code']}" for s in conflict.competing_subjects[:5]])
                    if len(conflict.competing_subjects) > 5:
                        subject_list += f" (+{len(conflict.competing_subjects) - 5} more)"
                    lines.append(f"   Competing subjects: {subject_list}")

        if self.suggestions:
            lines.append(f"\n### SUGGESTIONS TO RESOLVE ###")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"{i}. {suggestion}")

        lines.append("\n" + "="*70)
        return "\n".join(lines)


class TimetableGenerator(ITimetableGenerator):
    """
    Timetable generation service using the new schema.

    Algorithm extends the original Django implementation to support:
    - Multiple semesters (1-8)
    - Multiple sections per semester
    - Lab and theory subjects
    - Faculty availability constraints
    - Lunch breaks
    """

    # Time slot definitions (slot_number, start_time, end_time)
    TIME_SLOTS = [
        (1, "09:00", "09:50"),
        (2, "09:50", "10:40"),
        (3, "10:40", "11:30"),
        (4, "11:30", "12:20"),
        (5, "12:20", "13:10"),
        (6, "13:10", "14:00"),
        (7, "14:00", "14:50"),
        (8, "14:50", "15:40"),
        (9, "15:40", "16:30"),
        (10, "16:30", "17:20"),
    ]

    # Lunch break slots
    LUNCH_SLOTS = [5, 6]  # 12:20-13:10, 13:10-14:00

    # Working days
    WORKING_DAYS = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY
    ]

    def __init__(self, subjects: List[Subject]):
        """
        Initialize the generator with subjects.

        Args:
            subjects: List of subjects to schedule
        """
        self.subjects = subjects
        self.time_slots = [TimeSlot(num, start, end)
                          for num, start, end in self.TIME_SLOTS]
        # Deterministic seeding for reproducibility
        self.random_seed = os.urandom(4).hex()
        self.rng = random.Random(self.random_seed)
        self.last_attempt_count = 0
        self.last_conflicts: List[Dict[str, Any]] = []

    def get_time_slots(self) -> List[Dict[str, Any]]:
        """Get configured time slots."""
        return [slot.to_dict() for slot in self.time_slots]

    def get_working_days(self) -> List[DayOfWeek]:
        """Get working days for timetable."""
        return self.WORKING_DAYS

    def get_lunch_break_slots(self) -> List[int]:
        """Get lunch break slot numbers."""
        return self.LUNCH_SLOTS

    def get_default_constraint_score(self, subject_id: str) -> ConstraintScore:
        """
        Return a default ConstraintScore for a subject if not found in feasibility analysis.

        This is used when scheduling logic needs a constraint score but one wasn't
        pre-computed during feasibility analysis.

        Args:
            subject_id: The subject ID to get a default score for

        Returns:
            A ConstraintScore with conservative default values
        """
        # Find the subject
        subject = None
        for s in self.subjects:
            if s.id == subject_id:
                subject = s
                break

        if subject is None:
            # Subject not found - return a critical score
            return ConstraintScore(
                subject_id=subject_id,
                faculty_id="unknown",
                subject_name="Unknown Subject",
                faculty_name="Unknown Faculty",
                required_slots=1,
                unique_available_slots=0
            )

        # Return a moderate default - assume reasonable availability
        # Using 5 unique slots as a conservative default (1 per day for 5 days)
        return ConstraintScore(
            subject_id=subject_id,
            faculty_id="unassigned",
            subject_name=subject.name,
            faculty_name="Unassigned Faculty",
            required_slots=subject.credits if hasattr(subject, 'credits') else 3,
            unique_available_slots=10  # Assume 2 slots per day across 5 days
        )

    async def validate_constraints(
        self,
        semester: int,
        sections: List[str],
        subject_ids: List[str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]]
    ) -> Dict[str, Any]:
        """
        Validate if timetable generation is possible with given inputs.

        Note: Faculty availability check is done at the assignment level,
        not subject level, since Subject no longer stores faculty_id.
        """
        errors = []
        warnings = []

        # Validate semester
        if not 1 <= semester <= 8:
            errors.append(f"Semester must be between 1 and 8, got {semester}")

        # Validate sections
        if not sections:
            errors.append("At least one section is required")

        # Validate subjects exist for semester
        semester_subjects = [s for s in self.subjects if s.id in subject_ids]
        if not semester_subjects:
            errors.append(f"No subjects found for the given subject IDs")

        # Check total required slots vs available slots. Exactly one lunch slot
        # is reserved per working day, while the other lunch-window slot can be
        # used for a class if needed.
        total_required = sum(s.get_weekly_hours() for s in semester_subjects) * len(sections)
        total_available = len(self.WORKING_DAYS) * (len(self.time_slots) - 1)

        if total_required > total_available:
            errors.append(
                f"Insufficient slots: Required {total_required}, Available {total_available}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    async def generate(
        self,
        semester: int,
        sections: List[str],
        subject_ids: List[str],
        faculty_availability: Dict[str, Dict[Any, List[int]]],  # Day keys can be string or DayOfWeek
        subject_faculty_map: Optional[Dict[str, str]] = None,
        faculty_names: Optional[Dict[str, str]] = None,
        occupied_slots: Optional[List[Dict[str, Any]]] = None
    ) -> Timetable:
        """
        Generate timetable for the given parameters.

        This adapts the existing Django algorithm:
        1. Initialize empty timetable grid
        2. Assign lab subjects (require 2 consecutive slots)
        3. Assign theory subjects
        4. Assign lunch breaks
        5. Handle conflicts and reassign

        Args:
            semester: Semester number (1-8)
            sections: List of sections (e.g., ["A", "B"])
            subject_ids: List of subject IDs to schedule
            faculty_availability: Faculty availability mapping (faculty_id -> day -> slots)
            subject_faculty_map: Optional mapping of subject_id to faculty_id
            faculty_names: Optional mapping of faculty_id to faculty_name

        Returns:
            Generated timetable with schedule in new format

        Raises:
            ValueError: If generation fails
        """
        # Filter subjects for this semester
        semester_subjects = [s for s in self.subjects if s.id in subject_ids]

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG GENERATOR] self.subjects count: {len(self.subjects)}, subject_ids: {subject_ids}")
        logger.info(f"[DEBUG GENERATOR] semester_subjects count: {len(semester_subjects)}")
        for s in semester_subjects:
            logger.info(f"[DEBUG GENERATOR] - subject: {s.name} ({s.id}), classes_per_week: {s.classes_per_week}")

        if not semester_subjects:
            raise ValueError("No subjects provided for scheduling")

        # Separate lab and theory subjects
        lab_subjects = [s for s in semester_subjects if s.is_lab()]
        # Treat ELECTIVE and CORE as theory subjects for scheduling
        theory_subjects = [s for s in semester_subjects if s.is_theory() or s.is_elective() or (not s.is_lab())]

        logger.info(f"[DEBUG GENERATOR] theory_subjects: {len(theory_subjects)}, lab_subjects: {len(lab_subjects)}")
        logger.info(f"[DEBUG GENERATOR] faculty_availability: {faculty_availability}")

        # Generate schedule for each section (using first section for now)
        section = sections[0] if sections else "A"
        schedule = await self._generate_schedule_for_section(
            semester=semester,
            section=section,
            theory_subjects=theory_subjects,
            lab_subjects=lab_subjects,
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map or {},
            faculty_names=faculty_names or {},
            occupied_slots=occupied_slots or []
        )

        return Timetable(
            id="",  # Will be set by repository
            semester=semester,
            section=section,
            version=1,
            is_active=True,
            schedule=schedule,
            created_by="system",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    async def _generate_schedule_for_section(
        self,
        semester: int,
        section: str,
        theory_subjects: List[Subject],
        lab_subjects: List[Subject],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        faculty_names: Dict[str, str] = None,
        occupied_slots: Optional[List[Dict[str, Any]]] = None
    ) -> List[DaySchedule]:
        """
        Generate schedule for a single section.

        Returns a list of DaySchedule with TimetableSlot objects.
        """
        import logging
        logger = logging.getLogger(__name__)
        faculty_names = faculty_names or {}
        self.last_conflicts = []

        # Validate that faculty have sufficient available slots before attempting
        validation_conflicts = self._collect_faculty_availability_conflicts(
            theory_subjects, lab_subjects, subject_faculty_map, faculty_availability, faculty_names
        )
        if validation_conflicts:
            self.last_conflicts = validation_conflicts
            error_message = self._format_conflict_summary(validation_conflicts)
            logger.error(f"[GENERATOR] {error_message}")
            raise ValueError(error_message)

        # Initialize timetable grid - day -> slot -> TimetableSlot
        timetable_grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]] = {
            day: {slot.slot_number: None for slot in self.time_slots}
            for day in self.WORKING_DAYS
        }

        # Track current-section slots separately from other sections. Other
        # sections block only the matching physical resource: theory uses the
        # semester classroom, labs use the lab room.
        occupied_slot_details_by_resource = self._occupied_slot_detail_maps(
            occupied_slots or [],
            faculty_names
        )
        assigned_slots = set()

        # Single attempt - stop at first conflict
        self.last_attempt_count = 1

        # Reset grid
        for day in self.WORKING_DAYS:
            for slot in self.time_slots:
                timetable_grid[day][slot.slot_number] = None
        occupied_slot_details_by_resource = self._occupied_slot_detail_maps(
            occupied_slots or [],
            faculty_names
        )
        assigned_slots = set()

        conflicts = []

        # Step 1: Reserve exactly one lunch break per working day before any
        # classes are placed, so the final timetable can never fill both
        # 12:20-13:10 and 13:10-14:00 on the same day.
        self._assign_lunch_breaks(timetable_grid, assigned_slots, faculty_availability)

        # Step 2: Assign labs (require 2 consecutive slots)
        lab_count = self._assign_labs_collecting_conflicts(
            lab_subjects, section, timetable_grid,
            faculty_availability, subject_faculty_map, assigned_slots,
            faculty_names, conflicts, occupied_slot_details_by_resource["lab_room"]
        )

        # Step 3: Assign theory classes
        theory_count = self._assign_theory_collecting_conflicts(
            theory_subjects, section, timetable_grid,
            faculty_availability, subject_faculty_map, assigned_slots,
            faculty_names, conflicts, occupied_slot_details_by_resource["classroom"]
        )

        if conflicts:
            self.last_conflicts = conflicts
            error_message = self._format_conflict_summary(conflicts)
            logger.error(f"[GENERATOR] {error_message}")
            raise ValueError(error_message)

        # Step 4: Convert grid to schedule and return
        return self._grid_to_schedule(timetable_grid)

    def _validate_faculty_availability(
        self,
        theory_subjects: List[Subject],
        lab_subjects: List[Subject],
        subject_faculty_map: Dict[str, str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        faculty_names: Dict[str, str] = None
    ) -> Optional[str]:
        """Validate that each faculty has sufficient available slots for their subjects.

        Returns only the FIRST error encountered, or None if no errors.
        """
        faculty_names = faculty_names or {}

        def _get_faculty_name(faculty_id: str) -> str:
            return faculty_names.get(faculty_id) or f"Faculty_{faculty_id[-4:]}"

        # Aggregate total slots needed per faculty across ALL their subjects
        faculty_total_needed: Dict[str, int] = defaultdict(int)
        faculty_subjects: Dict[str, List[Subject]] = defaultdict(list)

        # Check theory subjects and aggregate per faculty
        for subject in theory_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                return f"Conflict: No faculty assigned to subject: {subject.name}"

            faculty_total_needed[faculty_id] += subject.credits
            faculty_subjects[faculty_id].append(subject)

            avail = faculty_availability.get(faculty_id, {})
            total_slots = sum(len(slots) for slots in avail.values())

            if total_slots < subject.credits:
                faculty_name = _get_faculty_name(faculty_id)
                # Build slot detail showing available slots
                slot_details = []
                day_map = {DayOfWeek.MONDAY: "MON", DayOfWeek.TUESDAY: "TUE", DayOfWeek.WEDNESDAY: "WED",
                          DayOfWeek.THURSDAY: "THU", DayOfWeek.FRIDAY: "FRI"}
                for day, slots in avail.items():
                    day_str = day_map.get(day, str(day))
                    slot_details.append(f"{day_str}[{','.join(map(str, slots))}]")
                slots_str = ", ".join(slot_details) if slot_details else "None"
                return (
                    f"Conflict: Cannot schedule '{subject.name}' ({subject.code}). "
                    f"Faculty {faculty_name} has only {total_slots} available slot(s), "
                    f"but needs {subject.credits}. Available: {slots_str}. "
                    f"Please add more availability."
                )

        # Check lab subjects and aggregate per faculty
        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                return f"Conflict: No faculty assigned to lab subject: {subject.name}"

            faculty_total_needed[faculty_id] += 2  # Labs need 2 slots
            faculty_subjects[faculty_id].append(subject)

            avail = faculty_availability.get(faculty_id, {})
            # For labs, need consecutive slots - check each day
            has_consecutive = False
            for day_slots in avail.values():
                for i, slot in enumerate(day_slots[:-1]):
                    if slot + 1 in day_slots:
                        has_consecutive = True
                        break
                if has_consecutive:
                    break

            if not has_consecutive:
                faculty_name = _get_faculty_name(faculty_id)
                # Build slot detail showing available slots
                slot_details = []
                day_map = {DayOfWeek.MONDAY: "MON", DayOfWeek.TUESDAY: "TUE", DayOfWeek.WEDNESDAY: "WED",
                          DayOfWeek.THURSDAY: "THU", DayOfWeek.FRIDAY: "FRI"}
                for day, slots in avail.items():
                    day_str = day_map.get(day, str(day))
                    slot_details.append(f"{day_str}[{','.join(map(str, slots))}]")
                slots_str = ", ".join(slot_details) if slot_details else "None"
                return (
                    f"Conflict: Cannot schedule lab '{subject.name}' ({subject.code}). "
                    f"Faculty {faculty_name} has no 2 consecutive slots available. "
                    f"Available: {slots_str}. "
                    f"Labs require 2 consecutive periods (e.g., slots 1-2, 3-4, 7-8)."
                )

        # Validate TOTAL slots per faculty across all their subjects
        for faculty_id, total_needed in faculty_total_needed.items():
            avail = faculty_availability.get(faculty_id, {})
            total_available = sum(len(slots) for slots in avail.values())

            if total_available < total_needed:
                subject_names_list = [s.name for s in faculty_subjects[faculty_id]]
                faculty_name = _get_faculty_name(faculty_id)
                return (
                    f"Conflict: Faculty {faculty_name} teaching {', '.join(subject_names_list)} needs {total_needed} total slots, "
                    f"but only has {total_available} available slots. "
                    f"Please add {total_needed - total_available} more slots to this faculty's availability."
                )

        return None

    def _day_to_short_name(self, day: Any) -> str:
        """Convert internal day keys to compact labels used by the frontend."""
        day_map = {
            DayOfWeek.MONDAY: "MON",
            DayOfWeek.TUESDAY: "TUE",
            DayOfWeek.WEDNESDAY: "WED",
            DayOfWeek.THURSDAY: "THU",
            DayOfWeek.FRIDAY: "FRI",
            DayOfWeek.SATURDAY: "SAT",
            "MON": "MON",
            "TUE": "TUE",
            "WED": "WED",
            "THU": "THU",
            "FRI": "FRI",
            "SAT": "SAT",
        }
        return day_map.get(day, str(day))

    def _available_slots_payload(
        self,
        availability: Dict[Any, List[int]]
    ) -> List[Dict[str, Any]]:
        """Flatten availability into a JSON-friendly slot list."""
        slots = []
        for day, day_slots in availability.items():
            day_name = self._day_to_short_name(day)
            for slot in sorted(day_slots):
                slots.append({
                    "day": day_name,
                    "slot": slot,
                    "time": self._get_time_range_for_slot(slot)
                })
        return slots

    def _blocked_slots_payload(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        availability: Dict[Any, List[int]],
        faculty_names: Dict[str, str],
        occupied_slot_details: Optional[Dict[Tuple[DayOfWeek, int], Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Return available faculty slots currently occupied in the timetable grid."""
        blocked_slots = []
        subjects_by_id = {subject.id: subject for subject in self.subjects}
        occupied_slot_details = occupied_slot_details or {}
        seen = set()

        for day, day_slots in availability.items():
            grid_day = day
            if isinstance(day, str):
                grid_day = {
                    "MON": DayOfWeek.MONDAY,
                    "TUE": DayOfWeek.TUESDAY,
                    "WED": DayOfWeek.WEDNESDAY,
                    "THU": DayOfWeek.THURSDAY,
                    "FRI": DayOfWeek.FRIDAY,
                    "SAT": DayOfWeek.SATURDAY,
                }.get(day.upper(), day)

            day_grid = grid.get(grid_day, {})
            for slot in sorted(day_slots):
                existing = day_grid.get(slot)
                detail_key = (grid_day, slot)
                if detail_key in seen:
                    continue
                seen.add(detail_key)

                external_detail = occupied_slot_details.get(detail_key)
                if existing is None and external_detail:
                    blocked_slots.append(external_detail)
                    continue

                if existing is None:
                    continue

                subject = subjects_by_id.get(existing.subject_id)
                is_lunch = existing.is_lunch()
                blocked_slots.append({
                    "day": self._day_to_short_name(day),
                    "slot": slot,
                    "time": self._get_time_range_for_slot(slot),
                    "subject_id": existing.subject_id,
                    "subject_name": "Lunch Break" if is_lunch else (subject.name if subject else None),
                    "subject_code": "LUNCH" if is_lunch else (subject.code if subject else None),
                    "faculty_id": existing.faculty_id,
                    "faculty_name": (
                        "Lunch Break"
                        if is_lunch
                        else faculty_names.get(existing.faculty_id) or self._get_faculty_name_for_id(existing.faculty_id)
                    ),
                    "source": "current_attempt",
                    "source_label": "Current timetable attempt",
                })

        return blocked_slots

    def _occupied_slot_detail_map(
        self,
        occupied_slots: List[Dict[str, Any]],
        faculty_names: Optional[Dict[str, str]] = None
    ) -> Dict[Tuple[DayOfWeek, int], Dict[str, Any]]:
        """Convert external occupied slots into detailed blocker payloads."""
        faculty_names = faculty_names or {}
        subjects_by_id = {subject.id: subject for subject in self.subjects}
        details: Dict[Tuple[DayOfWeek, int], Dict[str, Any]] = {}

        for occupied in occupied_slots:
            day = self._normalize_day_value(occupied.get("day"))
            slot = occupied.get("slot")
            if day is None or slot is None:
                continue

            try:
                slot_number = int(slot)
            except (TypeError, ValueError):
                continue

            if day not in self.WORKING_DAYS or not 1 <= slot_number <= len(self.time_slots):
                continue

            subject_id = occupied.get("subject_id")
            faculty_id = occupied.get("faculty_id")
            subject = subjects_by_id.get(subject_id)
            subject_type = (
                occupied.get("subject_type")
                or (subject.subject_type.value if subject else None)
            )
            section = occupied.get("section")

            details[(day, slot_number)] = {
                "day": self._day_to_short_name(day),
                "slot": slot_number,
                "time": self._get_time_range_for_slot(slot_number),
                "section": section,
                "subject_id": subject_id,
                "subject_name": occupied.get("subject_name") or (subject.name if subject else None),
                "subject_code": occupied.get("subject_code") or (subject.code if subject else None),
                "subject_type": subject_type,
                "faculty_id": faculty_id,
                "faculty_name": (
                    occupied.get("faculty_name")
                    or faculty_names.get(faculty_id)
                    or (self._get_faculty_name_for_id(faculty_id) if faculty_id else None)
                ),
                "source": "same_semester_section",
                "source_label": f"Section {section}" if section else "Another section in this semester",
            }

        return details

    def _occupied_slot_detail_maps(
        self,
        occupied_slots: List[Dict[str, Any]],
        faculty_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[Tuple[DayOfWeek, int], Dict[str, Any]]]:
        """Group external occupied slots by physical resource."""
        details = self._occupied_slot_detail_map(occupied_slots, faculty_names)
        grouped = {
            "classroom": {},
            "lab_room": {},
        }

        for key, detail in details.items():
            if self._is_lab_subject_type(detail.get("subject_type")):
                detail["resource"] = "lab_room"
                detail["resource_label"] = "Lab room"
                grouped["lab_room"][key] = detail
            else:
                detail["resource"] = "classroom"
                detail["resource_label"] = "Classroom"
                grouped["classroom"][key] = detail

        return grouped

    def _is_lab_subject_type(self, subject_type: Any) -> bool:
        """Return whether a subject type value represents a lab."""
        value = getattr(subject_type, "value", subject_type)
        return str(value or "").lower() == SubjectType.LAB.value

    def _normalized_day_slots(
        self,
        availability: Dict[Any, List[int]]
    ) -> Dict[DayOfWeek, List[int]]:
        """Normalize availability keys to working-day enums."""
        normalized: Dict[DayOfWeek, List[int]] = {}
        for day in self.WORKING_DAYS:
            day_key = self._get_day_key(day)
            day_slots = availability.get(day)
            if day_slots is None:
                day_slots = availability.get(day_key, [])
            normalized[day] = sorted({
                int(slot)
                for slot in day_slots
                if 1 <= int(slot) <= len(self.time_slots)
            })
        return normalized

    def _normalize_day_value(self, day: Any) -> Optional[DayOfWeek]:
        """Normalize string/enum day values to DayOfWeek."""
        if isinstance(day, DayOfWeek):
            return day

        if isinstance(day, str):
            value = day.upper()
            short_map = {
                "MON": DayOfWeek.MONDAY,
                "TUE": DayOfWeek.TUESDAY,
                "WED": DayOfWeek.WEDNESDAY,
                "THU": DayOfWeek.THURSDAY,
                "FRI": DayOfWeek.FRIDAY,
                "SAT": DayOfWeek.SATURDAY,
                "SUN": DayOfWeek.SUNDAY,
            }
            if value in short_map:
                return short_map[value]
            for day_enum in DayOfWeek:
                if day_enum.value.upper() == value:
                    return day_enum

        return None

    def _occupied_slot_set(
        self,
        occupied_slots: List[Dict[str, Any]]
    ) -> set:
        """Convert external occupied slot payloads into day-slot pairs."""
        blocked = set()
        for occupied in occupied_slots:
            day = self._normalize_day_value(occupied.get("day"))
            slot = occupied.get("slot")
            if day is None or slot is None:
                continue

            try:
                slot_number = int(slot)
            except (TypeError, ValueError):
                continue

            if day in self.WORKING_DAYS and 1 <= slot_number <= len(self.time_slots):
                blocked.add((day, slot_number))

        return blocked

    def _lab_consecutive_pairs(
        self,
        availability: Dict[Any, List[int]]
    ) -> List[Tuple[DayOfWeek, int]]:
        """Return same-day consecutive pairs from explicit faculty availability."""
        pairs = []
        for day, day_slots in self._normalized_day_slots(availability).items():
            slot_set = set(day_slots)
            for slot in day_slots:
                if slot < len(self.time_slots) and slot + 1 in slot_set:
                    pairs.append((day, slot))
        return pairs

    def _consecutive_pairs_payload(
        self,
        availability: Dict[Any, List[int]]
    ) -> List[Dict[str, Any]]:
        """Return JSON-friendly lab pair details for conflict responses."""
        return [
            {
                "day": self._day_to_short_name(day),
                "start_slot": slot,
                "end_slot": slot + 1,
                "start_time": self._get_time_range_for_slot(slot),
                "end_time": self._get_time_range_for_slot(slot + 1),
            }
            for day, slot in self._lab_consecutive_pairs(availability)
        ]

    def _usable_consecutive_pairs_payload(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        availability: Dict[Any, List[int]],
        assigned_slots: set,
        external_blocked_slots: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Return lab pairs that are both available and currently free."""
        external_blocked_slots = external_blocked_slots or set()
        usable_pairs = []
        for day, slot in self._lab_consecutive_pairs(availability):
            next_slot = slot + 1
            if (
                grid[day][slot] is None
                and grid[day][next_slot] is None
                and (day, slot) not in assigned_slots
                and (day, next_slot) not in assigned_slots
                and (day, slot) not in external_blocked_slots
                and (day, next_slot) not in external_blocked_slots
            ):
                usable_pairs.append({
                    "day": self._day_to_short_name(day),
                    "start_slot": slot,
                    "end_slot": next_slot,
                    "start_time": self._get_time_range_for_slot(slot),
                    "end_time": self._get_time_range_for_slot(next_slot),
                })

        return usable_pairs

    def _format_availability_for_message(
        self,
        availability: Dict[Any, List[int]]
    ) -> str:
        """Return compact availability text such as MON[1,2], TUE[4]."""
        parts = []
        for day, day_slots in availability.items():
            day_name = self._day_to_short_name(day)
            parts.append(f"{day_name}[{','.join(map(str, sorted(day_slots)))}]")
        return ", ".join(parts) if parts else "None"

    def _has_consecutive_slots(self, availability: Dict[Any, List[int]]) -> bool:
        """Check if availability contains any pair of consecutive slots."""
        return bool(self._lab_consecutive_pairs(availability))

    def _subject_required_slots(self, subject: Subject, is_lab: bool = False) -> int:
        """Return how many timetable slots this subject needs."""
        return 2 if is_lab else subject.credits

    def _availability_slot_pairs(
        self,
        availability: Dict[Any, List[int]]
    ) -> List[Tuple[DayOfWeek, int]]:
        """Return normalized day-slot pairs for a faculty availability map."""
        pairs = []
        for day, day_slots in self._normalized_day_slots(availability).items():
            for slot in day_slots:
                pairs.append((day, slot))
        return pairs

    def _theory_subject_sort_key(
        self,
        subject: Subject,
        subject_faculty_map: Dict[str, str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]]
    ) -> Tuple[int, int, int, str]:
        """Sort theory subjects from most constrained to most flexible."""
        faculty_id = subject_faculty_map.get(subject.id)
        available_count = len(self._availability_slot_pairs(faculty_availability.get(faculty_id, {})))
        slack = available_count - subject.credits
        return (slack, available_count, -subject.credits, subject.code or subject.name)

    def _build_slot_contention(
        self,
        theory_subjects: List[Subject],
        subject_faculty_map: Dict[str, str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]]
    ) -> Dict[Tuple[DayOfWeek, int], int]:
        """Count how many theory assignments can use each slot."""
        contention: Dict[Tuple[DayOfWeek, int], int] = defaultdict(int)

        for subject in theory_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            availability = faculty_availability.get(faculty_id, {})
            for pair in set(self._availability_slot_pairs(availability)):
                contention[pair] += 1

        return contention

    def _build_generation_conflict(
        self,
        conflict_type: str,
        subject: Optional[Subject],
        faculty_id: Optional[str],
        faculty_name: str,
        issue: str,
        recommendation: str,
        required_slots: Optional[int] = None,
        scheduled_slots: int = 0,
        missing_slots: Optional[int] = None,
        availability: Optional[Dict[Any, List[int]]] = None,
        available_consecutive_pairs: Optional[List[Dict[str, Any]]] = None,
        assigned_slots: Optional[List[Dict[str, Any]]] = None,
        blocked_slots: Optional[List[Dict[str, Any]]] = None,
        suggestions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build a structured conflict for the API response."""
        available_slots = self._available_slots_payload(availability or {})
        available_count = len(available_slots)

        return {
            "type": conflict_type,
            "subject_id": subject.id if subject else None,
            "subject_name": subject.name if subject else None,
            "subject_code": subject.code if subject else None,
            "faculty_id": faculty_id,
            "faculty_name": faculty_name,
            "issue": issue,
            "recommendation": recommendation,
            "required_slots": required_slots,
            "scheduled_slots": scheduled_slots,
            "missing_slots": missing_slots,
            "available_slot_count": available_count,
            "available_slots": available_slots,
            "available_consecutive_pairs": available_consecutive_pairs or [],
            "assigned_slots": assigned_slots or [],
            "blocked_slots": blocked_slots or [],
            "suggestions": suggestions or [recommendation],
        }

    def _collect_faculty_availability_conflicts(
        self,
        theory_subjects: List[Subject],
        lab_subjects: List[Subject],
        subject_faculty_map: Dict[str, str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        faculty_names: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """Collect all pre-generation availability blockers."""
        faculty_names = faculty_names or {}
        conflicts = []

        def _get_faculty_name(faculty_id: Optional[str]) -> str:
            if not faculty_id:
                return "Not assigned"
            return faculty_names.get(faculty_id) or f"Faculty_{faculty_id[-4:]}"

        faculty_total_needed: Dict[str, int] = defaultdict(int)
        faculty_subjects: Dict[str, List[Subject]] = defaultdict(list)

        for subject in theory_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                conflicts.append(self._build_generation_conflict(
                    conflict_type="missing_faculty",
                    subject=subject,
                    faculty_id=None,
                    faculty_name="Not assigned",
                    issue="No faculty is assigned to this subject.",
                    recommendation="Assign a faculty member to this subject before generating the timetable.",
                    required_slots=subject.credits,
                    missing_slots=subject.credits,
                    suggestions=[
                        "Open Faculty Assignments and assign a faculty member to this subject.",
                        "Regenerate the timetable after the assignment is saved."
                    ]
                ))
                continue

            faculty_total_needed[faculty_id] += subject.credits
            faculty_subjects[faculty_id].append(subject)

            availability = faculty_availability.get(faculty_id, {})
            total_slots = sum(len(slots) for slots in availability.values())
            if total_slots < subject.credits:
                shortage = subject.credits - total_slots
                conflicts.append(self._build_generation_conflict(
                    conflict_type="insufficient_subject_availability",
                    subject=subject,
                    faculty_id=faculty_id,
                    faculty_name=_get_faculty_name(faculty_id),
                    issue=(
                        f"{_get_faculty_name(faculty_id)} has {total_slots} available slot(s), "
                        f"but {subject.name} needs {subject.credits}."
                    ),
                    recommendation=f"Add at least {shortage} more available slot(s) for this faculty and subject.",
                    required_slots=subject.credits,
                    scheduled_slots=total_slots,
                    missing_slots=shortage,
                    availability=availability,
                    suggestions=[
                        f"Add at least {shortage} more available slot(s) for {_get_faculty_name(faculty_id)}.",
                        "If the faculty cannot add slots, reassign this subject to another faculty member.",
                        "Regenerate the timetable after updating availability or assignments."
                    ]
                ))

        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                conflicts.append(self._build_generation_conflict(
                    conflict_type="missing_faculty",
                    subject=subject,
                    faculty_id=None,
                    faculty_name="Not assigned",
                    issue="No faculty is assigned to this lab subject.",
                    recommendation="Assign a faculty member to this lab before generating the timetable.",
                    required_slots=2,
                    missing_slots=2
                ))
                continue

            faculty_total_needed[faculty_id] += 2
            faculty_subjects[faculty_id].append(subject)

            availability = faculty_availability.get(faculty_id, {})
            consecutive_pairs = self._consecutive_pairs_payload(availability)
            if not consecutive_pairs:
                conflicts.append(self._build_generation_conflict(
                    conflict_type="missing_consecutive_slots",
                    subject=subject,
                    faculty_id=faculty_id,
                    faculty_name=_get_faculty_name(faculty_id),
                    issue=(
                        f"{_get_faculty_name(faculty_id)} has available slots, "
                        "but none of them form a same-day consecutive pair for this lab."
                    ),
                    recommendation="Add at least one same-day consecutive pair such as slots 1-2, 3-4, or 7-8.",
                    required_slots=2,
                    missing_slots=2,
                    availability=availability,
                    available_consecutive_pairs=consecutive_pairs,
                    suggestions=[
                        "Add one pair of consecutive slots on the same day.",
                        "Use an admin override only if the faculty can actually teach during that pair.",
                        "Regenerate the timetable after updating availability."
                    ]
                ))

        for faculty_id, total_needed in faculty_total_needed.items():
            availability = faculty_availability.get(faculty_id, {})
            total_available = sum(len(slots) for slots in availability.values())
            if total_available < total_needed:
                faculty_name = _get_faculty_name(faculty_id)
                subject_names = ", ".join(subject.name for subject in faculty_subjects[faculty_id])
                shortage = total_needed - total_available
                conflicts.append(self._build_generation_conflict(
                    conflict_type="faculty_total_shortage",
                    subject=None,
                    faculty_id=faculty_id,
                    faculty_name=faculty_name,
                    issue=(
                        f"{faculty_name} needs {total_needed} total slot(s) for {subject_names}, "
                        f"but only has {total_available} available."
                    ),
                    recommendation=f"Add at least {shortage} more available slot(s), or reassign one subject.",
                    required_slots=total_needed,
                    scheduled_slots=total_available,
                    missing_slots=shortage,
                    availability=availability,
                    suggestions=[
                        f"Add at least {shortage} more available slot(s) for {faculty_name}.",
                        "If that is not possible, move one assigned subject to another faculty member.",
                        "Regenerate the timetable after resolving the faculty workload shortage."
                    ]
                ))

        return conflicts

    def _format_conflict_summary(self, conflicts: List[Dict[str, Any]]) -> str:
        """Create a readable fallback message for clients that do not use structured conflicts."""
        if not conflicts:
            return "Conflict: Timetable generation failed."

        lines = [
            f"Conflict: Timetable generation blocked by {len(conflicts)} issue(s)."
        ]
        for index, conflict in enumerate(conflicts, 1):
            subject = conflict.get("subject_name") or "Multiple subjects"
            subject_code = conflict.get("subject_code")
            if subject_code:
                subject = f"{subject} ({subject_code})"
            faculty = conflict.get("faculty_name") or "Faculty"
            lines.append(f"{index}. {subject} - {faculty}: {conflict.get('issue')}")
            available = conflict.get("available_slots") or []
            consecutive_pairs = conflict.get("available_consecutive_pairs") or []
            assigned = conflict.get("assigned_slots") or []
            blocked = conflict.get("blocked_slots") or []
            if available:
                available_text = ", ".join(
                    f"{slot.get('day')}-{slot.get('slot')} ({slot.get('time')})"
                    for slot in available[:10]
                )
                lines.append(f"   Available: {available_text}")
            if "lab" in str(conflict.get("type", "")).lower() or "consecutive" in str(conflict.get("type", "")).lower():
                if consecutive_pairs:
                    pairs_text = ", ".join(
                        f"{pair.get('day')}-{pair.get('start_slot')}-{pair.get('end_slot')}"
                        for pair in consecutive_pairs[:10]
                    )
                    lines.append(f"   Usable lab pairs: {pairs_text}")
                else:
                    lines.append("   Usable lab pairs: None. Labs need two available consecutive slots on the same day.")
            if assigned:
                assigned_text = ", ".join(
                    f"{slot.get('day')}-{slot.get('slot')} ({slot.get('time')})"
                    for slot in assigned[:10]
                )
                lines.append(f"   Already assigned: {assigned_text}")
            if blocked:
                blocked_text = ", ".join(
                    f"{slot.get('day')}-{slot.get('slot')} ({slot.get('subject_code') or slot.get('subject_name') or 'occupied'})"
                    for slot in blocked[:10]
                )
                lines.append(f"   Blocked by current attempt: {blocked_text}")
        return "\n".join(lines)

    def _get_generation_error_details(
        self,
        theory_subjects: List[Subject],
        lab_subjects: List[Subject],
        subject_faculty_map: Dict[str, str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]]
    ) -> str:
        """Get detailed error information for failed generation."""
        details = []

        for subject in theory_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            avail = faculty_availability.get(faculty_id, {})
            total_slots = sum(len(slots) for slots in avail.values())
            details.append(f"'{subject.name}': {total_slots} slots available, needs {subject.credits}")

        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            avail = faculty_availability.get(faculty_id, {})
            total_slots = sum(len(slots) for slots in avail.values())
            details.append(f"'{subject.name}' (lab): {total_slots} slots available, needs 2 consecutive")

        return "Subject availability: " + "; ".join(details) + "."

    def _analyze_conflicts(
        self,
        theory_subjects: List[Subject],
        lab_subjects: List[Subject],
        subject_faculty_map: Dict[str, str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        max_attempts: int,
        assignment_failures: Dict[str, int] = None,
        best_lab_count: int = 0,
        best_theory_count: int = 0
    ) -> ConflictReport:
        """
        Analyze conflicts in detail when timetable generation fails.

        Returns a comprehensive ConflictReport organized by time slots:
        - For each time slot (day + time), shows which faculty are available
        - For each faculty, shows what subjects they teach
        - Highlights slots where multiple faculty are competing
        """
        slot_conflicts: List[SlotConflict] = []
        faculty_conflicts: List[FacultyConflict] = []
        subject_conflicts: List[SubjectConflict] = []
        suggestions: List[str] = []

        if assignment_failures is None:
            assignment_failures = {}

        # Calculate totals
        total_required_slots = len(lab_subjects) * 2 + sum(s.credits for s in theory_subjects)
        total_assigned = best_lab_count + best_theory_count
        total_missing = total_required_slots - total_assigned

        # Map faculty to their assigned subjects
        faculty_to_subjects: Dict[str, List[Subject]] = defaultdict(list)
        for subject in theory_subjects + lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if faculty_id:
                faculty_to_subjects[faculty_id].append(subject)

        # Get day names in order
        day_names = {
            DayOfWeek.MONDAY: "MON",
            DayOfWeek.TUESDAY: "TUE",
            DayOfWeek.WEDNESDAY: "WED",
            DayOfWeek.THURSDAY: "THU",
            DayOfWeek.FRIDAY: "FRI"
        }

        # Build slot-wise conflict report
        # For each time slot, show which faculty are available and their subjects
        for slot_info in self.TIME_SLOTS:
            slot_num, start_time, end_time = slot_info

            # Skip lunch slots from main analysis (show them separately)
            if slot_num in self.LUNCH_SLOTS:
                continue

            time_range = f"{start_time} - {end_time}"

            # Find all faculty available at this slot across all days
            for day in self.WORKING_DAYS:
                day_name = day_names.get(day, day.value)

                # Find faculty available at this (day, slot)
                available_faculty = []

                for faculty_id, avail in faculty_availability.items():
                    # Check if faculty is available at this day and slot
                    day_slots = avail.get(day) or avail.get(day_name, [])
                    if slot_num in day_slots:
                        # Get subjects taught by this faculty
                        subjects_taught = faculty_to_subjects.get(faculty_id, [])

                        available_faculty.append({
                            "faculty_id": faculty_id,
                            "faculty_name": self._get_faculty_name_for_id(faculty_id),
                            "subjects": [
                                {
                                    "subject_id": s.id,
                                    "subject_code": s.code,
                                    "subject_name": s.name,
                                    "subject_type": "LAB" if s in lab_subjects else "THEORY",
                                    "required_slots": s.credits if s in theory_subjects else 2
                                }
                                for s in subjects_taught
                            ]
                        })

                # Only create a conflict entry if there are multiple faculty competing
                # OR if this is a key slot with any faculty availability
                if len(available_faculty) >= 1:
                    conflict_type = "MULTIPLE_FACULTY" if len(available_faculty) > 1 else "SINGLE_FACULTY"

                    # Build description
                    if len(available_faculty) > 1:
                        subject_list = []
                        for fac in available_faculty:
                            for subj in fac['subjects']:
                                subject_list.append(f"{subj['subject_code']} ({subj['subject_type']})")
                        description = f"{len(available_faculty)} faculty available: {', '.join([f['faculty_name'] for f in available_faculty])}. Subjects: {', '.join(subject_list)}"
                    else:
                        fac = available_faculty[0]
                        subject_list = [f"{s['subject_code']}" for s in fac['subjects']]
                        description = f"Faculty {fac['faculty_name']} available for: {', '.join(subject_list)}"

                    slot_conflicts.append(SlotConflict(
                        day=day_name,
                        slot_number=slot_num,
                        time_range=time_range,
                        competing_faculty=[
                            {"faculty_id": f["faculty_id"], "faculty_name": f["faculty_name"]}
                            for f in available_faculty
                        ],
                        competing_subjects=[
                            {"subject_id": s["subject_id"], "subject_code": s["subject_code"], "subject_name": s["subject_name"]}
                            for f in available_faculty
                            for s in f["subjects"]
                        ],
                        conflict_type=conflict_type,
                        description=description
                    ))

        # Add summary about the generation attempt
        if total_missing > 0:
            suggestions.append(
                f"The algorithm attempted {max_attempts:,} times but could only schedule "
                f"{total_assigned} out of {total_required_slots} required slots."
            )
            suggestions.append(f"Missing: {total_missing} slots")

        # Count unique faculty and subjects for summary
        unique_faculty = len(faculty_to_subjects)
        unique_subjects = len(theory_subjects) + len(lab_subjects)

        suggestions.append(f"Analysis based on {unique_faculty} faculty teaching {unique_subjects} subjects.")
        suggestions.append("Review each time slot below to see faculty availability and subject assignments.")
        suggestions.append("To resolve conflicts, consider adjusting faculty availability or reassigning subjects to different faculty.")

        # Build summary
        summary_parts = []
        summary_parts.append(f"{len(slot_conflicts)} time slot(s) analyzed")
        if total_missing > 0:
            summary_parts.append(f"{total_missing} slots could not be scheduled")

        summary = ", ".join(summary_parts) if summary_parts else "Timetable generation analysis complete"

        return ConflictReport(
            total_attempts=max_attempts,
            summary=summary,
            slot_conflicts=slot_conflicts,
            faculty_conflicts=[],  # Not using faculty_conflicts in slot-wise view
            subject_conflicts=[],  # Not using subject_conflicts in slot-wise view
            suggestions=suggestions
        )

    def _get_faculty_name_for_id(self, faculty_id: str) -> str:
        """Get a display name for faculty ID."""
        return f"Faculty_{faculty_id[-4:]}" if len(faculty_id) > 4 else f"Faculty_{faculty_id}"

    def _get_time_range_for_slot(self, slot_number: int) -> str:
        """Get time range for a slot number."""
        if 1 <= slot_number <= len(self.TIME_SLOTS):
            return f"{self.TIME_SLOTS[slot_number - 1][1]} - {self.TIME_SLOTS[slot_number - 1][2]}"
        return f"Slot {slot_number}"

    def _assign_labs(
        self,
        lab_subjects: List[Subject],
        section: str,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        assigned_slots: set,
        faculty_names: Dict[str, str] = None
    ) -> int:
        """Assign lab subjects requiring 2 consecutive slots. Raises ValueError on first failure."""
        count = 0
        faculty_names = faculty_names or {}
        day_map = {DayOfWeek.MONDAY: "MON", DayOfWeek.TUESDAY: "TUE", DayOfWeek.WEDNESDAY: "WED",
                   DayOfWeek.THURSDAY: "THU", DayOfWeek.FRIDAY: "FRI"}

        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            faculty_name = faculty_names.get(faculty_id) or self._get_faculty_name_for_id(faculty_id) if faculty_id else "Unknown"
            # Find available consecutive slots
            avail = faculty_availability.get(faculty_id, {})
            available = self._find_consecutive_slots(
                grid, avail, subject, section, assigned_slots
            )

            if not available:
                # Show faculty's available slots to explain the conflict
                slot_details = []
                for day, slots in avail.items():
                    day_str = day_map.get(day, str(day))
                    slot_details.append(f"{day_str}[{','.join(map(str, slots))}]")
                slots_str = ", ".join(slot_details) if slot_details else "None"
                raise ValueError(
                    f"Conflict: Cannot schedule lab '{subject.name}' ({subject.code}). "
                    f"Faculty {faculty_name} has no 2 consecutive available slots. "
                    f"Available slots: {slots_str}. "
                    f"Labs require 2 consecutive periods (e.g., slots 1-2, 3-4, 7-8)."
                )

            day, slot1 = available
            slot2 = slot1 + 1

            # Create slots for both positions
            grid[day][slot1] = TimetableSlot(
                slot=slot1,
                subject_id=subject.id,
                faculty_id=faculty_id,
                room=None
            )
            grid[day][slot2] = TimetableSlot(
                slot=slot2,
                subject_id=subject.id,
                faculty_id=faculty_id,
                room=None
            )

            assigned_slots.add((day, slot1))
            assigned_slots.add((day, slot2))
            count += 2

        return count

    def _assign_labs_collecting_conflicts(
        self,
        lab_subjects: List[Subject],
        section: str,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        assigned_slots: set,
        faculty_names: Dict[str, str],
        conflicts: List[Dict[str, Any]],
        occupied_slot_details: Optional[Dict[Tuple[DayOfWeek, int], Dict[str, Any]]] = None
    ) -> int:
        """Assign labs and collect every lab that cannot be placed."""
        count = 0
        occupied_slot_details = occupied_slot_details or {}

        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            faculty_name = (
                faculty_names.get(faculty_id)
                or self._get_faculty_name_for_id(faculty_id)
                if faculty_id else "Unknown"
            )
            availability = faculty_availability.get(faculty_id, {})
            available = self._find_consecutive_slots(
                grid,
                availability,
                subject,
                section,
                assigned_slots,
                set(occupied_slot_details.keys())
            )

            if not available:
                consecutive_pairs = self._consecutive_pairs_payload(availability)
                usable_pairs = self._usable_consecutive_pairs_payload(
                    grid,
                    availability,
                    assigned_slots,
                    set(occupied_slot_details.keys())
                )
                blocked_slots = self._blocked_slots_payload(
                    grid,
                    availability,
                    faculty_names,
                    occupied_slot_details
                )
                section_blockers = [
                    slot for slot in blocked_slots
                    if slot.get("source") == "same_semester_section"
                ]
                conflict_type = "missing_consecutive_slots" if not consecutive_pairs else "lab_scheduling_conflict"
                if not consecutive_pairs:
                    issue = f"{faculty_name} has available slots, but none form a same-day consecutive pair for this lab."
                    recommendation = "Add two consecutive slots on the same day for this faculty."
                    suggestions = [
                        "Add or override a same-day pair such as slots 1-2, 3-4, or 7-8.",
                        "Regenerate the timetable after saving the new lab pair."
                    ]
                elif section_blockers:
                    blocked_sections = sorted({
                        slot.get("section")
                        for slot in section_blockers
                        if slot.get("section")
                    })
                    section_text = (
                        f"Section {', '.join(blocked_sections)}"
                        if blocked_sections
                        else "another section in this semester"
                    )
                    issue = (
                        f"{faculty_name} has consecutive lab availability, but the available pair is already "
                        f"occupied by {section_text} in the lab room. A lab can overlap with another section's "
                        "theory class, but it cannot overlap with another lab using the same lab room."
                    )
                    recommendation = (
                        "Choose a consecutive pair where the lab room is free, or regenerate/move the other lab first."
                    )
                    suggestions = [
                        "Open the occupied candidate slots below to see which section is using the pair.",
                        "Add another same-day consecutive lab pair that is not used by another lab.",
                        "If both sections must be regenerated, use bulk generation so the scheduler can plan them together."
                    ]
                else:
                    issue = (
                        f"{faculty_name} has consecutive availability, but those pairs are already reserved by lunch "
                        "or another class in this timetable attempt."
                    )
                    recommendation = "Move the blocking class/lunch choice or add another same-day consecutive pair."
                    suggestions = [
                        "Review the occupied candidate slots below.",
                        "Add another same-day consecutive pair such as slots 1-2, 3-4, or 7-8.",
                        "Regenerate the timetable after resolving the lab slot pair."
                    ]

                conflicts.append(self._build_generation_conflict(
                    conflict_type=conflict_type,
                    subject=subject,
                    faculty_id=faculty_id,
                    faculty_name=faculty_name,
                    issue=issue,
                    recommendation=recommendation,
                    required_slots=2,
                    scheduled_slots=0,
                    missing_slots=2,
                    availability=availability,
                    available_consecutive_pairs=consecutive_pairs,
                    blocked_slots=blocked_slots,
                    suggestions=suggestions
                ))
                conflicts[-1]["usable_consecutive_pairs"] = usable_pairs
                continue

            day, slot1 = available
            slot2 = slot1 + 1

            grid[day][slot1] = TimetableSlot(
                slot=slot1,
                subject_id=subject.id,
                faculty_id=faculty_id,
                room=None
            )
            grid[day][slot2] = TimetableSlot(
                slot=slot2,
                subject_id=subject.id,
                faculty_id=faculty_id,
                room=None
            )

            assigned_slots.add((day, slot1))
            assigned_slots.add((day, slot2))
            count += 2

        return count

    def _assign_theory(
        self,
        theory_subjects: List[Subject],
        section: str,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        assigned_slots: set,
        faculty_names: Dict[str, str] = None
    ) -> int:
        """Assign theory subjects based on credits. Raises ValueError on first failure."""
        count = 0
        faculty_names = faculty_names or {}
        day_map = {DayOfWeek.MONDAY: "MON", DayOfWeek.TUESDAY: "TUE", DayOfWeek.WEDNESDAY: "WED",
                   DayOfWeek.THURSDAY: "THU", DayOfWeek.FRIDAY: "FRI"}

        for subject in theory_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            faculty_name = faculty_names.get(faculty_id) or self._get_faculty_name_for_id(faculty_id) if faculty_id else "Unknown"
            assigned_for_subject = 0
            assigned_slot_details = []

            for i in range(subject.credits):
                # Find available slot
                available = self._find_available_slot(
                    grid, faculty_availability.get(faculty_id, {}),
                    subject, section, assigned_slots
                )

                if not available:
                    # Build details of already assigned slots for this subject
                    already_assigned = ", ".join(assigned_slot_details) if assigned_slot_details else "None"
                    # Show faculty's remaining availability
                    avail = faculty_availability.get(faculty_id, {})
                    slot_details = []
                    for day, slots in avail.items():
                        day_str = day_map.get(day, str(day))
                        slot_details.append(f"{day_str}[{','.join(map(str, slots))}]")
                    slots_str = ", ".join(slot_details) if slot_details else "None"
                    raise ValueError(
                        f"Conflict: Cannot schedule '{subject.name}' ({subject.code}) - slot {assigned_for_subject + 1}/{subject.credits}. "
                        f"Faculty {faculty_name} has no available slots for this session. "
                        f"Already assigned: {already_assigned}. "
                        f"Faculty availability: {slots_str}."
                    )

                day, slot = available
                day_str = day_map.get(day, str(day))
                time_range = self._get_time_range_for_slot(slot)
                assigned_slot_details.append(f"{day_str}-{slot} ({time_range})")

                grid[day][slot] = TimetableSlot(
                    slot=slot,
                    subject_id=subject.id,
                    faculty_id=faculty_id,
                    room=None
                )

                assigned_slots.add((day, slot))
                count += 1
                assigned_for_subject += 1

        return count

    def _assign_theory_collecting_conflicts(
        self,
        theory_subjects: List[Subject],
        section: str,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        assigned_slots: set,
        faculty_names: Dict[str, str],
        conflicts: List[Dict[str, Any]],
        occupied_slot_details: Optional[Dict[Tuple[DayOfWeek, int], Dict[str, Any]]] = None
    ) -> int:
        """Assign theory subjects and collect every subject that cannot be fully placed."""
        count = 0
        occupied_slot_details = occupied_slot_details or {}
        ordered_subjects = sorted(
            theory_subjects,
            key=lambda subject: self._theory_subject_sort_key(subject, subject_faculty_map, faculty_availability)
        )
        slot_contention = self._build_slot_contention(
            ordered_subjects,
            subject_faculty_map,
            faculty_availability
        )

        for subject in ordered_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            faculty_name = (
                faculty_names.get(faculty_id)
                or self._get_faculty_name_for_id(faculty_id)
                if faculty_id else "Unknown"
            )
            assigned_for_subject = 0
            assigned_slot_details = []
            availability = faculty_availability.get(faculty_id, {})

            for _ in range(subject.credits):
                available = self._find_available_slot(
                    grid,
                    availability,
                    subject,
                    section,
                    assigned_slots,
                    slot_contention,
                    set(occupied_slot_details.keys())
                )

                if not available:
                    missing_slots = subject.credits - assigned_for_subject
                    conflicts.append(self._build_generation_conflict(
                        conflict_type="theory_scheduling_conflict",
                        subject=subject,
                        faculty_id=faculty_id,
                        faculty_name=faculty_name,
                        issue=(
                            f"{subject.name} still needs {missing_slots} slot(s), "
                            f"but no usable slot remains for {faculty_name}."
                        ),
                        recommendation="Add more availability for this faculty or reassign the subject.",
                        required_slots=subject.credits,
                        scheduled_slots=assigned_for_subject,
                        missing_slots=missing_slots,
                        availability=availability,
                        assigned_slots=assigned_slot_details,
                        blocked_slots=self._blocked_slots_payload(
                            grid,
                            availability,
                            faculty_names,
                            occupied_slot_details
                        ),
                        suggestions=[
                            f"Add at least {missing_slots} more available slot(s) for {faculty_name}.",
                            "Prefer spreading the new slots across different days to give the generator more choices.",
                            "If availability cannot be expanded, reassign the subject to another faculty member."
                        ]
                    ))
                    break

                day, slot = available
                day_name = self._day_to_short_name(day)
                assigned_slot_details.append({
                    "day": day_name,
                    "slot": slot,
                    "time": self._get_time_range_for_slot(slot)
                })

                grid[day][slot] = TimetableSlot(
                    slot=slot,
                    subject_id=subject.id,
                    faculty_id=faculty_id,
                    room=None
                )

                assigned_slots.add((day, slot))
                count += 1
                assigned_for_subject += 1

        return count

    def _assign_labs_with_tracking(
        self,
        lab_subjects: List[Subject],
        section: str,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        assigned_slots: set
    ) -> Dict[str, Any]:
        """Assign lab subjects requiring 2 consecutive slots. Returns dict with assigned count and failures."""
        count = 0
        failures = defaultdict(int)

        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            # Find available consecutive slots
            available = self._find_consecutive_slots(
                grid, faculty_availability.get(faculty_id, {}),
                subject, section, assigned_slots
            )

            if available:
                day, slot1 = available
                slot2 = slot1 + 1

                # Create slots for both positions
                grid[day][slot1] = TimetableSlot(
                    slot=slot1,
                    subject_id=subject.id,
                    faculty_id=faculty_id,
                    room=None
                )
                grid[day][slot2] = TimetableSlot(
                    slot=slot2,
                    subject_id=subject.id,
                    faculty_id=faculty_id,
                    room=None
                )

                assigned_slots.add((day, slot1))
                assigned_slots.add((day, slot2))
                count += 2
            else:
                failures[subject.id] += 1

        return {"assigned": count, "failures": dict(failures)}

    def _assign_theory_with_tracking(
        self,
        theory_subjects: List[Subject],
        section: str,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        subject_faculty_map: Dict[str, str],
        assigned_slots: set
    ) -> Dict[str, Any]:
        """Assign theory subjects based on credits. Returns dict with assigned count and failures."""
        count = 0
        failures = defaultdict(int)

        for subject in theory_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            assigned_for_subject = 0

            for i in range(subject.credits):
                # Find available slot
                available = self._find_available_slot(
                    grid, faculty_availability.get(faculty_id, {}),
                    subject, section, assigned_slots
                )

                if available:
                    day, slot = available

                    grid[day][slot] = TimetableSlot(
                        slot=slot,
                        subject_id=subject.id,
                        faculty_id=faculty_id,
                        room=None
                    )

                    assigned_slots.add((day, slot))
                    count += 1
                    assigned_for_subject += 1
                else:
                    failures[subject.id] += 1

        return {"assigned": count, "failures": dict(failures)}

    def _assign_lunch_breaks(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        assigned_slots: set,
        faculty_availability: Optional[Dict[str, Dict[DayOfWeek, List[int]]]] = None
    ) -> None:
        """Reserve exactly one lunch break for each working day."""
        faculty_availability = faculty_availability or {}

        for day in self.WORKING_DAYS:
            lunch_slot = self._choose_lunch_slot(day, faculty_availability)
            grid[day][lunch_slot] = TimetableSlot(
                slot=lunch_slot,
                subject_id=None,
                faculty_id=None,
                room="LUNCH"
            )
            assigned_slots.add((day, lunch_slot))

    def _choose_lunch_slot(
        self,
        day: DayOfWeek,
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]]
    ) -> int:
        """
        Choose which lunch-window slot to reserve for the day.

        The slot with lower faculty availability demand is reserved as lunch,
        keeping the more useful slot available for classes. Ties prefer slot 5.
        """
        demand = {slot: 0 for slot in self.LUNCH_SLOTS}
        day_key = self._get_day_key(day)

        for availability in faculty_availability.values():
            day_slots = availability.get(day)
            if day_slots is None:
                day_slots = availability.get(day_key, [])

            for slot in self.LUNCH_SLOTS:
                if slot in day_slots:
                    demand[slot] += 1

        return min(self.LUNCH_SLOTS, key=lambda slot: (demand[slot], slot))

    def _find_consecutive_slots(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        availability: Dict[DayOfWeek, List[int]],
        subject: Subject,
        section: str,
        assigned_slots: Optional[set] = None,
        external_blocked_slots: Optional[set] = None
    ) -> Optional[Tuple[DayOfWeek, int]]:
        """Find 2 consecutive explicitly available slots for a lab."""
        import logging
        logger = logging.getLogger(__name__)
        assigned_slots = assigned_slots or set()
        external_blocked_slots = external_blocked_slots or set()

        candidate_pairs = self._lab_consecutive_pairs(availability)
        non_lunch_pairs = [
            pair for pair in candidate_pairs
            if pair[1] not in self.LUNCH_SLOTS and pair[1] + 1 not in self.LUNCH_SLOTS
        ]
        lunch_pairs = [
            pair for pair in candidate_pairs
            if pair not in non_lunch_pairs
        ]

        for day, slot_num in non_lunch_pairs + lunch_pairs:
            if (
                grid[day][slot_num] is None
                and grid[day][slot_num + 1] is None
                and (day, slot_num) not in assigned_slots
                and (day, slot_num + 1) not in assigned_slots
                and (day, slot_num) not in external_blocked_slots
                and (day, slot_num + 1) not in external_blocked_slots
            ):
                logger.info(f"[DEBUG LAB] Found available consecutive slots: {day} slots {slot_num}-{slot_num + 1}")
                return (day, slot_num)

        return None

    def _get_day_key(self, day: DayOfWeek) -> str:
        """Convert DayOfWeek enum to string key used in availability dict."""
        day_map = {
            DayOfWeek.MONDAY: "MON",
            DayOfWeek.TUESDAY: "TUE",
            DayOfWeek.WEDNESDAY: "WED",
            DayOfWeek.THURSDAY: "THU",
            DayOfWeek.FRIDAY: "FRI",
            DayOfWeek.SATURDAY: "SAT",
            DayOfWeek.SUNDAY: "SUN"
        }
        return day_map.get(day, day.value)

    def _find_available_slot(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        availability: Dict[DayOfWeek, List[int]],
        subject: Subject,
        section: str,
        assigned_slots: set,
        slot_contention: Optional[Dict[Tuple[DayOfWeek, int], int]] = None,
        external_blocked_slots: Optional[set] = None
    ) -> Optional[Tuple[DayOfWeek, int]]:
        """Find an available slot for a theory class.

        Strategy:
        1. First try to find non-lunch slots
        2. Prefer less-contested slots so flexible subjects do not consume scarce slots
        3. If no non-lunch slots found in faculty's availability, use lunch slots
        """
        import logging
        logger = logging.getLogger(__name__)
        external_blocked_slots = external_blocked_slots or set()

        # Collect all available slots from faculty's availability
        all_available_slots = []
        for day in self.WORKING_DAYS:
            if not availability:
                # If no specific availability, use all non-lunch slots
                day_slots = [s.slot_number for s in self.time_slots
                             if s.slot_number not in self.LUNCH_SLOTS]
            else:
                # Try both enum key and string key
                day_key = self._get_day_key(day)
                day_slots = availability.get(day) or availability.get(day_key, [])

            for slot_num in day_slots:
                all_available_slots.append((day, slot_num))

        # Separate non-lunch and lunch slots
        non_lunch_slots = [(d, s) for d, s in all_available_slots if s not in self.LUNCH_SLOTS]
        lunch_slots = [(d, s) for d, s in all_available_slots if s in self.LUNCH_SLOTS]

        logger.info(f"[DEBUG FIND_SLOT] Subject: {subject.name}, Non-lush slots: {len(non_lunch_slots)}, Lunch slots: {len(lunch_slots)}")

        def _slot_priority(pair: Tuple[DayOfWeek, int]) -> Tuple[int, int, int]:
            day, slot_num = pair
            day_index = self.WORKING_DAYS.index(day) if day in self.WORKING_DAYS else 99
            contention = slot_contention.get(pair, 0) if slot_contention else 0
            return (contention, day_index, slot_num)

        if slot_contention:
            non_lunch_slots.sort(key=_slot_priority)
            lunch_slots.sort(key=_slot_priority)
        else:
            self.rng.shuffle(non_lunch_slots)
            self.rng.shuffle(lunch_slots)

        # Try non-lunch slots first.
        for day, slot_num in non_lunch_slots:
            if (grid[day][slot_num] is None and
                (day, slot_num) not in assigned_slots and
                (day, slot_num) not in external_blocked_slots):
                logger.info(f"[DEBUG FIND_SLOT] Found non-lunch slot: {day} slot {slot_num}")
                return (day, slot_num)

        # No non-lunch slots available - try lunch slots
        for day, slot_num in lunch_slots:
            if (grid[day][slot_num] is None and
                (day, slot_num) not in assigned_slots and
                (day, slot_num) not in external_blocked_slots):
                logger.info(f"[DEBUG FIND_SLOT] Found lunch slot (faculty only has lunch available): {day} slot {slot_num}")
                return (day, slot_num)

        logger.warning(f"[DEBUG FIND_SLOT] No available slots found for {subject.name}")
        return None

    def _grid_to_schedule(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]]
    ) -> List[DaySchedule]:
        """Convert the grid to a list of DaySchedule objects.

        Only ONE lunch break per day - either slot 5 or slot 6, not both.
        """
        schedule = []

        for day in self.WORKING_DAYS:
            slots = []
            existing_lunch_slot = next(
                (
                    slot_num
                    for slot_num in self.LUNCH_SLOTS
                    if grid[day][slot_num] is not None
                    and grid[day][slot_num].is_lunch()
                ),
                None
            )

            # Determine which lunch slot to mark as LUNCH
            # Priority: if one slot has a class, mark the other as LUNCH
            # If both are free, prefer slot 5
            lunch_slot_to_mark = existing_lunch_slot
            if lunch_slot_to_mark is None:
                slot_5_has_class = (
                    grid[day][5] is not None
                    and not grid[day][5].is_lunch()
                )
                slot_6_has_class = (
                    grid[day][6] is not None
                    and not grid[day][6].is_lunch()
                )

                if slot_5_has_class and not slot_6_has_class:
                    lunch_slot_to_mark = 6  # Slot 5 has class, so slot 6 is lunch
                elif slot_6_has_class and not slot_5_has_class:
                    lunch_slot_to_mark = 5  # Slot 6 has class, so slot 5 is lunch
                elif not slot_5_has_class and not slot_6_has_class:
                    lunch_slot_to_mark = 5  # Both free, prefer slot 5 as lunch
                # If both have classes in old data, no lunch break can be inferred.

            for slot_num in range(1, 11):
                slot = grid[day][slot_num]
                if slot is None:
                    # Check if this is the designated lunch slot for this day
                    if slot_num == lunch_slot_to_mark:
                        # Mark as lunch break using room="LUNCH"
                        slots.append(TimetableSlot(
                            slot=slot_num,
                            subject_id=None,
                            faculty_id=None,
                            room="LUNCH"
                        ))
                    else:
                        # Create empty slot
                        slots.append(TimetableSlot(
                            slot=slot_num,
                            subject_id=None,
                            faculty_id=None,
                            room=None
                        ))
                else:
                    slots.append(slot)

            schedule.append(DaySchedule(day=day, slots=slots))

        return schedule
