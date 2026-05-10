# RBAC System Design - Academic Management Platform

**Status:** Ready for Implementation
**Date:** 2025-05-01
**Author:** System Design

---

## 1. Overview

Production-grade Role-Based Access Control (RBAC) system with defense-in-depth authorization enforcement at both API and Service layers.

### Roles (Exactly 3)
- **ADMIN** - Full system control
- **FACULTY** - Subject-specific access
- **STUDENT** - Personal data access only

---

## 2. Architecture

```
Request → API Layer (Role Check) → Service Layer (Business Auth + Input Validation) → Repository → Database
              ↓ 403 if wrong role      ↓ 403 if unauthorized OR invalid input
```

**Key Principle:**
- **API Layer:** Validates JWT token + user role
- **Service Layer:** Validates business authorization + input data
- **Repository Layer:** Pure data access, NO authorization logic

---

## 3. Components

### 3.1 RequestContext Object

**Location:** `app/domain/entities/request_context.py`

```python
from dataclasses import dataclass, field
from typing import Optional
from app.domain.entities.user import UserRole

@dataclass(frozen=True)
class RequestContext:
    """
    Immutable context passed to service layer.
    Contains user identity and role for authorization decisions.
    """
    user_id: str
    role: UserRole
    email: str
    semester: Optional[int] = None      # For students
    section: Optional[str] = None       # For students
    employee_id: Optional[str] = None   # For faculty

    @classmethod
    def from_user(cls, user: User) -> "RequestContext":
        return cls(
            user_id=user.id,
            role=user.role,
            email=user.email,
            semester=user.semester,
            section=user.section,
            employee_id=user.employee_id
        )

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_faculty(self) -> bool:
        return self.role == UserRole.FACULTY

    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT
```

### 3.2 Custom Exceptions

**Location:** `app/domain/exceptions.py`

```python
class AuthorizationError(Exception):
    """
    Raised when service-layer authorization fails.
    ALWAYS raise this instead of silent failures or empty results.
    """
    def __init__(self, message: str, code: str = "FORBIDDEN"):
        self.message = message
        self.code = code
        super().__init__(message)

class ResourceNotFoundError(Exception):
    """Raised when a requested resource doesn't exist."""
    def __init__(self, resource_type: str, identifier: str):
        self.message = f"{resource_type} '{identifier}' not found"
        self.code = "NOT_FOUND"
        super().__init__(self.message)

class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        self.code = "VALIDATION_ERROR"
        super().__init__(message)
```

### 3.3 JWT Token Management

**Location:** `app/infrastructure/config.py` (add to settings)

```python
class Settings(BaseSettings):
    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30    # Short-lived access tokens
    jwt_refresh_token_expire_days: int = 7        # Longer-lived refresh tokens
    jwt_refresh_enabled: bool = True               # Allow refresh token rotation
```

**Token Strategy:**
- Access tokens: 30 minutes (short-lived, reduced attack window)
- Refresh tokens: 7 days (optional, for better UX)
- Refresh token rotation: When refreshing, invalidate old refresh token
- Tokens include: `sub` (user_id), `role`, `email`, `type` (access/refresh)

### 3.4 Authorization Utilities

**Location:** `app/infrastructure/authorization.py`

```python
from typing import Optional
from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import UserRole, User
from app.domain.exceptions import AuthorizationError
from .dependencies import get_current_user, get_database
from .config import settings

async def get_request_context(
    current_user: User = Depends(get_current_user)
) -> RequestContext:
    """Convert User to RequestContext for service layer."""
    return RequestContext.from_user(current_user)

async def require_faculty_for_subject(
    subject_id: str,
    semester: int,
    section: str,
    academic_year: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> RequestContext:
    """
    API layer dependency: Verify faculty is assigned to subject.
    Raises 403 if not assigned.
    """
    if ctx.is_admin():
        return ctx

    from app.adapters.repositories.subject_assignment_repository import SubjectAssignmentRepository
    assignment_repo = SubjectAssignmentRepository(db)

    year = academic_year or settings.default_academic_year
    assignment = await assignment_repo.find_faculty_assignment(
        faculty_id=ctx.user_id,
        subject_id=subject_id,
        semester=semester,
        section=section,
        academic_year=year
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to teach this subject in this semester/section"
        )
    return ctx
```

### 3.5 Service Layer Validation Pattern

**CRITICAL RULES:**
1. Accept `RequestContext` as FIRST parameter
2. Validate ALL inputs before DB access
3. Raise `AuthorizationError` for auth failures (NEVER return empty results)
4. Raise `ResourceNotFoundError` for missing resources
5. Repositories are PURE data access (NO auth logic)

```python
from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError

class AttendanceUseCase:
    async def mark_attendance(
        self,
        ctx: RequestContext,  # FIRST parameter - ALWAYS
        request: MarkAttendanceRequest
    ) -> List[AttendanceRecord]:
        """
        Mark attendance for students.

        Raises:
            AuthorizationError: If user lacks permission
            ValidationError: If input data is invalid
            ResourceNotFoundError: If subject/student doesn't exist
        """
        # Step 1: Input validation (before any DB access)
        self._validate_mark_attendance_request(request)

        # Step 2: Role-based authorization
        if ctx.is_student():
            raise AuthorizationError("Students cannot mark attendance")

        # Step 3: Business authorization (faculty assignment check)
        if ctx.is_faculty():
            assignment = await self._verify_faculty_assignment(
                faculty_id=ctx.user_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section,
                academic_year=request.academic_year
            )
            # Assignment MUST exist - raise error if not
            if not assignment:
                raise AuthorizationError(
                    "You are not assigned to teach this subject in this semester/section"
                )

        # Step 4: Verify subject exists
        subject = await self.subject_repo.find_by_id(request.subject_id)
        if not subject:
            raise ResourceNotFoundError("Subject", request.subject_id)

        # Step 5: Proceed with business logic
        return await self._mark_attendance_records(ctx, request)

    def _validate_mark_attendance_request(self, request: MarkAttendanceRequest):
        """Validate request data before any processing."""
        if not request.subject_id or not ObjectId.is_valid(request.subject_id):
            raise ValidationError("Invalid subject_id", "subject_id")

        if not 1 <= request.semester <= 8:
            raise ValidationError("Semester must be between 1 and 8", "semester")

        if not request.section or len(request.section) > 2:
            raise ValidationError("Invalid section", "section")

        if not request.attendance:
            raise ValidationError("Attendance list cannot be empty", "attendance")

        # Validate each student ID
        for item in request.attendance:
            if not item.student_id or not ObjectId.is_valid(item.student_id):
                raise ValidationError(f"Invalid student_id: {item.student_id}", "attendance")
```

### 3.6 Repository Layer (Pure Data Access)

**CRITICAL:** Repositories do NOT enforce authorization. Service layer is responsible for all security.

```python
class AttendanceRepository:
    """Pure data access - NO authorization logic."""

    async def find_by_student_and_subject(
        self,
        student_id: str,
        subject_id: str
    ) -> List[AttendanceRecord]:
        """
        Get attendance records for a student in a subject.
        NO authorization check - service layer handles that.
        """
        # Simply return data, no filtering based on who is asking
        cursor = self.collection.find({
            "student_id": ObjectId(student_id),
            "subject_id": ObjectId(subject_id)
        })
        return [self._to_entity(doc) async for doc in cursor]

    async def save(self, attendance: AttendanceRecord) -> AttendanceRecord:
        """Save or update attendance record."""
        # Pure data access, no auth
        ...

    # DO NOT add methods like:
    # - get_student_attendance_for_user(requesting_user_role, ...)  ← NO
    # - find_with_authorization(user_context, ...)                 ← NO
```

### 3.7 API Layer Error Handlers

**Location:** `main.py`

```python
from fastapi.responses import JSONResponse
from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request, exc: AuthorizationError):
    """Convert AuthorizationError to HTTP 403."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": exc.message,
            "code": exc.code,
            "type": "authorization_error"
        }
    )

@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(request, exc: ResourceNotFoundError):
    """Convert ResourceNotFoundError to HTTP 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "code": exc.code,
            "type": "not_found_error"
        }
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Convert ValidationError to HTTP 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "field": exc.field,
            "code": exc.code,
            "type": "validation_error"
        }
    )
```

---

## 4. Protected Endpoint Examples

### 4.1 Admin: Create User

```python
@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    ctx: RequestContext = Depends(get_request_context),
    # API layer role check via existing dependency
    _: None = Depends(get_current_admin),
    user_use_case: UserUseCase = Depends(get_user_use_case)
):
    """
    Admin only - Create new user.

    API Layer: get_current_admin ensures only ADMIN reaches here
    Service Layer: Validates input and creates user
    """
    user = await user_use_case.create_user(ctx, request)
    return user
```

### 4.2 Faculty: Mark Attendance (with service-layer auth)

```python
@router.post("/attendance/mark")
async def mark_attendance(
    request: MarkAttendanceRequest,
    # API layer: Faculty or Admin can access
    current_user: User = Depends(get_current_faculty_or_admin),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    """
    Mark attendance for students.

    API Layer: Only FACULTY or ADMIN
    Service Layer: Verifies faculty is assigned to this specific subject
    """
    ctx = RequestContext.from_user(current_user)

    # Service layer will verify faculty-subject assignment
    # and raise AuthorizationError if not assigned
    records = await attendance_use_case.mark_attendance(ctx, request)

    return {
        "message": f"Attendance marked for {len(records)} students",
        "records_count": len(records)
    }
```

### 4.3 Student: View Own Attendance (IDOR prevention)

```python
@router.get("/attendance/my-summary")
async def get_my_attendance(
    subject_id: Optional[str] = None,
    # API layer: Any authenticated user
    current_user: User = Depends(get_current_user),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    """
    Get attendance summary for current student.

    API Layer: Any authenticated user can call
    Service Layer: Students only see their own data (IDOR prevention)
    """
    ctx = RequestContext.from_user(current_user)

    if ctx.is_student():
        # Force student_id to be the student's own ID
        # Service layer validates this matches ctx.user_id
        summaries = await attendance_use_case.get_student_attendance(
            ctx,
            student_id=ctx.user_id,  # Forced - prevents IDOR
            subject_id=subject_id
        )
    else:
        # Faculty/admin must specify which student
        raise HTTPException(400, "Students must use /attendance/my-summary")

    return {"summaries": summaries}
```

### 4.4 Student: View Timetable (semester/section scope)

```python
@router.get("/timetable/my")
async def get_my_timetable(
    academic_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """
    Get timetable for current student.

    Service Layer: Students see their semester/section only
    """
    ctx = RequestContext.from_user(current_user)

    if ctx.is_student():
        # Use student's semester/section from context
        if not ctx.semester or not ctx.section:
            raise HTTPException(400, "Student profile incomplete: semester/section not set")

        timetable = await timetable_use_case.get_timetable(
            ctx,
            semester=ctx.semester,
            section=ctx.section,
            academic_year=academic_year
        )
    else:
        # Faculty/admin need to specify parameters
        raise HTTPException(
            400,
            "Faculty/admin must use GET /timetable?semester=X&section=Y"
        )

    return timetable
```

---

## 5. Authorization Matrix

| Operation | Admin | Faculty | Student | Service Layer Check |
|-----------|-------|---------|---------|---------------------|
| Create users | ✅ | ❌ | ❌ | - |
| Assign faculty to subjects | ✅ | ❌ | ❌ | - |
| Generate timetables | ✅ | ❌ | ❌ | - |
| Mark attendance | ✅ | ⚠️ | ❌ | Faculty: verify assignment |
| Upload materials | ✅ | ⚠️ | ❌ | Faculty: verify assignment |
| View own attendance | ✅ | ✅ | ✅ | Student: own records only |
| View any attendance | ✅ | ⚠️ | ❌ | Faculty: assigned subjects |
| View timetable (own sem/sec) | ✅ | ✅ | ✅ | Student: own sem/sec |
| View timetable (any) | ✅ | ✅ | ❌ | - |
| Download materials | ✅ | ✅ | ✅ | Student: enrolled subjects |

⚠️ = Requires business authorization check

---

## 6. Security Checklist

### Authentication
- [ ] JWT access tokens expire in 30 minutes
- [ ] Refresh tokens expire in 7 days (optional)
- [ ] Passwords hashed with bcrypt
- [ ] JWT secret key is strong and from environment

### Authorization (API Layer)
- [ ] All protected endpoints use `get_current_user` or role-specific dependency
- [ ] Unauthenticated requests return 401
- [ ] Wrong role returns 403

### Authorization (Service Layer)
- [ ] All service methods accept `RequestContext` as first parameter
- [ ] Faculty-subject assignments verified before operations
- [ ] Students can only access their own data (IDOR prevention)
- [ ] `AuthorizationError` raised for all auth failures (no silent failures)

### Input Validation
- [ ] All IDs validated (ObjectId format)
- [ ] Pydantic models validate request structure
- [ ] `ValidationError` raised for invalid input
- [ ] Validation happens before DB access

### Error Handling
- [ ] Consistent error codes (FORBIDDEN, NOT_FOUND, VALIDATION_ERROR)
- [ ] No sensitive data in error messages
- [ ] Stack traces never exposed to clients

### Repository Layer
- [ ] NO authorization logic in repositories
- [ ] Repositories return data or raise technical errors
- [ ] Service layer is final authority for access control

---

## 7. Implementation Order

1. **Exception classes** (`app/domain/exceptions.py`)
2. **RequestContext entity** (`app/domain/entities/request_context.py`)
3. **Configuration updates** (JWT settings, default_academic_year)
4. **Authorization utilities** (`app/infrastructure/authorization.py`)
5. **Error handlers** (`main.py`)
6. **Update use cases** (add RequestContext, add validation)
7. **Update controllers** (use new patterns)
8. **Tests** (authorization paths, IDOR prevention)

---

## 8. Files to Create/Modify

### Create:
- `app/domain/entities/request_context.py`
- `app/domain/exceptions.py`
- `app/infrastructure/authorization.py`

### Modify:
- `app/infrastructure/config.py` (add JWT settings)
- `app/infrastructure/dependencies.py` (add get_request_context)
- `app/use_cases/attendance.py` (add RequestContext, validation)
- `app/use_cases/study_material.py` (add RequestContext, validation)
- `app/use_cases/timetable.py` (add RequestContext)
- `app/use_cases/auth.py` (update return types)
- `app/adapters/controllers/*.py` (use new patterns)
- `main.py` (add exception handlers)

### Do NOT Modify:
- Repository files (keep them as pure data access)
