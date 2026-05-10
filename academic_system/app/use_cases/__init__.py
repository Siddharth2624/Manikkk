"""Use cases - application business logic."""

from .auth import *
from .timetable import *
from .attendance import *
from .study_material import *
from .faculty_assignment import *
from .faculty_availability import *
from .admin_override import *

__all__ = [
    # Auth
    "AuthenticationUseCase",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "ChangePasswordRequest",
    # Timetable
    "TimetableUseCase",
    "GenerateTimetableRequest",
    "GenerateTimetableResponse",
    "ViewTimetableRequest",
    "FacultyScheduleRequest",
    # Attendance
    "AttendanceUseCase",
    "MarkAttendanceRequest",
    "AttendanceReportRequest",
    # Study Material
    "StudyMaterialUseCase",
    "UploadMaterialRequest",
    "SearchMaterialRequest",
    # Faculty Assignment
    "FacultyAssignmentService",
    "AssignSubjectRequest",
    "AssignSubjectResponse",
    # Faculty Availability
    "FacultyAvailabilityService",
    "UpdateAvailabilityRequest",
    "EffectiveAvailabilityResponse",
    # Admin Override
    "AdminOverrideService",
    "CreateOverrideRequest",
    "OverrideResponse",
    "AuditLogResponse",
]
