"""Subject assignment domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SubjectAssignment:
    """
    Links a subject to a semester-section-faculty combination.

    Replaces the denormalized sections array in Subject entity.
    Supports multiple faculty per subject through multiple assignments.

    Attributes:
        id: Unique assignment identifier
        subject_id: ID of the subject
        semester: Semester number (1-8)
        section: Section identifier (e.g., "A", "B")
        faculty_id: ID of the faculty member
        is_primary: Whether this is the primary faculty (for multi-faculty scenarios)
        created_at: Creation timestamp
    """
    id: str
    subject_id: str
    semester: int
    section: str
    faculty_id: str
    is_primary: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate subject assignment data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")

    def is_for_semester(self, semester: int) -> bool:
        """Check if assignment is for given semester."""
        return self.semester == semester

    def is_for_section(self, section: str) -> bool:
        """Check if assignment is for given section."""
        return self.section == section
