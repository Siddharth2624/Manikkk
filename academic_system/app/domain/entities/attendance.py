"""Attendance domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class AttendanceStatus(str, Enum):
    """Attendance status.

    New attendance marking only supports PRESENT and ABSENT. EXCUSED is kept so
    older records can still be read safely.
    """
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"


@dataclass
class AttendanceRecord:
    """
    Single attendance record for a student in a subject.

    Attributes:
        id: Unique record identifier
        student_id: ID of the student
        subject_id: ID of the subject
        faculty_id: ID of the faculty who marked attendance
        date: Date of attendance
        status: Attendance status (present, absent, excused)
        remarks: Additional remarks
        marked_at: When attendance was marked
        updated_at: Last update timestamp
    """
    id: str
    student_id: str
    subject_id: str
    faculty_id: str
    date: date
    status: AttendanceStatus
    remarks: Optional[str] = None
    marked_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_present(self) -> bool:
        """Check if student was present."""
        return self.status == AttendanceStatus.PRESENT

    def is_absent(self) -> bool:
        """Check if student was absent."""
        return self.status == AttendanceStatus.ABSENT

    def is_excused(self) -> bool:
        """Check if absence was excused."""
        return self.status == AttendanceStatus.EXCUSED

    def mark_present(self, faculty_id: str) -> None:
        """Mark student as present."""
        self.status = AttendanceStatus.PRESENT
        self.faculty_id = faculty_id
        self.updated_at = datetime.utcnow()

    def mark_absent(self, faculty_id: str, remarks: Optional[str] = None) -> None:
        """Mark student as absent."""
        self.status = AttendanceStatus.ABSENT
        self.faculty_id = faculty_id
        self.remarks = remarks
        self.updated_at = datetime.utcnow()

    def mark_excused(self, faculty_id: str, remarks: Optional[str] = None) -> None:
        """Mark student as excused."""
        self.status = AttendanceStatus.EXCUSED
        self.faculty_id = faculty_id
        self.remarks = remarks
        self.updated_at = datetime.utcnow()


@dataclass
class AttendanceSummary:
    """
    Attendance summary for a student in a subject.

    Attributes:
        student_id: ID of the student
        subject_id: ID of the subject
        total_classes: Total number of classes held
        present_count: Number of classes attended
        absent_count: Number of classes missed
        excused_count: Number of excused absences
        percentage: Attendance percentage
        is_below_threshold: Whether attendance is below 75%
    """
    student_id: str
    subject_id: str
    total_classes: int
    present_count: int
    absent_count: int
    excused_count: int
    percentage: float
    is_below_threshold: bool

    @classmethod
    def from_records(
        cls,
        student_id: str,
        subject_id: str,
        records: List[AttendanceRecord]
    ) -> "AttendanceSummary":
        """Create summary from attendance records."""
        total = len(records)
        present = sum(1 for r in records if r.is_present())
        absent = sum(1 for r in records if r.is_absent())
        excused = sum(1 for r in records if r.is_excused())

        # Legacy excused records are treated as absent in the two-status model.
        absent += excused
        excused = 0
        percentage = (present / total * 100) if total > 0 else 0.0

        return cls(
            student_id=student_id,
            subject_id=subject_id,
            total_classes=total,
            present_count=present,
            absent_count=absent,
            excused_count=excused,
            percentage=round(percentage, 2),
            is_below_threshold=percentage < 75.0
        )

    def get_status(self) -> str:
        """Get attendance status message."""
        if self.is_below_threshold:
            return f"Low attendance ({self.percentage}%)"
        return f"Good ({self.percentage}%)"
