"""Timetable controller - FastAPI routes - updated for single-document schema."""

import logging
import os
import random
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User
from app.domain.entities.timetable import DayOfWeek
from app.domain.entities.request_context import RequestContext
from app.domain.entities.feasibility import FeasibilityReport
from app.domain.exceptions import ResourceNotFoundError, FeasibilityError
from app.adapters.repositories import SubjectRepository, TimetableRepository, SubjectAssignmentRepository, UserRepository, FacultyAvailabilityRepository, AdminOverrideRepository
from app.adapters.repositories.generation_telemetry_repository import GenerationTelemetryRepository
from app.adapters.services.timetable_generator import TimetableGenerator
from app.domain.services.feasibility_analyzer import FeasibilityAnalyzer
from app.infrastructure.config import TelemetryConfig
from app.use_cases.timetable import TimetableUseCase
from app.infrastructure.dependencies import (
    get_current_user,
    get_current_admin,
    get_current_faculty_or_admin
)
from app.infrastructure.authorization import get_request_context
from app.infrastructure.database import get_database
from pydantic import BaseModel

router = APIRouter(prefix="/timetable", tags=["Timetable"])


# DTOs
class GenerateTimetableRequest(BaseModel):
    semester: int
    section: str
    subject_ids: Optional[List[str]] = None  # Optional: if not provided, auto-detect from assignments
    faculty_availability: Optional[dict] = None  # Optional: if not provided, use faculty availability data


class SimpleGenerateTimetableRequest(BaseModel):
    """Simplified request - just semester/section, auto-detect everything else."""
    semester: int
    section: str


class UpdateSlotRequest(BaseModel):
    day: str  # MON, TUE, WED, THU, FRI, SAT
    slot: int = Query(..., ge=1, le=10)
    subject_id: Optional[str] = None
    faculty_id: Optional[str] = None
    room: Optional[str] = None


class CreateVersionRequest(BaseModel):
    semester: int
    section: str


async def get_timetable_use_case(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> TimetableUseCase:
    """Dependency to get timetable use case with feasibility analysis."""
    subject_repo = SubjectRepository(db)
    timetable_repo = TimetableRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    user_repo = UserRepository(db)
    faculty_availability_repo = FacultyAvailabilityRepository(db)
    override_repo = AdminOverrideRepository(db)

    # Create timetable generator with subjects (will be updated before generation)
    timetable_generator = TimetableGenerator(subjects=[])

    # Create availability service for effective availability (base + overrides)
    from app.use_cases.faculty_availability import FacultyAvailabilityService
    availability_service = FacultyAvailabilityService(
        availability_repo=faculty_availability_repo,
        override_repo=override_repo,
        assignment_repo=assignment_repo,
        user_repo=user_repo,
        db=db
    )

    # Create feasibility analyzer for pre-generation analysis
    feasibility_analyzer = FeasibilityAnalyzer()

    # Create telemetry repository for generation tracking
    telemetry_config = TelemetryConfig(enabled=True)
    telemetry_repo = GenerationTelemetryRepository(db, telemetry_config)

    return TimetableUseCase(
        subject_repo,
        timetable_repo,
        timetable_generator=timetable_generator,
        assignment_repo=assignment_repo,
        user_repo=user_repo,
        faculty_availability_repo=faculty_availability_repo,
        availability_service=availability_service,
        override_repo=override_repo,
        feasibility_analyzer=feasibility_analyzer,
        telemetry_repo=telemetry_repo
    )


def _generation_conflict_response(
    timetable_use_case: TimetableUseCase,
    error: ValueError,
    semester: int,
    section: str
) -> Optional[JSONResponse]:
    """Return a structured generation-conflict response when the generator provides details."""
    generator = getattr(timetable_use_case, "timetable_generator", None)
    conflicts = getattr(generator, "last_conflicts", None)

    if not conflicts:
        return None

    return JSONResponse(
        status_code=400,
        content={
            "status": "generation_conflict",
            "message": "Timetable generation is blocked by one or more scheduling conflicts.",
            "summary": f"{len(conflicts)} issue(s) must be resolved before the timetable can be generated.",
            "semester": semester,
            "section": section,
            "conflicts": conflicts,
            "raw_error": str(error),
        }
    )


@router.post("/generate")
async def generate_timetable(
    request: GenerateTimetableRequest,
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Generate timetable for a semester and section (admin only).

    If subject_ids and faculty_availability are not provided, they will be auto-detected
    from existing subject assignments and faculty availability data.
    """
    try:
        from app.use_cases.timetable import GenerateTimetableRequest as GenRequest

        # If subject_ids not provided, auto-detect from assignments
        subject_ids = request.subject_ids
        faculty_availability = request.faculty_availability
        subject_faculty_map = {}

        if subject_ids is None or faculty_availability is None:
            detected = await timetable_use_case.detect_assignments_for_timetable(
                semester=request.semester,
                section=request.section
            )
            if subject_ids is None:
                subject_ids = detected["subject_ids"]
            if faculty_availability is None:
                faculty_availability = detected["faculty_availability"]
            subject_faculty_map = detected.get("subject_faculty_map", {})

        gen_request = GenRequest(
            semester=request.semester,
            section=request.section,
            subject_ids=subject_ids,
            faculty_availability=faculty_availability,
            subject_faculty_map=subject_faculty_map,
            created_by=current_user.id
        )

        response = await timetable_use_case.generate_timetable(gen_request)

        return {
            "message": "Timetable generated successfully",
            "timetable": {
                "id": response.timetable.id,
                "semester": response.timetable.semester,
                "section": response.timetable.section,
                "version": response.timetable.version
            },
            "warnings": response.warnings
        }
    except ValueError as e:
        conflict_response = _generation_conflict_response(
            timetable_use_case,
            e,
            request.semester,
            request.section
        )
        if conflict_response:
            return conflict_response

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/generate/simple")
async def generate_timetable_simple(
    request: SimpleGenerateTimetableRequest,
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Generate timetable with automatic detection (simplified version).

    Only requires semester and section.
    Automatically detects subjects, faculty, and their availability from assignments.
    """
    try:
        response = await timetable_use_case.generate_timetable_simple(
            semester=request.semester,
            section=request.section,
            created_by=current_user.id
        )

        return {
            "message": "Timetable generated successfully",
            "timetable": {
                "id": response.timetable.id,
                "semester": response.timetable.semester,
                "section": response.timetable.section,
                "version": response.timetable.version
            },
            "warnings": response.warnings
        }
    except FeasibilityError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status": "fail",
                "can_proceed": False,
                "confidence_score": e.report.confidence_score,
                "recoverability": e.report.recoverability.value,
                "errors": e.report.errors,
                "warnings": _format_warnings(e.report.warnings),
                "suggestions": _format_suggestions(e.report.suggestions),
                "constraint_scores": _format_constraint_scores(e.report.constraint_scores),
                "telemetry": _format_telemetry(e.report.telemetry_snapshot)
            }
        )
    except ValueError as e:
        conflict_response = _generation_conflict_response(
            timetable_use_case,
            e,
            request.semester,
            request.section
        )
        if conflict_response:
            return conflict_response

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/generate/bulk")
async def generate_timetable_bulk(
    semester: int = Query(..., ge=1, le=8, description="Semester number"),
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generate timetable for ALL sections in a semester (admin only).

    Generates timetables for all sections (A, B, etc.) in one click.
    Returns a summary of generated timetables.
    """
    try:
        # Get all distinct sections for this semester from assignments
        assignment_repo = SubjectAssignmentRepository(db)
        sections = await assignment_repo.get_distinct_sections(semester)

        if not sections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sections found for semester {semester}"
            )

        results = []
        errors = []

        # Generate timetable for each section
        for section in sections:
            try:
                response = await timetable_use_case.generate_timetable_simple(
                    semester=semester,
                    section=section,
                    created_by=current_user.id
                )
                results.append({
                    "section": section,
                    "timetable_id": response.timetable.id,
                    "version": response.timetable.version,
                    "status": "success"
                })
                logger.info(f"Generated timetable for semester {semester}, section {section}")
            except ValueError as e:
                error_msg = str(e)
                errors.append({
                    "section": section,
                    "error": error_msg
                })
                logger.warning(f"Failed to generate timetable for semester {semester}, section {section}: {error_msg}")

        return {
            "message": f"Bulk generation completed for semester {semester}",
            "semester": semester,
            "total_sections": len(sections),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk generation failed: {str(e)}"
        )


@router.get("/assignments/preview")
async def get_assignments_preview(
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Get subject assignments for a semester/section (for preview before generating timetable)."""
    try:
        assignments = await timetable_use_case.get_assignments_for_timetable(
            semester=semester,
            section=section
        )
        return {
            "semester": semester,
            "section": section,
            "assignments": assignments
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("")
async def view_timetable(
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    version: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """View timetable for a semester and section.

    If version is specified, returns that version.
    Otherwise returns the active version with subject/faculty details joined.
    """
    try:
        from app.use_cases.timetable import ViewTimetableRequest
        request = ViewTimetableRequest(
            semester=semester,
            section=section,
            version=version
        )

        timetable = await timetable_use_case.view_timetable(request)

        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )

        return timetable
    except Exception as e:
        logger.error(f"Error in view_timetable: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading timetable: {str(e)}"
        )


@router.get("/faculty/{faculty_id}")
async def get_faculty_schedule(
    faculty_id: str,
    current_user: User = Depends(get_current_faculty_or_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Get schedule for a faculty member."""
    from app.use_cases.timetable import FacultyScheduleRequest

    # Faculty can only see their own schedule
    if current_user.is_faculty() and current_user.id != faculty_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own schedule"
        )

    request = FacultyScheduleRequest(
        faculty_id=faculty_id
    )

    schedule = await timetable_use_case.get_faculty_schedule(request)
    return {"faculty_id": faculty_id, "schedule": schedule}


@router.get("/list")
async def list_timetables(
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """List all semester-section combinations with active timetables."""
    timetables = await timetable_use_case.list_all_timetables()
    return {"timetables": timetables}


@router.get("/my")
async def get_my_timetable(
    ctx: RequestContext = Depends(get_request_context),
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Get the current user's timetable. For students: uses their semester and section."""
    # Faculty/admin should use query params instead
    if current_user.is_faculty() or current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faculty and admin users should use the /timetable endpoint with query parameters."
        )

    from app.use_cases.timetable import ViewTimetableRequest
    request = ViewTimetableRequest(
        semester=ctx.semester,
        section=ctx.section,
        version=None  # Get active version
    )

    timetable = await timetable_use_case.view_timetable(request)

    if not timetable:
        raise ResourceNotFoundError(
            f"Timetable not found for semester {ctx.semester}, section {ctx.section}"
        )

    return timetable


@router.get("/versions/{semester}/{section}")
async def list_timetable_versions(
    semester: int,
    section: str,
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """List all versions of a timetable (admin only)."""
    versions = await timetable_use_case.list_versions(
        semester=semester,
        section=section
    )
    return {
        "semester": semester,
        "section": section,
        "versions": versions
    }


@router.post("/versions/activate/{timetable_id}")
async def activate_timetable_version(
    timetable_id: str,
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Activate a specific timetable version (admin only)."""
    success = await timetable_use_case.activate_version(
        timetable_id=timetable_id,
        semester=semester,
        section=section
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable not found"
        )

    return {"message": "Timetable version activated successfully"}


@router.post("/versions/create")
async def create_new_version(
    request: CreateVersionRequest,
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Create a new version of an existing timetable (admin only)."""
    from app.use_cases.timetable import CreateVersionRequest as CreateRequest

    create_request = CreateRequest(
        semester=request.semester,
        section=request.section,
        created_by=current_user.id
    )

    new_timetable = await timetable_use_case.create_new_version(create_request)

    if not new_timetable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existing timetable found to copy"
        )

    return {
        "message": "New timetable version created",
        "timetable": {
            "id": new_timetable.id,
            "semester": new_timetable.semester,
            "section": new_timetable.section,
            "version": new_timetable.version
        }
    }


@router.put("/slots/{timetable_id}")
async def update_timetable_slot(
    timetable_id: str,
    request: UpdateSlotRequest,
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Update a single slot in a timetable (admin only)."""
    from app.use_cases.timetable import UpdateTimetableRequest

    # Convert day string to DayOfWeek
    day_map = {
        "MON": DayOfWeek.MONDAY,
        "TUE": DayOfWeek.TUESDAY,
        "WED": DayOfWeek.WEDNESDAY,
        "THU": DayOfWeek.THURSDAY,
        "FRI": DayOfWeek.FRIDAY,
        "SAT": DayOfWeek.SATURDAY
    }

    day = day_map.get(request.day.upper())
    if not day:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day: {request.day}"
        )

    update_request = UpdateTimetableRequest(
        timetable_id=timetable_id,
        day=day,
        slot=request.slot,
        subject_id=request.subject_id,
        faculty_id=request.faculty_id,
        room=request.room
    )

    updated = await timetable_use_case.update_slot(update_request)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable not found"
        )

    return {
        "message": "Slot updated successfully",
        "timetable": {
            "id": updated.id,
            "version": updated.version
        }
    }


@router.get("/conflicts")
async def check_timetable_conflicts(
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    day: str = Query(...),
    slot: int = Query(..., ge=1, le=10),
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Check for conflicts at a specific day and slot."""
    day_map = {
        "MON": DayOfWeek.MONDAY,
        "TUE": DayOfWeek.TUESDAY,
        "WED": DayOfWeek.WEDNESDAY,
        "THU": DayOfWeek.THURSDAY,
        "FRI": DayOfWeek.FRIDAY,
        "SAT": DayOfWeek.SATURDAY
    }

    day_enum = day_map.get(day.upper())
    if not day_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day: {day}"
        )

    conflicts = await timetable_use_case.check_conflicts(
        semester=semester,
        section=section,
        day=day_enum,
        slot=slot
    )

    return {
        "semester": semester,
        "section": section,
        "day": day,
        "slot": slot,
        "conflicts": conflicts
    }


@router.get("/conflicts/faculty/{faculty_id}")
async def check_faculty_conflicts(
    faculty_id: str,
    day: str = Query(...),
    slot: int = Query(..., ge=1, le=10),
    exclude_timetable_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Check if faculty is already booked at this day/slot."""
    day_map = {
        "MON": DayOfWeek.MONDAY,
        "TUE": DayOfWeek.TUESDAY,
        "WED": DayOfWeek.WEDNESDAY,
        "THU": DayOfWeek.THURSDAY,
        "FRI": DayOfWeek.FRIDAY,
        "SAT": DayOfWeek.SATURDAY
    }

    day_enum = day_map.get(day.upper())
    if not day_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day: {day}"
        )

    conflicts = await timetable_use_case.check_faculty_conflicts(
        faculty_id=faculty_id,
        day=day_enum,
        slot=slot,
        exclude_timetable_id=exclude_timetable_id
    )

    return {
        "faculty_id": faculty_id,
        "day": day,
        "slot": slot,
        "conflicts": conflicts
    }


@router.get("/conflicts/room/{room}")
async def check_room_conflicts(
    room: str,
    day: str = Query(...),
    slot: int = Query(..., ge=1, le=10),
    exclude_timetable_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Check if room is already booked at this day/slot."""
    day_map = {
        "MON": DayOfWeek.MONDAY,
        "TUE": DayOfWeek.TUESDAY,
        "WED": DayOfWeek.WEDNESDAY,
        "THU": DayOfWeek.THURSDAY,
        "FRI": DayOfWeek.FRIDAY,
        "SAT": DayOfWeek.SATURDAY
    }

    day_enum = day_map.get(day.upper())
    if not day_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day: {day}"
        )

    conflicts = await timetable_use_case.check_room_conflicts(
        room=room,
        day=day_enum,
        slot=slot,
        exclude_timetable_id=exclude_timetable_id
    )

    return {
        "room": room,
        "day": day,
        "slot": slot,
        "conflicts": conflicts
    }


@router.delete("/{semester}/{section}")
async def delete_timetable(
    semester: int,
    section: str,
    current_user: User = Depends(get_current_admin),
    timetable_use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Delete all versions of timetable for a semester and section (admin only)."""
    deleted_count = await timetable_use_case.delete_timetable(
        semester=semester,
        section=section
    )

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No timetables found to delete"
        )

    return {
        "message": f"Deleted {deleted_count} timetable version(s)",
        "deleted_count": deleted_count
    }


@router.get("/slots")
async def get_time_slots():
    """Get available time slots."""
    time_slots = []
    for i in range(1, 11):
        hour = 9 + (i - 1) // 2
        minute = "00" if (i - 1) % 2 == 0 else "30"
        time_slots.append({
            "slot": i,
            "start_time": f"{hour}:{minute}",
            "end_time": f"{hour}:{'30' if minute == '00' else '00'}"
        })
    return {"time_slots": time_slots}


# =============================================================================
# Feasibility Response Formatting Helpers
# =============================================================================


def _format_warnings(warnings) -> Dict[str, Any]:
    """Format WarningCollection into structured response."""
    return {
        "local": [
            {
                "faculty_id": w.faculty_id,
                "faculty_name": w.faculty_name,
                "subject_id": w.subject_id,
                "subject_name": w.subject_name,
                "risk_level": w.risk_level.value,
                "constraint_score": w.constraint_score,
                "severity": w.severity.value,
                "message": w.message,
                "suggestion": w.suggestion
            }
            for w in warnings.local
        ],
        "global": [
            {
                "slot_number": w.slot_number,
                "time_range": w.time_range,
                "competing_subjects": w.competing_subjects,
                "competing_faculty": w.competing_faculty,
                "competing_subject_names": getattr(w, "competing_subject_names", []),
                "competing_faculty_names": getattr(w, "competing_faculty_names", []),
                "supply_demand_ratio": w.supply_demand_ratio,
                "risk_level": w.risk_level.value,
                "message": w.message
            }
            for w in warnings.global_warnings
        ]
    }


def _format_suggestions(suggestions: List) -> List[Dict[str, Any]]:
    """Format suggestions list into structured response."""
    return [
        {
            "target_faculty_id": s.target_faculty_id,
            "target_subject_id": s.target_subject_id,
            "suggestion_type": s.suggestion_type.value,
            "message": s.message,
            "priority": s.priority.value,
            "expected_impact": s.expected_impact
        }
        for s in suggestions
    ]


def _format_constraint_scores(constraint_scores: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Format constraint scores dict into structured response."""
    return {
        key: {
            "subject_id": score.subject_id,
            "faculty_id": score.faculty_id,
            "subject_name": score.subject_name,
            "faculty_name": score.faculty_name,
            "required_slots": score.required_slots,
            "unique_available_slots": score.unique_available_slots,
            "score": score.score,
            "severity": score.severity.value,
            "consecutive_pairs_available": score.consecutive_pairs_available
        }
        for key, score in constraint_scores.items()
    }


def _format_telemetry(telemetry: Optional[Any]) -> Optional[Dict[str, Any]]:
    """Format FeasibilityTelemetry into structured response."""
    if telemetry is None:
        return None
    return {
        "analysis_timestamp": telemetry.analysis_timestamp.isoformat(),
        "semester": telemetry.semester,
        "section": telemetry.section,
        "total_faculty": telemetry.total_faculty,
        "total_subjects": telemetry.total_subjects,
        "total_theory": telemetry.total_theory,
        "total_labs": telemetry.total_labs,
        "bottleneck_slots": telemetry.bottleneck_slots,
        "tightly_constrained_faculty": telemetry.tightly_constrained_faculty,
        "low_diversity_faculty": telemetry.low_diversity_faculty,
        "lab_feasible": telemetry.lab_feasible,
        "estimated_generation_time_ms": telemetry.estimated_generation_time_ms
    }
