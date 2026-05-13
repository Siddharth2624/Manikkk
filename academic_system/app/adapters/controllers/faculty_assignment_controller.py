"""Faculty Assignment & Availability Admin Controller.

Provides endpoints for:
- Assigning subjects to faculty
- Managing faculty availability
- Creating and managing admin overrides
"""

import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query

logger = logging.getLogger(__name__)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User, UserRole
from app.domain.interfaces.repositories import (
    IUserRepository,
    ISubjectRepository,
    ISubjectAssignmentRepository,
    IFacultyAvailabilityRepository,
    IAdminOverrideRepository
)
from app.domain.exceptions import ValidationError, ResourceNotFoundError, AuthorizationError
from app.use_cases.faculty_assignment import (
    FacultyAssignmentService,
    AssignSubjectRequest as ServiceAssignSubjectRequest
)
from app.use_cases.faculty_availability import (
    FacultyAvailabilityService,
    UpdateAvailabilityRequest as ServiceUpdateAvailabilityRequest,
    EffectiveAvailabilityResponse as ServiceEffectiveAvailabilityResponse
)
from app.use_cases.admin_override import (
    AdminOverrideService,
    CreateOverrideRequest as ServiceCreateOverrideRequest
)
from app.infrastructure.dependencies import (
    get_current_admin,
    get_current_faculty,
    get_current_user,
    get_database
)
from app.adapters.controllers.dto.faculty_assignment import (
    DayOfWeekEnum,
    OverrideActionEnum,
    OverrideTypeEnum,
    SlotDTO,
    OverrideSlotDTO,
    OverrideDetail,
    AssignSubjectRequest,
    UpdateAvailabilityRequest,
    CreateOverrideRequest,
    AssignmentResponse,
    SubjectInfo,
    MySubjectResponse,
    FacultyAssignmentResponse,
    AvailabilityResponse,
    EffectiveAvailabilityResponse,
    OverrideLogResponse,
    OverrideResponse
)

router = APIRouter(prefix="/admin", tags=["Admin - Faculty Assignment"])


# =============================================================================
# Dependency Injection Functions
# =============================================================================

async def get_user_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> IUserRepository:
    """Dependency to get user repository."""
    from app.adapters.repositories.user_repository import UserRepository
    return UserRepository(db)


async def get_subject_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ISubjectRepository:
    """Dependency to get subject repository."""
    from app.adapters.repositories.subject_repository import SubjectRepository
    return SubjectRepository(db)


async def get_subject_assignment_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ISubjectAssignmentRepository:
    """Dependency to get subject assignment repository."""
    from app.adapters.repositories.subject_assignment_repository import SubjectAssignmentRepository
    return SubjectAssignmentRepository(db)


async def get_faculty_availability_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> IFacultyAvailabilityRepository:
    """Dependency to get faculty availability repository."""
    from app.adapters.repositories.faculty_availability_repository import FacultyAvailabilityRepository
    return FacultyAvailabilityRepository(db)


async def get_admin_override_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> IAdminOverrideRepository:
    """Dependency to get admin override repository."""
    from app.adapters.repositories.admin_override_repository import AdminOverrideRepository
    return AdminOverrideRepository(db)


async def get_faculty_assignment_service(
    user_repo: IUserRepository = Depends(get_user_repository),
    subject_repo: ISubjectRepository = Depends(get_subject_repository),
    assignment_repo: ISubjectAssignmentRepository = Depends(get_subject_assignment_repository),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FacultyAssignmentService:
    """Dependency to get faculty assignment service."""
    return FacultyAssignmentService(
        user_repo=user_repo,
        subject_repo=subject_repo,
        assignment_repo=assignment_repo,
        db=db
    )


async def get_faculty_availability_service(
    availability_repo: IFacultyAvailabilityRepository = Depends(get_faculty_availability_repository),
    override_repo: IAdminOverrideRepository = Depends(get_admin_override_repository),
    assignment_repo: ISubjectAssignmentRepository = Depends(get_subject_assignment_repository),
    user_repo: IUserRepository = Depends(get_user_repository),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FacultyAvailabilityService:
    """Dependency to get faculty availability service."""
    return FacultyAvailabilityService(
        availability_repo=availability_repo,
        override_repo=override_repo,
        assignment_repo=assignment_repo,
        user_repo=user_repo,
        db=db
    )


async def get_admin_override_service(
    override_repo: IAdminOverrideRepository = Depends(get_admin_override_repository),
    availability_repo: IFacultyAvailabilityRepository = Depends(get_faculty_availability_repository),
    assignment_repo: ISubjectAssignmentRepository = Depends(get_subject_assignment_repository),
    user_repo: IUserRepository = Depends(get_user_repository),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> AdminOverrideService:
    """Dependency to get admin override service."""
    return AdminOverrideService(
        override_repo=override_repo,
        availability_repo=availability_repo,
        assignment_repo=assignment_repo,
        user_repo=user_repo,
        db=db
    )


async def _build_assignment_response(
    assignment,
    subject_repo: ISubjectRepository,
    user_repo: IUserRepository
) -> FacultyAssignmentResponse:
    """Build a frontend-friendly assignment response with display names."""
    subject = await subject_repo.find_by_id(assignment.subject_id)
    faculty = await user_repo.find_by_id(assignment.faculty_id)

    return FacultyAssignmentResponse(
        id=assignment.id,
        faculty_id=assignment.faculty_id,
        faculty_name=faculty.full_name if faculty else "",
        faculty_email=faculty.email if faculty else "",
        subject_id=assignment.subject_id,
        subject_name=subject.name if subject else "",
        subject_code=subject.code if subject else "",
        semester=assignment.semester,
        section=assignment.section,
        created_at=assignment.created_at
    )


def _build_effective_availability_response(
    response: ServiceEffectiveAvailabilityResponse
) -> EffectiveAvailabilityResponse:
    """Convert service effective availability into API response DTO."""
    persistent_overrides = []
    one_time_overrides = []

    for override in response.applied_overrides:
        slots = [
            OverrideSlotDTO(
                day=DayOfWeekEnum(s["day"]),
                slot=s["slot"],
                action=OverrideActionEnum(s["action"])
            )
            for s in override["slots"]
        ]
        detail = OverrideDetail(
            id=override["id"],
            override_type=override["type"],
            slots=slots,
            admin_id=override["admin_id"],
            timestamp=override["timestamp"],
            applied=override.get("applied", False)
        )
        if override["type"] == "persistent":
            persistent_overrides.append(detail)
        else:
            one_time_overrides.append(detail)

    return EffectiveAvailabilityResponse(
        base_slots=[
            SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
            for slot in response.base_slots
        ],
        effective_slots=[
            SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
            for slot in response.effective_slots
        ],
        persistent_overrides=persistent_overrides,
        one_time_overrides=one_time_overrides
    )


# =============================================================================
# Admin Routes
# =============================================================================


@router.post(
    "/assign-subject",
    response_model=AssignmentResponse,
    summary="Assign a subject to a faculty member",
    description="Creates a new assignment linking a faculty member to a subject for a specific semester and section."
)
@router.post(
    "/subject-assignments",
    response_model=AssignmentResponse,
    include_in_schema=False
)
async def assign_subject(
    request: AssignSubjectRequest,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_faculty_assignment_service)
):
    """Assign a subject to a faculty member (admin only)."""
    try:
        response = await service.assign_subject(
            ServiceAssignSubjectRequest(
                faculty_id=request.faculty_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section
            ),
            current_admin
        )
        assignment = response.assignment

        return AssignmentResponse(
            id=assignment.id,
            faculty_id=assignment.faculty_id,
            subject_id=assignment.subject_id,
            semester=assignment.semester,
            section=assignment.section,
            created_at=assignment.created_at
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/assign-subject/{assignment_id}",
    summary="Delete a subject assignment",
    description="Removes an assignment linking a faculty member to a subject."
)
@router.delete(
    "/subject-assignments/{assignment_id}",
    include_in_schema=False
)
async def delete_assignment(
    assignment_id: str,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_faculty_assignment_service)
):
    """Delete a subject assignment (admin only)."""
    try:
        result = await service.remove_assignment(assignment_id, current_admin)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        return {"message": "Assignment deleted successfully"}

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/assignments",
    response_model=List[FacultyAssignmentResponse],
    summary="Get all subject assignments",
    description="Retrieves all subject assignments with optional filters for faculty, subject, semester, or section."
)
@router.get(
    "/subject-assignments",
    response_model=List[FacultyAssignmentResponse],
    include_in_schema=False
)
async def get_assignments(
    faculty_id: Optional[str] = Query(None, description="Filter by faculty ID"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    semester: Optional[int] = Query(None, ge=1, le=8, description="Filter by semester"),
    section: Optional[str] = Query(None, description="Filter by section"),
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_faculty_assignment_service)
):
    """Get all subject assignments (admin only)."""
    try:
        assignments = await service.find_assignments(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section
        )

        result = []
        for assignment in assignments:
            result.append(
                await _build_assignment_response(
                    assignment,
                    service.subject_repo,
                    service.user_repo
                )
            )
        return result

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/faculty/{faculty_id}/subjects",
    response_model=List[FacultyAssignmentResponse],
    summary="Get subjects assigned to a faculty member",
    description="Retrieves all subjects assigned to a specific faculty member."
)
async def get_faculty_subjects(
    faculty_id: str,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_faculty_assignment_service)
):
    """Get subjects assigned to a faculty member (admin only)."""
    try:
        assignments = await service.find_assignments(faculty_id=faculty_id)

        result = []
        for assignment in assignments:
            result.append(
                await _build_assignment_response(
                    assignment,
                    service.subject_repo,
                    service.user_repo
                )
            )
        return result

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/subjects/{subject_id}/faculty",
    response_model=List[FacultyAssignmentResponse],
    summary="Get faculty assigned to a subject",
    description="Retrieves all faculty members assigned to a specific subject."
)
async def get_subject_faculty(
    subject_id: str,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_faculty_assignment_service)
):
    """Get faculty assigned to a subject (admin only)."""
    try:
        assignments = await service.find_assignments(subject_id=subject_id)

        result = []
        for assignment in assignments:
            result.append(
                await _build_assignment_response(
                    assignment,
                    service.subject_repo,
                    service.user_repo
                )
            )
        return result

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# =============================================================================
# Faculty Availability Admin Routes
# =============================================================================


@router.get(
    "/faculty-availability",
    response_model=AvailabilityResponse,
    summary="Get faculty availability",
    description="Get a faculty member's availability for a specific subject assignment."
)
async def get_faculty_availability_admin(
    faculty_id: str = Query(..., description="Faculty ID"),
    subject_id: str = Query(..., description="Subject ID"),
    semester: int = Query(..., ge=1, le=8, description="Semester"),
    section: str = Query(..., min_length=1, max_length=2, description="Section"),
    current_admin: User = Depends(get_current_admin),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Get faculty availability for a subject (admin only)."""
    try:
        response = await service.get_effective_availability(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section
        )

        slots = response.effective_slots if response else []

        return AvailabilityResponse(
            available_slots=[
                SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
                for slot in slots
            ]
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/faculty-availability/effective",
    response_model=EffectiveAvailabilityResponse,
    summary="Get effective faculty availability",
    description="Get base availability plus admin overrides for a faculty assignment."
)
async def get_faculty_effective_availability_admin(
    faculty_id: str = Query(..., description="Faculty ID"),
    subject_id: str = Query(..., description="Subject ID"),
    semester: int = Query(..., ge=1, le=8, description="Semester"),
    section: str = Query(..., min_length=1, max_length=2, description="Section"),
    current_admin: User = Depends(get_current_admin),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Get effective availability including base slots and admin overrides."""
    try:
        response = await service.get_effective_availability(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section,
            requesting_user=current_admin
        )

        return _build_effective_availability_response(response)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.put(
    "/faculty-availability/{faculty_id}",
    response_model=AvailabilityResponse,
    summary="Update faculty availability",
    description="Admins can update availability on behalf of a faculty member."
)
async def update_faculty_availability(
    faculty_id: str,
    request: UpdateAvailabilityRequest,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Update faculty availability (admin can update any faculty)."""
    try:
        service_request = ServiceUpdateAvailabilityRequest(
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            available_slots=[slot.model_dump() for slot in request.available_slots]
        )

        availability = await service.update_availability(
            service_request,
            faculty_id,
            current_admin
        )

        return AvailabilityResponse(
            available_slots=[
                SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
                for slot in availability.available_slots
            ]
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# =============================================================================
# Admin Override Routes
# =============================================================================


@router.post(
    "/overrides",
    response_model=OverrideResponse,
    summary="Create an admin override",
    description="Create an override to add or remove slots from a faculty's availability."
)
async def create_override(
    request: CreateOverrideRequest,
    current_admin: User = Depends(get_current_admin),
    service: AdminOverrideService = Depends(get_admin_override_service)
):
    """Create an admin override (admin only)."""
    try:
        response = await service.create_override(
            ServiceCreateOverrideRequest(
                faculty_id=request.faculty_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section,
                override_type=request.override_type,
                slots=[slot.model_dump() for slot in request.slots]
            ),
            current_admin.id,
            current_admin
        )
        override = response.override

        return OverrideResponse(
            id=override.id,
            faculty_id=override.faculty_id,
            subject_id=override.subject_id,
            semester=override.semester,
            section=override.section,
            override_type=override.override_type.value,
            slots=[
                OverrideSlotDTO(
                    day=DayOfWeekEnum(slot.day.value),
                    slot=slot.slot,
                    action=OverrideActionEnum(slot.action.value)
                )
                for slot in override.slots
            ],
            admin_id=override.admin_id,
            timestamp=override.timestamp,
            applied=override.applied
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/overrides",
    response_model=List[OverrideLogResponse],
    summary="Get all admin overrides",
    description="Retrieves all admin overrides with optional filters."
)
async def get_overrides(
    faculty_id: Optional[str] = Query(None, description="Filter by faculty ID"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    current_admin: User = Depends(get_current_admin),
    service: AdminOverrideService = Depends(get_admin_override_service),
    user_repo: IUserRepository = Depends(get_user_repository),
    subject_repo: ISubjectRepository = Depends(get_subject_repository)
):
    """Get all admin overrides (admin only)."""
    try:
        audit_log = await service.get_audit_log(
            faculty_id=faculty_id,
            subject_id=subject_id,
            current_user=current_admin
        )

        result = []
        for override in audit_log.overrides:
            faculty = await user_repo.find_by_id(override.faculty_id)
            admin = await user_repo.find_by_id(override.admin_id)
            subject = await subject_repo.find_by_id(override.subject_id)

            result.append(
                OverrideLogResponse(
                    id=override.id,
                    faculty_id=override.faculty_id,
                    faculty_name=faculty.full_name if faculty else "",
                    subject_id=override.subject_id,
                    subject_name=subject.name if subject else "",
                    semester=override.semester,
                    section=override.section,
                    override_type=override.override_type.value,
                    slots=[
                        OverrideSlotDTO(
                            day=DayOfWeekEnum(slot.day.value),
                            slot=slot.slot,
                            action=OverrideActionEnum(slot.action.value)
                        )
                        for slot in override.slots
                    ],
                    admin_id=override.admin_id,
                    admin_name=admin.full_name if admin else "",
                    timestamp=override.timestamp,
                    applied=override.applied
                )
            )

        return result

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/overrides/{override_id}",
    summary="Delete an admin override",
    description="Deletes an admin override by ID."
)
async def delete_override(
    override_id: str,
    current_admin: User = Depends(get_current_admin),
    service: AdminOverrideService = Depends(get_admin_override_service)
):
    """Delete an admin override (admin only)."""
    try:
        result = await service.delete_override(override_id, current_admin)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Override not found"
            )
        return {"message": "Override deleted successfully"}

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# =============================================================================
# Faculty Routes (for faculty self-service)
# =============================================================================

faculty_router = APIRouter(prefix="/faculty", tags=["Faculty - Assignments & Availability"])


@faculty_router.get(
    "/my-subjects",
    response_model=List[MySubjectResponse],
    summary="Get my assigned subjects",
    description="Retrieves all subjects assigned to the currently logged-in faculty member."
)
async def get_my_subjects(
    current_faculty: User = Depends(get_current_faculty),
    service: FacultyAssignmentService = Depends(get_faculty_assignment_service),
    subject_repo: ISubjectRepository = Depends(get_subject_repository),
    availability_repo: IFacultyAvailabilityRepository = Depends(get_faculty_availability_repository)
):
    """Get subjects assigned to current faculty."""
    try:
        assignments = await service.find_assignments(faculty_id=current_faculty.id)

        result = []
        for a in assignments:
            # Fetch subject details
            subject = await subject_repo.find_by_id(a.subject_id)

            # Fetch availability for this assignment
            availability = await availability_repo.find_by_faculty_and_subject(
                faculty_id=current_faculty.id,
                subject_id=a.subject_id,
                semester=a.semester,
                section=a.section
            )

            # Convert available_slots to format expected by frontend ["Day-Slot"]
            available_slots = []
            if availability and availability.available_slots:
                for slot in availability.available_slots:
                    day_initial = slot.day[0]  # 'M' from 'MON'
                    day_rest = slot.day[1:].lower() if len(slot.day) > 1 else ''
                    available_slots.append(f"{day_initial}{day_rest}-{slot.slot}")

            result.append(
                MySubjectResponse(
                    subject=SubjectInfo(
                        id=a.subject_id,
                        code=subject.code if subject else "",
                        name=subject.name if subject else "Unknown",
                        credits=subject.credits if subject else 3
                    ),
                    semester=a.semester,
                    section=a.section,
                    available_slots=available_slots
                )
            )

        return result

    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@faculty_router.get(
    "/availability",
    response_model=AvailabilityResponse,
    summary="Get faculty availability for a subject",
    description="Get current faculty's availability for a specific subject assignment. Includes admin overrides."
)
async def get_faculty_availability(
    subject_id: str = Query(..., description="Subject ID"),
    semester: int = Query(..., ge=1, le=8, description="Semester"),
    section: str = Query(..., min_length=1, max_length=2, description="Section"),
    current_faculty: User = Depends(get_current_faculty),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Get faculty's availability for a subject (including admin overrides)."""
    try:
        if not ObjectId.is_valid(subject_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subject_id"
            )

        # Get EFFECTIVE availability (base + overrides)
        effective_response = await service.get_effective_availability(
            faculty_id=current_faculty.id,
            subject_id=subject_id,
            semester=semester,
            section=section,
            requesting_user=current_faculty
        )

        slots = effective_response.effective_slots if effective_response else []

        return AvailabilityResponse(
            available_slots=[
                SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
                for slot in slots
            ]
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@faculty_router.post(
    "/availability",
    response_model=AvailabilityResponse,
    summary="Update faculty availability",
    description="Update current faculty's availability for a subject assignment."
)
async def update_my_availability(
    request: UpdateAvailabilityRequest,
    current_faculty: User = Depends(get_current_faculty),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Update current faculty's availability (faculty can only update own)."""
    try:
        # Convert DTO to service request
        service_request = ServiceUpdateAvailabilityRequest(
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            available_slots=[slot.model_dump() for slot in request.available_slots]
        )

        availability = await service.update_availability(
            service_request,
            current_faculty.id,
            current_faculty  # Faculty is both the requesting_user and the target
        )

        return AvailabilityResponse(
            available_slots=[
                SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
                for slot in availability.available_slots
            ]
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@faculty_router.get(
    "/availability/effective",
    response_model=EffectiveAvailabilityResponse,
    summary="Get effective availability (with overrides)",
    description="Get effective availability including base slots and admin-applied overrides. DEBUG: Shows breakdown of persistent vs one-time overrides."
)
async def get_my_effective_availability(
    subject_id: str = Query(..., description="Subject ID"),
    semester: int = Query(..., ge=1, le=8, description="Semester"),
    section: str = Query(..., min_length=1, max_length=2, description="Section"),
    current_faculty: User = Depends(get_current_faculty),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Get effective availability (base + admin overrides applied). DEBUG endpoint."""
    try:
        response: ServiceEffectiveAvailabilityResponse = await service.get_effective_availability(
            faculty_id=current_faculty.id,
            subject_id=subject_id,
            semester=semester,
            section=section,
            requesting_user=current_faculty
        )

        # Split overrides by type for debugging
        persistent_overrides = []
        one_time_overrides = []
        for override in response.applied_overrides:
            slots = [
                OverrideSlotDTO(
                    day=DayOfWeekEnum(s["day"]),
                    slot=s["slot"],
                    action=OverrideActionEnum(s["action"])
                )
                for s in override["slots"]
            ]
            detail = OverrideDetail(
                id=override["id"],
                override_type=override["type"],
                slots=slots,
                admin_id=override["admin_id"],
                timestamp=override["timestamp"],
                applied=override.get("applied", False)
            )
            if override["type"] == "persistent":
                persistent_overrides.append(detail)
            else:
                one_time_overrides.append(detail)

        return EffectiveAvailabilityResponse(
            base_slots=[
                SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
                for slot in response.base_slots
            ],
            effective_slots=[
                SlotDTO(day=DayOfWeekEnum(slot.day.value), slot=slot.slot)
                for slot in response.effective_slots
            ],
            persistent_overrides=persistent_overrides,
            one_time_overrides=one_time_overrides
        )

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@faculty_router.get(
    "/availability/occupied",
    summary="Get overlapping faculty availability for semester/section",
    description="Get slots also marked available by other faculty. Informational only; availability is not a reservation."
)
async def get_occupied_slots(
    semester: int = Query(..., ge=1, le=8, description="Semester"),
    section: str = Query(..., min_length=1, max_length=2, description="Section"),
    current_faculty: User = Depends(get_current_faculty),
    service: FacultyAvailabilityService = Depends(get_faculty_availability_service)
):
    """Get slots also marked available by other faculty for this semester/section."""
    try:
        occupied = await service.get_occupied_slots(
            semester=semester,
            section=section,
            exclude_faculty_id=current_faculty.id
        )

        # Convert to list format for frontend
        occupied_slots = [
            {
                "day": day,
                "slot": slot,
                "faculty_name": faculty_name
            }
            for (day, slot), faculty_name in occupied.items()
        ]

        return {
            "semester": semester,
            "section": section,
            "occupied_slots": occupied_slots
        }

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
