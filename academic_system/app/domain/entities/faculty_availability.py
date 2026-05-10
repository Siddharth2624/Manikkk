"""Faculty availability domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum


class DayOfWeek(str, Enum):
    """Days of the week for availability slots."""
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"


@dataclass
class AvailableSlot:
    """Single available time slot."""
    day: DayOfWeek
    slot: int  # 1-10

    def __post_init__(self):
        if not 1 <= self.slot <= 10:
            raise ValueError("Slot must be between 1 and 10")


@dataclass
class FacultyAvailability:
    """
    Faculty availability for a specific subject assignment.

    One record per (faculty_id, subject_id, semester, section).
    """
    id: Optional[str]
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    available_slots: List[AvailableSlot]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "faculty_id": self.faculty_id,
            "subject_id": self.subject_id,
            "semester": self.semester,
            "section": self.section,
            "available_slots": [
                {"day": s.day.value, "slot": s.slot} for s in self.available_slots
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
