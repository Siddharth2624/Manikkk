"""Authorization and RBAC tests."""

import pytest
from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import UserRole, User
from app.domain.entities.attendance import AttendanceRecord, AttendanceStatus
from app.domain.exceptions import AuthorizationError, ValidationError
from datetime import UTC, datetime


class TestRequestContext:
    def test_from_user_student(self):
        user = User(
            id="123", email="s@test.com", password_hash="h",
            full_name="S", role=UserRole.STUDENT, is_active=True,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
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
            semester=1, section="A",
            attendance_date=datetime.now().date(),
            attendance=[{"student_id": "s123", "status": "present", "remarks": ""}],
            faculty_id="f123"
        )

        with pytest.raises(AuthorizationError, match="Only faculty can mark attendance"):
            await use_case.mark_attendance(ctx, request)

    @pytest.mark.asyncio
    async def test_mark_attendance_rejects_excused_status(self):
        from app.use_cases.attendance import AttendanceUseCase, MarkAttendanceRequest
        from unittest.mock import Mock

        ctx = RequestContext(
            user_id="507f1f77bcf86cd799439012",
            role=UserRole.FACULTY,
            email="f@test.com"
        )

        use_case = AttendanceUseCase(Mock(), Mock(), Mock(), Mock())
        request = MarkAttendanceRequest(
            subject_id="507f1f77bcf86cd799439011",
            semester=1,
            section="A",
            attendance_date=datetime.now().date(),
            attendance=[{"student_id": "s123", "status": "excused", "remarks": ""}],
            faculty_id="507f1f77bcf86cd799439012"
        )

        with pytest.raises(ValidationError, match="present.*absent"):
            await use_case.mark_attendance(ctx, request)

    @pytest.mark.asyncio
    async def test_subject_report_includes_students_without_attendance_records(self):
        from app.use_cases.attendance import AttendanceUseCase, AttendanceReportRequest
        from types import SimpleNamespace
        from unittest.mock import AsyncMock

        faculty_id = "507f1f77bcf86cd799439012"
        subject_id = "507f1f77bcf86cd799439011"
        ctx = RequestContext(
            user_id=faculty_id,
            role=UserRole.FACULTY,
            email="f@test.com"
        )

        attendance_repo = AsyncMock()
        subject_repo = AsyncMock()
        user_repo = AsyncMock()
        assignment_repo = AsyncMock()

        subject_repo.find_by_id.return_value = SimpleNamespace(
            id=subject_id,
            name="Data Structures",
            code="CS101"
        )
        assignment_repo.find_faculty_assignment.return_value = SimpleNamespace(id="assignment1")
        user_repo.find_all.return_value = [
            SimpleNamespace(id="student1", full_name="Student One", roll_number="001"),
            SimpleNamespace(id="student2", full_name="Student Two", roll_number="002"),
        ]
        attendance_repo.find_by_student_and_subject.side_effect = [
            [
                AttendanceRecord(
                    id="record1",
                    student_id="student1",
                    subject_id=subject_id,
                    faculty_id=faculty_id,
                    date=datetime.now().date(),
                    status=AttendanceStatus.PRESENT,
                )
            ],
            [],
        ]

        use_case = AttendanceUseCase(
            attendance_repo,
            subject_repo,
            user_repo,
            assignment_repo
        )
        request = AttendanceReportRequest(
            subject_id=subject_id,
            semester=1,
            section="A"
        )

        report = await use_case.get_subject_attendance(ctx, request)

        assert len(report["students"]) == 2
        assert report["students"][0]["present"] == 1
        assert report["students"][1]["total_classes"] == 0
        assert report["students"][1]["percentage"] == 0.0
        user_repo.find_all.assert_awaited_once_with(
            role=UserRole.STUDENT,
            semester=1,
            section="A",
            limit=1000
        )
