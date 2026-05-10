"""Dependency injection for FastAPI routes."""

from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from .database import get_database
from .security import verify_token
from app.domain.entities.user import UserRole, User

# Type hints for repository factory functions (lazy imports to avoid circular dependency)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.adapters.repositories.user_repository import UserRepository
    from app.adapters.repositories.subject_repository import SubjectRepository
    from app.adapters.repositories.subject_assignment_repository import SubjectAssignmentRepository
    from app.adapters.repositories.timetable_repository import TimetableRepository
    from app.adapters.repositories.attendance_repository import AttendanceRepository
    from app.adapters.repositories.study_material_repository import StudyMaterialRepository
    from app.adapters.repositories.semester_repository import SemesterRepository
    from app.adapters.repositories.faculty_availability_repository import FacultyAvailabilityRepository
    from app.adapters.repositories.admin_override_repository import AdminOverrideRepository


# Repository dependency factories (lazy imports to avoid circular dependency)
def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get user repository instance."""
    from app.adapters.repositories.user_repository import UserRepository
    return UserRepository(db)


def get_subject_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get subject repository instance."""
    from app.adapters.repositories.subject_repository import SubjectRepository
    return SubjectRepository(db)


def get_subject_assignment_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get subject assignment repository instance."""
    from app.adapters.repositories.subject_assignment_repository import SubjectAssignmentRepository
    return SubjectAssignmentRepository(db)


def get_timetable_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get timetable repository instance."""
    from app.adapters.repositories.timetable_repository import TimetableRepository
    return TimetableRepository(db)


def get_attendance_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get attendance repository instance."""
    from app.adapters.repositories.attendance_repository import AttendanceRepository
    return AttendanceRepository(db)


def get_study_material_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get study material repository instance."""
    from app.adapters.repositories.study_material_repository import StudyMaterialRepository
    return StudyMaterialRepository(db)


def get_semester_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get semester repository instance."""
    from app.adapters.repositories.semester_repository import SemesterRepository
    return SemesterRepository(db)


def get_faculty_availability_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get faculty availability repository instance."""
    from app.adapters.repositories.faculty_availability_repository import FacultyAvailabilityRepository
    return FacultyAvailabilityRepository(db)


def get_admin_override_repository(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get admin override repository instance."""
    from app.adapters.repositories.admin_override_repository import AdminOverrideRepository
    return AdminOverrideRepository(db)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Raises:
        HTTPException: If authentication fails
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fetch user from database
    from app.adapters.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


def require_role(*roles: UserRole):
    """
    Dependency factory to require specific user roles.

    Usage:
        @router.get("/admin-only")
        async def admin_only_route(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            return {"message": "Welcome admin"}
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(r.value for r in roles)}"
            )
        return current_user

    return role_checker


async def get_current_admin(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> User:
    """Dependency to get current admin user."""
    return current_user


async def get_current_faculty(
    current_user: User = Depends(require_role(UserRole.FACULTY))
) -> User:
    """Dependency to get current faculty user."""
    return current_user


async def get_current_student(
    current_user: User = Depends(require_role(UserRole.STUDENT))
) -> User:
    """Dependency to get current student user."""
    return current_user


async def get_current_faculty_or_admin(
    current_user: User = Depends(require_role(UserRole.FACULTY, UserRole.ADMIN))
) -> User:
    """Dependency to get current faculty or admin user."""
    return current_user
