"""Subject domain entity - simplified (removed sections and faculty_id)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SubjectType(str, Enum):
    """Type of subject."""
    THEORY = "theory"
    LAB = "lab"
    ELECTIVE = "elective"
    CORE = "core"


@dataclass
class Subject:
    """
    Subject entity representing a course/subject.

    Removed: sections array (moved to subject_assignments)
    Removed: faculty_id (moved to subject_assignments)

    Attributes:
        id: Unique subject identifier
        code: Subject code (e.g., "CS101")
        name: Subject name
        semester: Semester number (1-8) - for catalog organization
        subject_type: Type of subject
        credits: Number of credits
        classes_per_week: Number of classes per week
        description: Subject description
        syllabus: Subject syllabus/topics
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    code: str
    name: str
    semester: int  # Kept for catalog organization, NOT for assignment
    subject_type: SubjectType
    credits: int
    classes_per_week: int
    description: Optional[str] = None
    syllabus: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate subject data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not 1 <= self.credits <= 6:
            raise ValueError("Credits must be between 1 and 6")
        if not 1 <= self.classes_per_week <= 10:
            raise ValueError("Classes per week must be between 1 and 10")

    def is_lab(self) -> bool:
        """Check if this is a lab subject."""
        return self.subject_type == SubjectType.LAB

    def is_theory(self) -> bool:
        """Check if this is a theory subject."""
        return self.subject_type == SubjectType.THEORY

    def is_elective(self) -> bool:
        """Check if this is an elective subject."""
        return self.subject_type == SubjectType.ELECTIVE

    def get_weekly_hours(self) -> int:
        """Get total weekly teaching hours."""
        if self.is_lab():
            return self.classes_per_week * 2
        return self.classes_per_week

    def get_display_name(self) -> str:
        """Get display name for the subject."""
        return f"{self.code} - {self.name}"