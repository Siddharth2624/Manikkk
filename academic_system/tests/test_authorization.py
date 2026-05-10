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
            attendance_date=datetime.now().date(),
            attendance=[{"student_id": "s123", "status": "present", "remarks": ""}],
            faculty_id="f123"
        )

        with pytest.raises(AuthorizationError, match="not authorized"):
            await use_case.mark_attendance(ctx, request)
