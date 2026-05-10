"""Semester domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SemesterStatus(str, Enum):
    """Semester status."""
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


@dataclass
class Semester:
    """
    Semester entity representing an academic semester.

    Attributes:
        id: Unique semester identifier
        semester_number: Semester number (1-8)
        branch: Branch/department (e.g., "CSE", "ECE")
        status: Current status of the semester
        start_date: Semester start date
        end_date: Semester end date
        sections: List of sections in this semester
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    semester_number: int
    branch: str
    status: SemesterStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sections: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate semester data."""
        if not 1 <= self.semester_number <= 8:
            raise ValueError("Semester number must be between 1 and 8")

    def add_section(self, section: str) -> None:
        """Add a section to this semester."""
        if section not in self.sections:
            self.sections.append(section)
            self.updated_at = datetime.utcnow()

    def remove_section(self, section: str) -> None:
        """Remove a section from this semester."""
        if section in self.sections:
            self.sections.remove(section)
            self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if semester is currently active."""
        if self.status != SemesterStatus.ONGOING:
            return False
        if self.start_date and self.end_date:
            now = datetime.utcnow()
            return self.start_date <= now <= self.end_date
        return True

    def get_display_name(self) -> str:
        """Get display name for the semester."""
        return f"Semester {self.semester_number} - {self.branch}"
