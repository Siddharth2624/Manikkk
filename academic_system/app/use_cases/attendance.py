"""Attendance use cases."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import date, datetime
from bson import ObjectId

from app.domain.entities.attendance import (
    AttendanceRecord, AttendanceSummary, AttendanceStatus
)
from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import User, UserRole
from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError
from app.domain.interfaces.repositories import (
    IAttendanceRepository,
    ISubjectRepository,
    IUserRepository,
    ISubjectAssignmentRepository
)


@dataclass
class MarkAttendanceRequest:
    """Request to mark attendance."""
    subject_id: str
    semester: int
    section: str
    attendance_date: date
    attendance: List[dict]  # [{"student_id": str, "status": str, "remarks": str}]
    faculty_id: str


@dataclass
class AttendanceReportRequest:
    """Request for attendance report."""
    subject_id: str
    semester: int
    section: str
    student_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AttendanceUseCase:
    """Use case for attendance operations."""

    ALLOWED_MARKING_STATUSES = {
        AttendanceStatus.PRESENT.value,
        AttendanceStatus.ABSENT.value,
    }

    def __init__(
        self,
        attendance_repository: IAttendanceRepository,
        subject_repository: ISubjectRepository,
        user_repository: IUserRepository,
        subject_assignment_repository: ISubjectAssignmentRepository
    ):
        self.attendance_repository = attendance_repository
        self.subject_repository = subject_repository
        self.user_repository = user_repository
        self.subject_assignment_repository = subject_assignment_repository

    async def mark_attendance(
        self,
        ctx: RequestContext,
        request: MarkAttendanceRequest
    ) -> List[AttendanceRecord]:
        """
        Mark attendance for multiple students.

        Faculty authorization check: Verifies the faculty is assigned to this
        subject for the specified semester and section.

        Args:
            ctx: Request context for authorization
            request: Attendance marking request

        Returns:
            List of created/updated attendance records

        Raises:
            ValidationError: If input validation fails
            AuthorizationError: If user lacks permission
            ResourceNotFoundError: If subject not found
        """
        # Input validation
        # Validate subject_id is valid ObjectId
        if not request.subject_id or not ObjectId.is_valid(request.subject_id):
            raise ValidationError("Invalid subject ID format", field="subject_id")

        # Validate semester is 1-8
        if not isinstance(request.semester, int) or request.semester < 1 or request.semester > 8:
            raise ValidationError("Semester must be between 1 and 8", field="semester")

        # Validate section exists and length <= 2
        if not request.section or not isinstance(request.section, str) or len(request.section) > 2:
            raise ValidationError("Section must be a string with max length 2", field="section")

        # Validate attendance list is not empty
        if not request.attendance or not isinstance(request.attendance, list):
            raise ValidationError("Attendance list cannot be empty", field="attendance")

        for index, item in enumerate(request.attendance):
            if not isinstance(item, dict):
                raise ValidationError(
                    "Each attendance item must be an object",
                    field=f"attendance[{index}]"
                )
            if not item.get("student_id"):
                raise ValidationError(
                    "Student ID is required",
                    field=f"attendance[{index}].student_id"
                )
            if item.get("status") not in self.ALLOWED_MARKING_STATUSES:
                raise ValidationError(
                    "Attendance status must be either 'present' or 'absent'",
                    field=f"attendance[{index}].status"
                )

        # Role check: ONLY FACULTY can mark attendance
        if not ctx.is_faculty():
            raise AuthorizationError("Only faculty can mark attendance")

        # Faculty assignment check: Faculty must be assigned to teach this subject
        faculty_id = ctx.user_id

        # Verify subject exists
        subject = await self.subject_repository.find_by_id(request.subject_id)
        if not subject:
            raise ResourceNotFoundError("Subject", request.subject_id)

        # Faculty authorization: Verify faculty is assigned to this subject
        # for the specified semester and section
        assignment = await self.subject_assignment_repository.find_faculty_assignment(
            faculty_id=faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section
        )

        if not assignment:
            raise AuthorizationError(
                f"Faculty {faculty_id} is not authorized to mark attendance "
                f"for subject {request.subject_id} in semester {request.semester}, "
                f"section {request.section}"
            )

        # Create attendance records
        records = []
        for item in request.attendance:
            record = AttendanceRecord(
                id="",
                student_id=item["student_id"],
                subject_id=request.subject_id,
                faculty_id=request.faculty_id,
                date=request.attendance_date,
                status=AttendanceStatus(item["status"]),
                remarks=item.get("remarks"),
                marked_at=datetime.utcnow()
            )
            records.append(record)

        # Save batch
        await self.attendance_repository.save_batch(records)

        return records

    async def get_student_attendance(
        self,
        ctx: RequestContext,
        student_id: str,
        subject_id: Optional[str] = None
    ) -> List[AttendanceSummary]:
        """
        Get attendance summary for a student.

        IDOR prevention: Students can only view their own attendance.

        Args:
            ctx: Request context for authorization
            student_id: ID of the student
            subject_id: Optional subject ID for specific subject summary

        Returns:
            List of attendance summaries

        Raises:
            AuthorizationError: If student tries to access another student's data
        """
        # IDOR prevention: Students can only view their own attendance
        if ctx.is_student() and ctx.user_id != student_id:
            raise AuthorizationError(
                "Students can only view their own attendance"
            )

        if subject_id:
            summary = await self.attendance_repository.get_summary(
                student_id=student_id,
                subject_id=subject_id
            )
            if summary:
                return [summary]

            return [
                AttendanceSummary(
                    student_id=student_id,
                    subject_id=subject_id,
                    total_classes=0,
                    present_count=0,
                    absent_count=0,
                    excused_count=0,
                    percentage=0.0,
                    is_below_threshold=False
                )
            ]

        if ctx.is_student() and ctx.semester and ctx.section:
            assignments = await self.subject_assignment_repository.find_by_semester_and_section(
                semester=ctx.semester,
                section=ctx.section
            )
            subject_ids = []
            for assignment in assignments:
                if assignment.subject_id not in subject_ids:
                    subject_ids.append(assignment.subject_id)

            if subject_ids:
                summaries = []
                for assigned_subject_id in subject_ids:
                    summary = await self.attendance_repository.get_summary(
                        student_id=student_id,
                        subject_id=assigned_subject_id
                    )
                    summaries.append(
                        summary or AttendanceSummary(
                            student_id=student_id,
                            subject_id=assigned_subject_id,
                            total_classes=0,
                            present_count=0,
                            absent_count=0,
                            excused_count=0,
                            percentage=0.0,
                            is_below_threshold=False
                        )
                    )
                return summaries

        return await self.attendance_repository.get_all_summaries(student_id)

    async def get_subject_attendance(
        self,
        ctx: RequestContext,
        request: AttendanceReportRequest
    ) -> dict:
        """
        Get attendance report for a subject.

        Args:
            ctx: Request context for authorization
            request: Attendance report request

        Returns:
            Dictionary with attendance data

        Raises:
            AuthorizationError: If user lacks permission
        """
        # Role check: Students cannot access attendance reports
        if ctx.is_student():
            raise AuthorizationError("Students are not authorized to access attendance reports")

        # Faculty assignment check: Faculty must be assigned to this subject
        if ctx.is_faculty():
            assignment = await self.subject_assignment_repository.find_faculty_assignment(
                faculty_id=ctx.user_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section
            )
            if not assignment:
                raise AuthorizationError(
                    f"Faculty {ctx.user_id} is not authorized to view attendance reports "
                    f"for subject {request.subject_id} in semester {request.semester}, "
                    f"section {request.section}"
                )

        # Get subject details
        subject = await self.subject_repository.find_by_id(request.subject_id)
        if not subject:
            raise ResourceNotFoundError("Subject", request.subject_id)

        # Get every student in the section, even if they do not have attendance
        # records yet. Reports should show the whole class roster.
        students = await self.user_repository.find_all(
            role=UserRole.STUDENT,
            semester=request.semester,
            section=request.section,
            limit=1000
        )
        if request.student_id:
            students = [student for student in students if student.id == request.student_id]

        # Build attendance data
        attendance_data = []
        flat_students = []
        for student in students:
            start = request.start_date or date.today().replace(month=1, day=1)
            end = request.end_date or date.today()

            records = await self.attendance_repository.find_by_student_and_subject(
                student_id=student.id,
                subject_id=request.subject_id,
                start_date=start,
                end_date=end
            )

            if records:
                summary = AttendanceSummary.from_records(
                    student_id=student.id,
                    subject_id=request.subject_id,
                    records=records
                )
            else:
                summary = AttendanceSummary(
                    student_id=student.id,
                    subject_id=request.subject_id,
                    total_classes=0,
                    present_count=0,
                    absent_count=0,
                    excused_count=0,
                    percentage=0.0,
                    is_below_threshold=False
                )

            nested_row = {
                "student": {
                    "id": student.id,
                    "name": student.full_name,
                    "roll_number": student.roll_number
                },
                "summary": {
                    "total": summary.total_classes,
                    "present": summary.present_count,
                    "absent": summary.absent_count,
                    "excused": summary.excused_count,
                    "percentage": summary.percentage,
                    "is_below_threshold": summary.is_below_threshold
                }
            }
            flat_row = {
                "student_id": student.id,
                "student_name": student.full_name,
                "roll_number": student.roll_number,
                "total_classes": summary.total_classes,
                "present": summary.present_count,
                "absent": summary.absent_count,
                "excused": summary.excused_count,
                "percentage": summary.percentage,
                "is_below_threshold": summary.is_below_threshold
            }
            attendance_data.append(nested_row)
            flat_students.append(flat_row)

        return {
            "subject": {
                "id": subject.id,
                "name": subject.name,
                "code": subject.code
            },
            "attendance": attendance_data,
            "students": flat_students,
            "date_range": {
                "start": request.start_date.isoformat() if request.start_date else None,
                "end": request.end_date.isoformat() if request.end_date else None
            }
        }

    async def get_daily_attendance(
        self,
        ctx: RequestContext,
        subject_id: str,
        attendance_date: date
    ) -> List[AttendanceRecord]:
        """
        Get attendance records for a subject on a specific date.

        Args:
            ctx: Request context for authorization
            subject_id: Subject identifier
            attendance_date: Date to query

        Returns:
            List of attendance records

        Raises:
            AuthorizationError: If user lacks permission
        """
        # Role check: Students cannot access daily attendance records
        if ctx.is_student():
            raise AuthorizationError("Students are not authorized to access daily attendance records")

        # Faculty must be assigned to the subject (check if we can determine semester/section)
        # For now, allow admin and faculty to access (faculty assignment can be added later)

        return await self.attendance_repository.find_by_subject_and_date(
            subject_id=subject_id,
            attendance_date=attendance_date
        )
