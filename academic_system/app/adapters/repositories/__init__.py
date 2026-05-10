"""Repository implementations - MongoDB adapters."""

from .user_repository import UserRepository
from .semester_repository import SemesterRepository
from .subject_repository import SubjectRepository
from .timetable_repository import TimetableRepository
from .attendance_repository import AttendanceRepository
from .study_material_repository import StudyMaterialRepository
from .subject_assignment_repository import SubjectAssignmentRepository
from .faculty_availability_repository import FacultyAvailabilityRepository
from .admin_override_repository import AdminOverrideRepository

__all__ = [
    "UserRepository",
    "SemesterRepository",
    "SubjectRepository",
    "TimetableRepository",
    "AttendanceRepository",
    "StudyMaterialRepository",
    "SubjectAssignmentRepository",
    "FacultyAvailabilityRepository",
    "AdminOverrideRepository",
]
