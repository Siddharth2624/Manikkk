"""Admin override log domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

from app.domain.entities.faculty_availability import DayOfWeek


class OverrideType(str, Enum):
    """Type of override."""
    PERSISTENT = "persistent"
    ONE_TIME = "one_time"


class OverrideAction(str, Enum):
    """Action for a slot override."""
    ADD = "add"      # Force include
    REMOVE = "remove" # Force exclude


@dataclass
class OverrideSlot:
    """Single slot in an override."""
    day: DayOfWeek
    slot: int
    action: OverrideAction

    def __post_init__(self):
        if not 1 <= self.slot <= 10:
            raise ValueError("Slot must be between 1 and 10")

    def to_dict(self) -> dict:
        return {"day": self.day.value, "slot": self.slot, "action": self.action.value}


@dataclass
class AdminOverrideLog:
    """
    Audit log for admin availability overrides.

    Stores ALL overrides (persistent and one-time).
    Does NOT modify faculty_availability directly.
    """
    id: Optional[str]
    admin_id: str
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    override_type: OverrideType
    applied: bool  # True if used in generation (one-time only)
    slots: List[OverrideSlot]
    timestamp: datetime

    def __post_init__(self):
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "faculty_id": self.faculty_id,
            "subject_id": self.subject_id,
            "semester": self.semester,
            "section": self.section,
            "override_type": self.override_type.value,
            "applied": self.applied,
            "slots": [s.to_dict() for s in self.slots],
            "timestamp": self.timestamp.isoformat()
        }
