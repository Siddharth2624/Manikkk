"""Study material domain entity."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class MaterialType(str, Enum):
    """Type of study material."""
    LINK = "link"
    PDF = "pdf"
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    VIDEO = "video"
    ARCHIVE = "archive"
    OTHER = "other"


@dataclass
class StudyMaterial:
    """
    Study material uploaded by faculty.

    Attributes:
        id: Unique material identifier
        title: Title of the material
        description: Description of the material
        subject_id: ID of the subject
        semester: Semester number (1-8)
        sections: List of sections this material is for (empty = all sections)
        faculty_id: ID of the faculty who uploaded
        material_url: External material link, such as Google Drive
        material_date: Class/material date for day-wise records
        access_count: Number of times opened
        tags: Tags for categorization
        is_public: Whether material is publicly accessible
        created_at: Creation timestamp
        updated_at: Last update timestamp
        material_type: Type of material
    """
    id: str
    title: str
    description: Optional[str]
    subject_id: str
    semester: int
    sections: List[str]
    faculty_id: str
    material_url: str
    material_date: date
    access_count: int
    tags: List[str]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    material_type: MaterialType = MaterialType.LINK

    def __post_init__(self):
        """Validate study material data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.material_url:
            raise ValueError("Material URL is required")

    def is_visible_to(self, student_semester: int, student_section: str) -> bool:
        """
        Check if material is visible to a student.

        Args:
            student_semester: Student's semester
            student_section: Student's section
        """
        if not self.is_public:
            return False
        if self.semester != student_semester:
            return False
        if self.sections and student_section not in self.sections:
            return False
        return True

    def increment_access_count(self) -> None:
        """Increment the access count."""
        self.access_count += 1
        self.updated_at = datetime.utcnow()

    def increment_download_count(self) -> None:
        """Backward-compatible alias for older repository interface naming."""
        self.increment_access_count()

    def add_tag(self, tag: str) -> None:
        """Add a tag to the material."""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the material."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()
