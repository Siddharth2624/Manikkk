"""Timetable domain entity - redesigned for single document per semester-section."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class DayOfWeek(str, Enum):
    """Days of the week."""
    MONDAY = "MON"
    TUESDAY = "TUE"
    WEDNESDAY = "WED"
    THURSDAY = "THU"
    FRIDAY = "FRI"
    SATURDAY = "SAT"
    SUNDAY = "SUN"


class SlotType(str, Enum):
    """Type of time slot."""
    THEORY = "theory"
    LAB = "lab"
    LUNCH_BREAK = "lunch_break"
    FREE = "free"


@dataclass
class TimetableSlot:
    """
    Single time slot entry.

    Only stores references (IDs), not denormalized names.
    """
    slot: int                    # 1-10
    subject_id: Optional[str] = None
    faculty_id: Optional[str] = None
    room: Optional[str] = None

    def is_free(self) -> bool:
        """Check if this is a free slot."""
        return self.subject_id is None

    def is_lunch(self) -> bool:
        """Check if this is lunch break."""
        return self.subject_id is None and self.room == "LUNCH"


@dataclass
class DaySchedule:
    """
    Schedule for one day of the week.
    """
    day: DayOfWeek
    slots: List[TimetableSlot] = field(default_factory=list)

    def get_slot(self, slot_number: int) -> Optional[TimetableSlot]:
        """Get slot by number."""
        for slot in self.slots:
            if slot.slot == slot_number:
                return slot
        return None

    def set_slot(self, slot_number: int, slot: TimetableSlot) -> None:
        """Set or replace a slot."""
        # Remove existing slot at this position
        self.slots = [s for s in self.slots if s.slot != slot_number]
        self.slots.append(slot)
        self.slots.sort(key=lambda s: s.slot)


@dataclass
class Timetable:
    """
    Complete timetable for a semester-section combination.

    ONE document per semester-section.
    Supports versioning with is_active flag.
    """
    id: str
    semester: int
    section: str
    version: int
    is_active: bool
    schedule: List[DaySchedule]
    created_by: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate timetable data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")
        if self.version < 1:
            raise ValueError("Version must be at least 1")

    def get_entry(self, day: DayOfWeek, slot_number: int) -> Optional[TimetableSlot]:
        """Get slot for specific day and slot number."""
        for day_schedule in self.schedule:
            if day_schedule.day == day:
                return day_schedule.get_slot(slot_number)
        return None

    def get_weekly_schedule(self) -> Dict[DayOfWeek, Dict[int, TimetableSlot]]:
        """Get complete weekly schedule as nested dict."""
        result = {}
        for day_schedule in self.schedule:
            result[day_schedule.day] = {
                slot.slot: slot for slot in day_schedule.slots
            }
        return result

    def get_faculty_slots(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Get all slots assigned to a faculty member."""
        result = []
        for day_schedule in self.schedule:
            for slot in day_schedule.slots:
                if slot.faculty_id == faculty_id:
                    result.append({
                        "day": day_schedule.day.value,
                        "slot": slot.slot,
                        "subject_id": slot.subject_id,
                        "room": slot.room
                    })
        return result

    def get_subject_slots(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all slots for a subject."""
        result = []
        for day_schedule in self.schedule:
            for slot in day_schedule.slots:
                if slot.subject_id == subject_id:
                    result.append({
                        "day": day_schedule.day.value,
                        "slot": slot.slot,
                        "faculty_id": slot.faculty_id,
                        "room": slot.room
                    })
        return result

    def get_free_slots(self) -> List[Dict[str, Any]]:
        """Get all free slots."""
        result = []
        for day_schedule in self.schedule:
            for slot in day_schedule.slots:
                if slot.is_free():
                    result.append({
                        "day": day_schedule.day.value,
                        "slot": slot.slot
                    })
        return result

    def to_matrix(self) -> Dict[str, Any]:
        """Convert to matrix representation for UI rendering."""
        time_slots = [
            (i, f"{9 + i//2}:{'00' if i % 2 == 0 else '30'}")
            for i in range(1, 11)
        ]

        matrix = []
        for slot_num, time_range in time_slots:
            row = {"time": time_range, "slots": []}
            for day in DayOfWeek:
                slot = self.get_entry(day, slot_num)
                if slot and not slot.is_free():
                    row["slots"].append({
                        "slot": slot.slot,
                        "subject_id": slot.subject_id,
                        "faculty_id": slot.faculty_id,
                        "room": slot.room
                    })
                else:
                    row["slots"].append({"type": "free"})
            matrix.append(row)

        return {
            "semester": self.semester,
            "section": self.section,
            "matrix": matrix
        }


@dataclass
class TimeSlot:
    """Time slot configuration (metadata, not actual schedule)."""
    slot_number: int
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"

    def __str__(self) -> str:
        return f"{self.start_time} - {self.end_time}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_number": self.slot_number,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "display": str(self)
        }