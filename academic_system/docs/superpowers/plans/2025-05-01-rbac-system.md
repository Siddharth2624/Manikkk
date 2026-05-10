# RBAC System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build production-grade RBAC system with defense-in-depth authorization at API and Service layers

**Architecture:** API layer validates JWT+role, Service layer validates business authorization, Repository layer is pure data access

**Tech Stack:** FastAPI, MongoDB (Motor), JWT (python-jose), Bcrypt, Pydantic

---

## File Structure

**New Files:**
- `app/domain/entities/request_context.py` - Immutable user context for service layer
- `app/domain/exceptions.py` - Custom exception classes (AuthorizationError, ResourceNotFoundError, ValidationError)
- `app/infrastructure/authorization.py` - Authorization utilities and dependencies

**Modified Files:**
- `app/infrastructure/config.py` - Add JWT settings
- `app/infrastructure/dependencies.py` - Add get_request_context
- `app/use_cases/attendance.py` - Add RequestContext, add validation
- `app/use_cases/study_material.py` - Add RequestContext, add validation
- `app/use_cases/timetable.py` - Add RequestContext
- `app/adapters/controllers/attendance_controller.py` - Use new patterns
- `app/adapters/controllers/study_material_controller.py` - Use new patterns
- `app/adapters/controllers/timetable_controller.py` - Use new patterns
- `main.py` - Add exception handlers

**Test Files:**
- `tests/test_authorization.py` - Authorization tests

---

## Task 1: Create Custom Exception Classes

**Files:**
- Create: `app/domain/exceptions.py`

```python
"""Custom exception classes for authorization and validation."""

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

- [ ] **Step 1: Create the exceptions file**

```bash
mkdir -p app/domain
```

- [ ] **Step 2: Write exception classes**

Write the code above to `app/domain/exceptions.py`

- [ ] **Step 3: Verify imports work**

```bash
python -c "from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/domain/exceptions.py
git commit -m "feat: add custom exception classes for RBAC"
```

---

## Task 2: Create RequestContext Entity

**Files:**
- Create: `app/domain/entities/request_context.py`

```python
"""RequestContext - Immutable user context for service layer authorization."""

from dataclasses import dataclass
from typing import Optional

from app.domain.entities.user import UserRole, User

@dataclass(frozen=True)
class RequestContext:
    """
    Immutable context passed to service layer.
    Contains user identity and role for authorization decisions.
    """
    user_id: str
    role: UserRole
    email: str
    semester: Optional[int] = None
    section: Optional[str] = None
    employee_id: Optional[str] = None

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

    def can_access_student_data(self, student_id: str) -> bool:
        if self.role in (UserRole.ADMIN, UserRole.FACULTY):
            return True
        return self.user_id == student_id
```

- [ ] **Step 1: Create RequestContext entity**

Write to `app/domain/entities/request_context.py`

- [ ] **Step 2: Test creation**

```bash
python -c "
from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import UserRole, User
from datetime import datetime

user = User(
    id='123', email='t@test.com', password_hash='h', full_name='T',
    role=UserRole.STUDENT, is_active=True,
    created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    semester=3, section='A'
)
ctx = RequestContext.from_user(user)
assert ctx.is_student()
assert ctx.can_access_student_data('123')
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/domain/entities/request_context.py
git commit -m "feat: add RequestContext entity"
```

---

## Task 3: Update Configuration

**Files:**
- Modify: `app/infrastructure/config.py`

- [ ] **Step 1: Read current config**

```bash
cat app/infrastructure/config.py
```

- [ ] **Step 2: Add JWT settings to Settings class**

Add these fields after existing JWT settings:

```python
jwt_access_token_expire_minutes: int = 30
jwt_refresh_token_expire_days: int = 7
jwt_refresh_enabled: bool = True
default_academic_year: str = "2024-2025"
```

- [ ] **Step 3: Verify config**

```bash
python -c "from app.infrastructure.config import settings; print(settings.default_academic_year); print('OK')"
```

Expected: `2024-2025` then `OK`

- [ ] **Step 4: Commit**

```bash
git add app/infrastructure/config.py
git commit -m "feat: add JWT settings and default academic year"
```

---

## Task 4: Create Authorization Utilities

**Files:**
- Create: `app/infrastructure/authorization.py`

```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import User
from .dependencies import get_current_user

async def get_request_context(
    current_user: User = Depends(get_current_user)
) -> RequestContext:
    """Convert User to RequestContext for service layer."""
    return RequestContext.from_user(current_user)
```

- [ ] **Step 1: Create authorization module**

Write to `app/infrastructure/authorization.py`

- [ ] **Step 2: Verify import**

```bash
python -c "from app.infrastructure.authorization import get_request_context; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/infrastructure/authorization.py
git commit -m "feat: add get_request_context dependency"
```

---

## Task 5: Add Exception Handlers to Main App

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Read main.py structure**

```bash
head -30 main.py
```

- [ ] **Step 2: Add imports**

Add after FastAPI imports:

```python
from fastapi.responses import JSONResponse
from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError
```

- [ ] **Step 3: Add exception handlers**

Add after app creation:

```python
@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request, exc: AuthorizationError):
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message, "code": exc.code, "type": "authorization_error"}
    )

@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(request, exc: ResourceNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "code": exc.code, "type": "not_found_error"}
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "field": exc.field, "code": exc.code, "type": "validation_error"}
    )
```

- [ ] **Step 4: Test server starts**

```bash
python -c "from main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add exception handlers"
```

---

## Task 6: Update Attendance Use Case

**Files:**
- Modify: `app/use_cases/attendance.py`

- [ ] **Step 1: Read current file**

```bash
cat app/use_cases/attendance.py
```

- [ ] **Step 2: Add imports**

```python
from app.domain.entities.request_context import RequestContext
from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError
from bson import ObjectId
```

- [ ] **Step 3: Update mark_attendance signature and add validation**

Update method signature to accept `ctx` first, add validation at start:

```python
async def mark_attendance(
    self,
    ctx: RequestContext,
    request: MarkAttendanceRequest
) -> List[AttendanceRecord]:
    # Input validation
    if not request.subject_id or not ObjectId.is_valid(request.subject_id):
        raise ValidationError("Invalid subject_id", "subject_id")
    if not 1 <= request.semester <= 8:
        raise ValidationError("Semester must be 1-8", "semester")
    if not request.section or len(request.section) > 2:
        raise ValidationError("Invalid section", "section")
    if not request.attendance:
        raise ValidationError("Attendance list required", "attendance")

    # Role check
    if ctx.is_student():
        raise AuthorizationError("Students cannot mark attendance")

    # Faculty assignment check
    if ctx.is_faculty():
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=ctx.user_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year
        )
        if not assignment:
            raise AuthorizationError("You are not assigned to teach this subject")

    # Proceed with existing logic...
```

- [ ] **Step 4: Update get_student_attendance**

Add student data access check:

```python
async def get_student_attendance(
    self,
    ctx: RequestContext,
    student_id: str,
    subject_id: Optional[str] = None
) -> List[AttendanceSummary]:
    # IDOR prevention
    if ctx.is_student() and ctx.user_id != student_id:
        raise AuthorizationError("Students can only view own attendance")
    # Continue with existing logic...
```

- [ ] **Step 5: Commit**

```bash
git add app/use_cases/attendance.py
git commit -m "feat(rbac): add RequestContext and validation to attendance"
```

---

## Task 7: Update Study Material Use Case

**Files:**
- Modify: `app/use_cases/study_material.py`

- [ ] **Step 1: Add imports**

```python
from app.domain.entities.request_context import RequestContext
from app.domain.exceptions import AuthorizationError, ValidationError
from bson import ObjectId
```

- [ ] **Step 2: Update upload_material**

Add ctx parameter and validation:

```python
async def upload_material(
    self,
    ctx: RequestContext,
    request: UploadMaterialRequest,
    file_content: bytes,
    file_name: str
) -> StudyMaterial:
    # Validation
    if not request.subject_id or not ObjectId.is_valid(request.subject_id):
        raise ValidationError("Invalid subject_id", "subject_id")
    if not file_content:
        raise ValidationError("File required", "file")

    # Auth
    if ctx.is_student():
        raise AuthorizationError("Students cannot upload")

    if ctx.is_faculty():
        # Verify assignment (simplified - check if teaching this subject)
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=ctx.user_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.sections[0] if request.sections else None,
            academic_year="2024-2025"
        )
        if not assignment:
            raise AuthorizationError("You can only upload for subjects you teach")

    # Continue with existing logic...
```

- [ ] **Step 3: Commit**

```bash
git add app/use_cases/study_material.py
git commit -m "feat(rbac): add RequestContext and validation to materials"
```

---

## Task 8: Update Attendance Controller

**Files:**
- Modify: `app/adapters/controllers/attendance_controller.py`

- [ ] **Step 1: Add imports**

```python
from app.domain.entities.request_context import RequestContext
from app.infrastructure.authorization import get_request_context
from app.domain.exceptions import AuthorizationError, ValidationError, ResourceNotFoundError
```

- [ ] **Step 2: Update mark_attendance endpoint**

```python
@router.post("/mark")
async def mark_attendance(
    request: MarkAttendanceRequest,
    ctx: RequestContext = Depends(get_request_context),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    try:
        from app.use_cases.attendance import MarkAttendanceRequest as MarkRequest

        mark_request = MarkRequest(
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year,
            attendance_date=request.attendance_date,
            attendance=[item.model_dump() for item in request.attendance],
            faculty_id=ctx.user_id
        )

        records = await attendance_use_case.mark_attendance(ctx, mark_request)

        return {
            "message": f"Attendance marked for {len(records)} students",
            "records_count": len(records)
        }
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
```

- [ ] **Step 3: Update get_my_attendance endpoint**

```python
@router.get("/my-summary")
async def get_my_attendance_summary(
    subject_id: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    summaries = await attendance_use_case.get_student_attendance(
        ctx,
        student_id=ctx.user_id,  # Forced to own ID (IDOR prevention)
        subject_id=subject_id
    )

    return {
        "student": {
            "id": ctx.user_id,
            "email": ctx.email,
            "semester": ctx.semester,
            "section": ctx.section
        },
        "summaries": summaries
    }
```

- [ ] **Step 4: Commit**

```bash
git add app/adapters/controllers/attendance_controller.py
git commit -m "feat(rbac): update attendance controller"
```

---

## Task 9: Update Study Material Controller

**Files:**
- Modify: `app/adapters/controllers/study_material_controller.py`

- [ ] **Step 1: Add imports**

```python
from app.domain.entities.request_context import RequestContext
from app.infrastructure.authorization import get_request_context
from app.domain.exceptions import AuthorizationError, ValidationError
```

- [ ] **Step 2: Update upload endpoint with error handling**

```python
@router.post("/upload")
async def upload_material(
    metadata: UploadMaterialRequest,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_request_context),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    try:
        content = await file.read()

        from app.use_cases.study_material import UploadMaterialRequest as UploadRequest

        request = UploadRequest(
            title=metadata.title,
            description=metadata.description,
            subject_id=metadata.subject_id,
            semester=metadata.semester,
            sections=metadata.sections,
            faculty_id=ctx.user_id,
            file_content=content,
            file_name=file.filename,
            tags=metadata.tags,
            is_public=metadata.is_public
        )

        material = await material_use_case.upload_material(ctx, request)

        return {
            "id": material.id,
            "title": material.title,
            "file_url": material.file_url
        }
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/controllers/study_material_controller.py
git commit -m "feat(rbac): update study material controller"
```

---

## Task 10: Update Timetable Controller

**Files:**
- Modify: `app/adapters/controllers/timetable_controller.py`

- [ ] **Step 1: Add imports**

```python
from app.domain.entities.request_context import RequestContext
from app.infrastructure.authorization import get_request_context
from app.domain.exceptions import ResourceNotFoundError
```

- [ ] **Step 2: Add student timetable endpoint**

```python
@router.get("/my")
async def get_my_timetable(
    academic_year: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    timetable_repo: TimetableRepository = Depends(get_timetable_repository)
):
    """Get timetable for current student."""
    if ctx.is_student():
        if not ctx.semester or not ctx.section:
            raise HTTPException(
                status_code=400,
                detail="Student profile incomplete: semester/section not set"
            )

        timetable = await timetable_repo.find_by_semester_and_section(
            semester=ctx.semester,
            section=ctx.section,
            academic_year=academic_year or "2024-2025"
        )

        if not timetable:
            raise ResourceNotFoundError("Timetable", f"{ctx.semester}-{ctx.section}")

        return {
            "semester": timetable.semester,
            "section": timetable.section,
            "schedule": timetable.schedule
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="Faculty/admin must use /timetable?semester=X&section=Y"
        )
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/controllers/timetable_controller.py
git commit -m "feat(rbac): add student timetable endpoint"
```

---

## Task 11: Create Authorization Tests

**Files:**
- Create: `tests/test_authorization.py`

```python
"""Authorization and RBAC tests."""

import pytest
from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import UserRole, User
from app.domain.exceptions import AuthorizationError, ValidationError
from datetime import datetime


class TestRequestContext:
    def test_from_user_student(self):
        user = User(
            id="123", email="s@test.com", password_hash="h",
            full_name="S", role=UserRole.STUDENT, is_active=True,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            semester=3, section="A"
        )
        ctx = RequestContext.from_user(user)
        assert ctx.user_id == "123"
        assert ctx.is_student()
        assert ctx.can_access_student_data("123")
        assert not ctx.can_access_student_data("456")


class TestExceptions:
    def test_authorization_error(self):
        error = AuthorizationError("Access denied", "FORBIDDEN")
        assert error.message == "Access denied"
        assert error.code == "FORBIDDEN"


class TestAttendanceAuthorization:
    @pytest.mark.asyncio
    async def test_student_cannot_mark_attendance(self):
        from app.use_cases.attendance import AttendanceUseCase, MarkAttendanceRequest
        from unittest.mock import Mock

        ctx = RequestContext(
            user_id="s123", role=UserRole.STUDENT,
            email="s@test.com"
        )

        use_case = AttendanceUseCase(Mock(), Mock(), Mock(), Mock())
        request = MarkAttendanceRequest(
            subject_id="507f1f77bcf86cd799439011",
            semester=1, section="A", academic_year="2024-2025",
            attendance_date=datetime.now().date(), attendance=[]
        )

        with pytest.raises(AuthorizationError, match="cannot mark"):
            await use_case.mark_attendance(ctx, request)
```

- [ ] **Step 1: Create test file**

Write to `tests/test_authorization.py`

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_authorization.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_authorization.py
git commit -m "test(rbac): add authorization tests"
```

---

## Task 12: Update Domain Entities Exports

**Files:**
- Modify: `app/domain/entities/__init__.py`

- [ ] **Step 1: Add RequestContext import**

```python
from .request_context import RequestContext
```

Add to `__all__`

- [ ] **Step 2: Commit**

```bash
git add app/domain/entities/__init__.py
git commit -m "feat: export RequestContext"
```

---

## Task 13: Update Domain Exports

**Files:**
- Modify: `app/domain/__init__.py`

- [ ] **Step 1: Add exceptions to domain exports**

```python
from .exceptions import AuthorizationError, ResourceNotFoundError, ValidationError
```

- [ ] **Step 2: Commit**

```bash
git add app/domain/__init__.py
git commit -m "feat: export exceptions from domain"
```

---

## Task 14: Final Verification

- [ ] **Step 1: Verify application imports**

```bash
python -c "from main import app; print('App loads successfully')"
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v --tb=short
```

- [ ] **Step 3: Verify no regressions**

Check that existing functionality still works

---

## Completion Checklist

- [ ] RequestContext created and exported
- [ ] Exception classes created and exported
- [ ] JWT settings added to config
- [ ] get_request_context dependency created
- [ ] Exception handlers added to main.py
- [ ] Attendance use case updated with validation
- [ ] Study material use case updated with validation
- [ ] Controllers updated to use RequestContext
- [ ] Student timetable endpoint added
- [ ] Authorization tests created
- [ ] Application starts without errors
- [ ] All tests pass
