"""Domain layer - core business logic and entities."""

from .exceptions import AuthorizationError, ResourceNotFoundError, ValidationError

from .entities import (
    User, UserRole, StudentProfile, FacultyProfile,
    Semester, SemesterStatus,
    Subject, SubjectType,
    Timetable, TimetableSlot, DaySchedule, DayOfWeek, SlotType, TimeSlot,
    AttendanceRecord, AttendanceSummary, AttendanceStatus,
    StudyMaterial, MaterialType,
    SubjectAssignment
)

from .interfaces import (
    IUserRepository,
    ISemesterRepository,
    ISubjectRepository,
    ITimetableRepository,
    IAttendanceRepository,
    IStudyMaterialRepository,
    ITimetableGenerator,
    IFileStorageService
)

__all__ = [
    # Exceptions
    "AuthorizationError", "ResourceNotFoundError", "ValidationError",
    # Entities
    "User", "UserRole", "StudentProfile", "FacultyProfile",
    "Semester", "SemesterStatus",
    "Subject", "SubjectType",
    "Timetable", "TimetableSlot", "DaySchedule", "DayOfWeek", "SlotType", "TimeSlot",
    "AttendanceRecord", "AttendanceSummary", "AttendanceStatus",
    "StudyMaterial", "MaterialType",
    "SubjectAssignment",
    # Interfaces
    "IUserRepository",
    "ISemesterRepository",
    "ISubjectRepository",
    "ITimetableRepository",
    "IAttendanceRepository",
    "IStudyMaterialRepository",
    "ITimetableGenerator",
    "IFileStorageService",
]
