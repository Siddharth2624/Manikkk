"""Repository interfaces (ports) - define contracts without implementation."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from app.domain.entities.user import User, UserRole
from app.domain.entities.semester import Semester, SemesterStatus
from app.domain.entities.subject import Subject, SubjectType
from app.domain.entities.timetable import Timetable, DayOfWeek
from app.domain.entities.attendance import AttendanceRecord, AttendanceSummary
from app.domain.entities.study_material import StudyMaterial
from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.entities.admin_override_log import AdminOverrideLog, OverrideType


class IUserRepository(ABC):
    """Port: User repository interface."""

    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID."""
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        pass

    @abstractmethod
    async def find_by_roll_number(self, roll_number: str) -> Optional[User]:
        """Find student by roll number."""
        pass

    @abstractmethod
    async def find_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Find faculty by employee ID."""
        pass

    @abstractmethod
    async def find_all(
        self,
        role: Optional[UserRole] = None,
        semester: Optional[int] = None,
        section: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[User]:
        """Find users with optional filters."""
        pass

    @abstractmethod
    async def count(self, role: Optional[UserRole] = None) -> int:
        """Count users by role."""
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        """Save or update user."""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user by ID."""
        pass

    @abstractmethod
    async def exists(self, email: str) -> bool:
        """Check if user exists by email."""
        pass


class ISemesterRepository(ABC):
    """Port: Semester repository interface."""

    @abstractmethod
    async def find_by_id(self, semester_id: str) -> Optional[Semester]:
        """Find semester by ID."""
        pass

    @abstractmethod
    async def find_all(
        self,
        status: Optional[SemesterStatus] = None,
        branch: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Semester]:
        """Find all semesters with optional filters."""
        pass

    @abstractmethod
    async def get_active_semester(self) -> Optional[Semester]:
        """Get currently active semester."""
        pass

    @abstractmethod
    async def save(self, semester: Semester) -> Semester:
        """Save or update semester."""
        pass

    @abstractmethod
    async def delete(self, semester_id: str) -> bool:
        """Delete semester by ID."""
        pass


class ISubjectRepository(ABC):
    """Port: Subject repository interface."""

    @abstractmethod
    async def find_by_id(self, subject_id: str) -> Optional[Subject]:
        """Find subject by ID."""
        pass

    @abstractmethod
    async def find_by_code(self, code: str) -> Optional[Subject]:
        """Find subject by code."""
        pass

    @abstractmethod
    async def find_all(
        self,
        semester: Optional[int] = None,
        subject_type: Optional[SubjectType] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Subject]:
        """Find subjects with optional filters."""
        pass

    @abstractmethod
    async def save(self, subject: Subject) -> Subject:
        """Save or update subject."""
        pass

    @abstractmethod
    async def delete(self, subject_id: str) -> bool:
        """Delete subject by ID."""
        pass


class ISubjectAssignmentRepository(ABC):
    """Repository for subject assignment operations."""

    @abstractmethod
    async def save(self, assignment: SubjectAssignment) -> SubjectAssignment:
        """Save or update subject assignment."""
        pass

    @abstractmethod
    async def find_by_id(self, assignment_id: str) -> Optional[SubjectAssignment]:
        """Find assignment by ID."""
        pass

    @abstractmethod
    async def find_faculty_assignment(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str
    ) -> Optional[SubjectAssignment]:
        """Find if faculty is assigned to specific subject/semester/section."""
        pass

    @abstractmethod
    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a semester and section."""
        pass

    @abstractmethod
    async def find_by_faculty(
        self,
        faculty_id: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a faculty member."""
        pass

    @abstractmethod
    async def find_by_subject(
        self,
        subject_id: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a subject."""
        pass

    @abstractmethod
    async def delete(self, assignment_id: str) -> bool:
        """Delete assignment by ID."""
        pass

    @abstractmethod
    async def find_all(
        self,
        semester: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """Find all assignments with optional filters."""
        pass

    @abstractmethod
    async def find_by_faculty_and_semester(
        self,
        faculty_id: str,
        semester: int
    ) -> List[SubjectAssignment]:
        """Find all assignments for a faculty member in a specific semester."""
        pass


class ITimetableRepository(ABC):
    """Port: Timetable repository interface - redesigned for single-document schema."""

    @abstractmethod
    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str
    ) -> Optional[Timetable]:
        """Find active timetable by semester and section."""
        pass

    @abstractmethod
    async def find_by_faculty(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Find all timetable entries for a faculty (aggregation result)."""
        pass

    @abstractmethod
    async def save(self, timetable: Timetable) -> Timetable:
        """Save or update timetable (creates new version)."""
        pass

    @abstractmethod
    async def delete_by_semester_and_section(
        self,
        semester: int,
        section: str
    ) -> int:
        """Delete all timetables for a semester and section. Returns count."""
        pass

    @abstractmethod
    async def find_conflicts(
        self,
        semester: int,
        section: str,
        day: DayOfWeek,
        slot: int
    ) -> List[Dict[str, Any]]:
        """Find conflicting entries at the same day and slot."""
        pass


class IAttendanceRepository(ABC):
    """Port: Attendance repository interface."""

    @abstractmethod
    async def save(self, attendance: AttendanceRecord) -> AttendanceRecord:
        """Save or update attendance record."""
        pass

    @abstractmethod
    async def save_batch(self, attendances: List[AttendanceRecord]) -> bool:
        """Save multiple attendance records."""
        pass

    @abstractmethod
    async def find_by_student_and_subject(
        self,
        student_id: str,
        subject_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AttendanceRecord]:
        """Find attendance records for a student in a subject."""
        pass

    @abstractmethod
    async def find_by_subject_and_date(
        self,
        subject_id: str,
        attendance_date: date
    ) -> List[AttendanceRecord]:
        """Find all attendance records for a subject on a date."""
        pass

    @abstractmethod
    async def get_summary(
        self,
        student_id: str,
        subject_id: str
    ) -> Optional[AttendanceSummary]:
        """Get attendance summary for a student in a subject."""
        pass

    @abstractmethod
    async def get_all_summaries(
        self,
        student_id: str
    ) -> List[AttendanceSummary]:
        """Get attendance summaries for all subjects of a student."""
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        subject_id: str,
        start_date: date,
        end_date: date
    ) -> List[AttendanceRecord]:
        """Find attendance records within a date range."""
        pass

    @abstractmethod
    async def delete(self, attendance_id: str) -> bool:
        """Delete attendance record."""
        pass


class IStudyMaterialRepository(ABC):
    """Port: Study material repository interface."""

    @abstractmethod
    async def find_by_id(self, material_id: str) -> Optional[StudyMaterial]:
        """Find study material by ID."""
        pass

    @abstractmethod
    async def find_by_subject(
        self,
        subject_id: str,
        semester: Optional[int] = None,
        section: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> List[StudyMaterial]:
        """Find study materials for a subject."""
        pass

    @abstractmethod
    async def find_by_faculty(self, faculty_id: str) -> List[StudyMaterial]:
        """Find study materials uploaded by a faculty."""
        pass

    @abstractmethod
    async def find_by_semester(
        self,
        semester: int,
        section: Optional[str] = None
    ) -> List[StudyMaterial]:
        """Find study materials for a semester."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        semester: Optional[int] = None,
        section: Optional[str] = None,
        faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[StudyMaterial]:
        """Search study materials by title, description, or tags."""
        pass

    @abstractmethod
    async def save(self, material: StudyMaterial) -> StudyMaterial:
        """Save or update study material."""
        pass

    @abstractmethod
    async def delete(self, material_id: str) -> bool:
        """Delete study material by ID."""
        pass

    @abstractmethod
    async def increment_download_count(self, material_id: str) -> bool:
        """Increment download count for material."""
        pass


class IFacultyAvailabilityRepository(ABC):
    """Repository for faculty availability records."""

    @abstractmethod
    async def save(self, availability: FacultyAvailability) -> FacultyAvailability:
        """Save or update availability record."""
        pass

    @abstractmethod
    async def find(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str
    ) -> Optional[FacultyAvailability]:
        """Find availability by unique key."""
        pass

    @abstractmethod
    async def find_by_faculty(
        self, faculty_id: str
    ) -> List[FacultyAvailability]:
        """Find all availability for a faculty member."""
        pass

    @abstractmethod
    async def find_by_faculty_and_subject(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str
    ) -> Optional[FacultyAvailability]:
        """Find availability for a specific faculty subject assignment."""
        pass

    @abstractmethod
    async def update(self, availability: FacultyAvailability) -> FacultyAvailability:
        """Update existing availability record."""
        pass

    @abstractmethod
    async def delete(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str
    ) -> bool:
        """Delete availability record."""
        pass

    @abstractmethod
    async def find_by_semester_and_section(
        self, semester: int, section: str
    ) -> List[FacultyAvailability]:
        """Find all availability records for a semester and section (across all faculty)."""
        pass


class IAdminOverrideRepository(ABC):
    """Repository for admin override logs."""

    @abstractmethod
    async def save(self, override: AdminOverrideLog) -> AdminOverrideLog:
        """Save override log entry."""
        pass

    @abstractmethod
    async def find_by_id(self, override_id: str) -> Optional[AdminOverrideLog]:
        """Find override by ID."""
        pass

    @abstractmethod
    async def find_applicable(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str
    ) -> List[AdminOverrideLog]:
        """Find all applicable overrides (persistent + unapplied one-time)."""
        pass

    @abstractmethod
    async def find_audit_log(
        self, faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None
    ) -> List[AdminOverrideLog]:
        """Find overrides for audit log view."""
        pass

    @abstractmethod
    async def mark_one_time_applied(
        self, semester: int, section: str
    ) -> int:
        """Mark one-time overrides as applied after timetable generation."""
        pass

    @abstractmethod
    async def delete(self, override_id: str) -> bool:
        """Delete override by ID."""
        pass
