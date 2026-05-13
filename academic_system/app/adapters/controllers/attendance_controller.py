"""Attendance controller - FastAPI routes."""

from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.request_context import RequestContext
from app.domain.interfaces.repositories import (
    IAttendanceRepository, ISubjectRepository, IUserRepository, ISubjectAssignmentRepository
)
from app.adapters.repositories import (
    AttendanceRepository, SubjectRepository, UserRepository, SubjectAssignmentRepository
)
from app.use_cases.attendance import AttendanceUseCase
from app.infrastructure.authorization import get_request_context
from app.infrastructure.database import get_database
from app.domain.exceptions import AuthorizationError, ValidationError, ResourceNotFoundError
from pydantic import BaseModel
from datetime import date
import traceback

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# DTOs
class AttendanceItem(BaseModel):
    student_id: str
    status: Literal["present", "absent"]
    remarks: Optional[str] = None


class MarkAttendanceRequest(BaseModel):
    subject_id: str
    semester: int
    section: str
    attendance_date: date
    attendance: List[AttendanceItem]


async def get_attendance_use_case(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> AttendanceUseCase:
    """Dependency to get attendance use case."""
    attendance_repo = AttendanceRepository(db)
    subject_repo = SubjectRepository(db)
    user_repo = UserRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    return AttendanceUseCase(attendance_repo, subject_repo, user_repo, assignment_repo)


@router.post("/mark")
async def mark_attendance(
    request: MarkAttendanceRequest,
    ctx: RequestContext = Depends(get_request_context),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    """Mark attendance for students (faculty only)."""
    try:
        from app.use_cases.attendance import MarkAttendanceRequest as MarkRequest

        mark_request = MarkRequest(
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            attendance_date=request.attendance_date,
            attendance=[item.model_dump() for item in request.attendance],
            faculty_id=ctx.user_id
        )

        records = await attendance_use_case.mark_attendance(ctx, mark_request)

        return {
            "message": f"Attendance marked for {len(records)} students",
            "records_count": len(records)
        }
    except (AuthorizationError, ValidationError, ResourceNotFoundError) as e:
        raise  # Let the exception handlers in main.py handle these
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark attendance: {str(e)}"
        )


@router.get("/my-summary")
async def get_my_attendance_summary(
    subject_id: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    """Get attendance summary for current student."""
    # Force student_id from context for IDOR prevention
    student_id = ctx.user_id

    summaries = await attendance_use_case.get_student_attendance(
        ctx,
        student_id=student_id,
        subject_id=subject_id
    )

    response_summaries = []
    for summary in summaries:
        subject = await attendance_use_case.subject_repository.find_by_id(summary.subject_id)
        response_summaries.append({
            "subject_id": summary.subject_id,
            "subject_name": subject.name if subject else "Unknown Subject",
            "subject_code": subject.code if subject else "N/A",
            "subject": {
                "id": summary.subject_id,
                "name": subject.name if subject else "Unknown Subject",
                "code": subject.code if subject else "N/A"
            },
            "total_classes": summary.total_classes,
            "present": summary.present_count,
            "absent": summary.absent_count,
            "excused": summary.excused_count,
            "percentage": summary.percentage,
            "is_below_threshold": summary.is_below_threshold
        })

    return {
        "student": {
            "id": ctx.user_id,
            "email": ctx.email,
            "semester": ctx.semester,
            "section": ctx.section
        },
        "summaries": response_summaries
    }


@router.get("/report/{subject_id}")
async def get_attendance_report(
    subject_id: str,
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    student_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    ctx: RequestContext = Depends(get_request_context),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    """Get attendance report for a subject (faculty/admin only)."""
    from app.use_cases.attendance import AttendanceReportRequest

    request = AttendanceReportRequest(
        subject_id=subject_id,
        semester=semester,
        section=section,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date
    )

    report = await attendance_use_case.get_subject_attendance(ctx, request)
    return report


@router.get("/daily/{subject_id}")
async def get_daily_attendance(
    subject_id: str,
    attendance_date: date,
    ctx: RequestContext = Depends(get_request_context),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
):
    """Get attendance records for a subject on a specific date (faculty/admin only)."""
    try:
        records = await attendance_use_case.get_daily_attendance(
            ctx,
            subject_id=subject_id,
            attendance_date=attendance_date
        )

        return {
            "subject_id": subject_id,
            "date": attendance_date.isoformat(),
            "records": [
                {
                    "student_id": r.student_id,
                    "status": r.status.value,
                    "remarks": r.remarks,
                    "marked_at": r.marked_at.isoformat() if r.marked_at else None
                }
                for r in records
            ]
        }
    except (AuthorizationError, ValidationError, ResourceNotFoundError) as e:
        raise  # Let the exception handlers in main.py handle these
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily attendance: {str(e)}"
        )
