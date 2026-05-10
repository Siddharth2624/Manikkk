"""Infrastructure layer - framework and external concerns."""

from .config import settings
from .database import db, get_database, init_indexes
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    SecurityManager
)
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
    get_current_admin,
    get_current_faculty,
    get_current_student,
    get_current_faculty_or_admin
)

__all__ = [
    # Config
    "settings",
    # Database
    "db",
    "get_database",
    "init_indexes",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "SecurityManager",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "get_current_admin",
    "get_current_faculty",
    "get_current_student",
    "get_current_faculty_or_admin",
]
