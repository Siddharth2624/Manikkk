"""Domain interfaces - ports defining contracts."""

from .repositories import (
    IUserRepository,
    ISemesterRepository,
    ISubjectRepository,
    ITimetableRepository,
    IAttendanceRepository,
    IStudyMaterialRepository
)
from .timetable_generator import ITimetableGenerator
from .file_storage import IFileStorageService

__all__ = [
    # Repositories
    "IUserRepository",
    "ISemesterRepository",
    "ISubjectRepository",
    "ITimetableRepository",
    "IAttendanceRepository",
    "IStudyMaterialRepository",
    # Services
    "ITimetableGenerator",
    "IFileStorageService",
]
