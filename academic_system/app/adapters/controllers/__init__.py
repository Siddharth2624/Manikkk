"""Controllers - FastAPI routers."""

from .auth_controller import router as auth_router
from .admin_controller import router as admin_router
from .timetable_controller import router as timetable_router
from .attendance_controller import router as attendance_router
from .study_material_controller import router as study_material_router
from .faculty_assignment_controller import router as admin_faculty_router, faculty_router

__all__ = [
    "auth_router",
    "admin_router",
    "timetable_router",
    "attendance_router",
    "study_material_router",
    "admin_faculty_router",
    "faculty_router",
]
