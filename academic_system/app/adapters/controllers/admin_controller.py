"""Admin controller - FastAPI routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User, UserRole
from app.domain.entities.subject import SubjectType
from app.infrastructure.config import Settings, settings
from app.domain.interfaces.repositories import IUserRepository, ISubjectRepository
from app.adapters.repositories import UserRepository, SubjectRepository
from app.infrastructure.dependencies import get_current_admin, get_current_user, get_current_faculty, get_current_student, get_current_faculty_or_admin
from app.infrastructure.database import get_database
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/admin", tags=["Admin"])


# DTOs
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    semester: int = None
    section: str = None
    roll_number: str = None
    employee_id: str = None
    department: str = None


class UpdateUserRequest(BaseModel):
    full_name: str = None
    department: str = None
    semester: int = None
    section: str = None
    is_active: bool = None


class SubjectCreateRequest(BaseModel):
    code: str
    name: str
    semester: int
    subject_type: SubjectType
    credits: Optional[int] = None
    classes_per_week: Optional[int] = None


async def get_user_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> IUserRepository:
    """Dependency to get user repository."""
    return UserRepository(db)


async def get_subject_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ISubjectRepository:
    """Dependency to get subject repository."""
    return SubjectRepository(db)


async def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


# Test endpoint (disabled in production)
@router.get("/test")
async def test_admin(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """Test admin endpoint - shows current user info. Disabled in production."""
    # Disable debug endpoint in production
    if settings.environment.lower() == "production":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "message": "Admin test endpoint working",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "is_admin": current_user.is_admin(),
            "is_faculty": current_user.is_faculty(),
            "is_student": current_user.is_student()
        }
    }


@router.get("/stats/public")
async def get_public_stats(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get public statistics (no auth required)."""
    total_users = await db.users.count_documents({})
    students = await db.users.count_documents({"role": "student"})
    faculty = await db.users.count_documents({"role": "faculty"})
    admins = await db.users.count_documents({"role": "admin"})

    return {
        "total_users": total_users,
        "students": students,
        "faculty": faculty,
        "admins": admins
    }


# User Management Endpoints
@router.get("/users")
async def list_users(
    role: UserRole = None,
    semester: int = None,
    section: str = None,
    skip: int = 0,
    limit: int = Query(20, le=100),
    current_admin: User = Depends(get_current_admin),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """List users with optional filters (admin only)."""
    users = await user_repo.find_all(
        role=role,
        semester=semester,
        section=section,
        skip=skip,
        limit=limit
    )
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "semester": u.semester,
                "section": u.section,
                "roll_number": u.roll_number,
                "department": u.department,
                "is_active": u.is_active
            }
            for u in users
        ],
        "count": len(users)
    }


@router.get("/students/by-class")
async def get_students_by_class(
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    current_user: User = Depends(get_current_faculty_or_admin),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Get students by semester and section (faculty/admin only)."""
    users = await user_repo.find_all(
        role=UserRole.STUDENT,
        semester=semester,
        section=section
    )
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "roll_number": u.roll_number,
                "semester": u.semester,
                "section": u.section
            }
            for u in users
        ]
    }


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    current_admin: User = Depends(get_current_admin),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Create a new user (admin only)."""
    try:
        user = await user_repo.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
            semester=request.semester,
            section=request.section,
            roll_number=request.roll_number,
            employee_id=request.employee_id,
            department=request.department
        )
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "message": "User created successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_admin: User = Depends(get_current_admin),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Update user information (admin only)."""
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await user_repo.save(user)
    return {"message": "User updated successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Delete a user (admin only)."""
    success = await user_repo.delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deleted successfully"}


# Statistics Endpoints
@router.get("/stats")
async def get_statistics(
    current_admin: User = Depends(get_current_admin),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Get system statistics (admin only)."""
    total_users = await user_repo.count()
    admins = await user_repo.count(UserRole.ADMIN)
    faculty = await user_repo.count(UserRole.FACULTY)
    students = await user_repo.count(UserRole.STUDENT)

    return {
        "total_users": total_users,
        "admins": admins,
        "faculty": faculty,
        "students": students
    }


# Subject Management Endpoints
@router.get("/subjects")
async def list_subjects(
    semester: int = None,
    subject_type: SubjectType = None,
    current_admin: User = Depends(get_current_admin),
    subject_repo: ISubjectRepository = Depends(get_subject_repository)
):
    """List all subjects (admin only)."""
    subjects = await subject_repo.find_all(semester=semester, subject_type=subject_type, limit=100)
    return {
        "subjects": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "semester": s.semester,
                "subject_type": s.subject_type.value if hasattr(s.subject_type, 'value') else s.subject_type,
                "credits": s.credits,
                "classes_per_week": s.classes_per_week
            }
            for s in subjects
        ]
    }


@router.post("/subjects")
async def create_subject(
    request: SubjectCreateRequest,
    current_admin: User = Depends(get_current_admin),
    subject_repo: ISubjectRepository = Depends(get_subject_repository)
):
    """Create a new subject (admin only)."""
    try:
        from app.domain.entities.subject import Subject

        if not request.code.strip() or not request.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subject code and name are required"
            )

        existing = await subject_repo.find_by_code(request.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subject code {request.code.upper()} already exists"
            )

        if request.subject_type == SubjectType.LAB:
            credits = 2
            classes_per_week = 2
        else:
            credits = request.credits or 3
            classes_per_week = request.classes_per_week or credits

        subject = Subject(
            id="",
            code=request.code.strip().upper(),
            name=request.name.strip(),
            semester=request.semester,
            subject_type=request.subject_type,
            credits=credits,
            classes_per_week=classes_per_week
        )

        subject = await subject_repo.save(subject)
        return {
            "id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "semester": subject.semester,
            "subject_type": subject.subject_type.value,
            "credits": subject.credits,
            "classes_per_week": subject.classes_per_week,
            "message": "Subject created successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subject: {str(e)}"
        )
