"""Domain entities - core business objects."""

from .user import User, UserRole, StudentProfile, FacultyProfile
from .semester import Semester, SemesterStatus
from .subject import Subject, SubjectType
from .timetable import (
    Timetable,
    TimetableSlot,
    DaySchedule,
    DayOfWeek,
    SlotType,
    TimeSlot
)
from .attendance import (
    AttendanceRecord,
    AttendanceSummary,
    AttendanceStatus
)
from .study_material import StudyMaterial, MaterialType
from .subject_assignment import SubjectAssignment
from .request_context import RequestContext
from .feasibility import (
    FeasibilityStatus,
    Recoverability,
    ConstraintSeverity,
    RiskLevel,
    SuggestionType,
    SuggestionPriority,
    ConstraintScore,
    LocalWarning,
    GlobalWarning,
    WarningCollection,
    Suggestion,
    FeasibilityTelemetry,
    GenerationTelemetry,
    FeasibilityReport,
)

__all__ = [
    # User
    "User",
    "UserRole",
    "StudentProfile",
    "FacultyProfile",
    # Semester
    "Semester",
    "SemesterStatus",
    # Subject
    "Subject",
    "SubjectType",
    # Timetable
    "Timetable",
    "TimetableSlot",
    "DaySchedule",
    "DayOfWeek",
    "SlotType",
    "TimeSlot",
    # Attendance
    "AttendanceRecord",
    "AttendanceSummary",
    "AttendanceStatus",
    # Study Material
    "StudyMaterial",
    "MaterialType",
    # Subject Assignment
    "SubjectAssignment",
    # Request Context
    "RequestContext",
    # Feasibility Analysis
    "FeasibilityStatus",
    "Recoverability",
    "ConstraintSeverity",
    "RiskLevel",
    "SuggestionType",
    "SuggestionPriority",
    "ConstraintScore",
    "LocalWarning",
    "GlobalWarning",
    "WarningCollection",
    "Suggestion",
    "FeasibilityTelemetry",
    "GenerationTelemetry",
    "FeasibilityReport",
]
