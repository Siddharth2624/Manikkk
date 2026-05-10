"""Admin override service for managing faculty availability overrides."""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.admin_override_log import (
    AdminOverrideLog, OverrideSlot, OverrideType, OverrideAction, DayOfWeek
)
from app.domain.entities.user import User, UserRole
from app.domain.exceptions import ValidationError, ResourceNotFoundError, AuthorizationError
from app.domain.interfaces.repositories import (
    IAdminOverrideRepository,
    IFacultyAvailabilityRepository,
    ISubjectAssignmentRepository,
    IUserRepository
)


@dataclass
class CreateOverrideRequest:
    """Request to create an availability override."""
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    override_type: str  # "persistent" or "one_time"
    slots: List[dict]  # List of {"day": "MON", "slot": 1, "action": "add"}


@dataclass
class OverrideResponse:
    """Response after creating an override."""
    override: AdminOverrideLog
    message: str


@dataclass
class AuditLogResponse:
    """Response for audit log query."""
    overrides: List[AdminOverrideLog]
    total_count: int


class AdminOverrideService:
    """Service for managing admin availability overrides."""

    def __init__(
        self,
        override_repo: IAdminOverrideRepository,
        availability_repo: IFacultyAvailabilityRepository,
        assignment_repo: ISubjectAssignmentRepository,
        user_repo: IUserRepository,
        db: AsyncIOMotorDatabase
    ):
        self.override_repo = override_repo
        self.availability_repo = availability_repo
        self.assignment_repo = assignment_repo
        self.user_repo = user_repo
        self.db = db

    async def create_override(
        self,
        request: CreateOverrideRequest,
        admin_id: str,
        current_user: User
    ) -> OverrideResponse:
        """
        Create an availability override with validation and logging.

        Args:
            request: Override details
            admin_id: ID of the admin creating the override
            current_user: User making the request (must be admin)

        Returns:
            OverrideResponse with created override

        Raises:
            AuthorizationError: If current_user is not admin
            ValidationError: If validation fails
            ResourceNotFoundError: If faculty or assignment not found
        """
        # Authorization check
        if current_user.role != UserRole.ADMIN:
            raise AuthorizationError(
                "Only administrators can create availability overrides"
            )

        # Validate override type
        try:
            override_type = OverrideType(request.override_type)
        except ValueError:
            raise ValidationError(
                f"Invalid override_type: {request.override_type}. "
                f"Must be 'persistent' or 'one_time'"
            )

        # Verify faculty exists
        faculty = await self.user_repo.find_by_id(request.faculty_id)
        if not faculty or faculty.role != UserRole.FACULTY:
            raise ResourceNotFoundError("Faculty", request.faculty_id)

        # Verify the faculty is assigned to this subject
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section
        )

        if not assignment:
            raise ValidationError(
                "Faculty is not assigned to this subject for the given semester/section"
            )

        # Validate and convert slots
        if not request.slots:
            raise ValidationError("At least one slot must be provided")

        override_slots = []
        slot_keys = set()

        for slot_data in request.slots:
            # Validate day
            try:
                day = DayOfWeek(slot_data["day"])
            except (KeyError, ValueError):
                raise ValidationError(
                    f"Invalid day: {slot_data.get('day', 'missing')}. "
                    f"Must be MON, TUE, WED, THU, FRI, or SAT"
                )

            # Validate slot number
            slot = slot_data.get("slot")
            if not isinstance(slot, int) or not 1 <= slot <= 10:
                raise ValidationError(
                    f"Invalid slot: {slot}. Must be an integer between 1 and 10"
                )

            # Validate action
            try:
                action = OverrideAction(slot_data["action"])
            except (KeyError, ValueError):
                raise ValidationError(
                    f"Invalid action: {slot_data.get('action', 'missing')}. "
                    f"Must be 'add' or 'remove'"
                )

            # Check for duplicates within request
            key = (day.value, slot, action.value)
            if key in slot_keys:
                raise ValidationError(
                    f"Duplicate slot entry: {day.value} slot {slot} {action.value}"
                )
            slot_keys.add(key)

            override_slots.append(OverrideSlot(
                day=day,
                slot=slot,
                action=action
            ))

        # Create the override log entry
        override = AdminOverrideLog(
            id=None,
            admin_id=admin_id,
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            override_type=override_type,
            applied=False,  # Will be marked True when timetable is generated
            slots=override_slots,
            timestamp=datetime.utcnow()
        )

        saved = await self.override_repo.save(override)

        action_desc = "added" if override_type == OverrideType.PERSISTENT else "added (one-time)"
        return OverrideResponse(
            override=saved,
            message=f"Override {action_desc} successfully for {faculty.full_name}"
        )

    async def get_audit_log(
        self,
        faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        current_user: Optional[User] = None
    ) -> AuditLogResponse:
        """
        Get audit log of overrides with optional filters.

        Args:
            faculty_id: Filter by faculty (optional)
            subject_id: Filter by subject (optional)
            from_date: Filter overrides after this date (optional)
            current_user: User making the request (must be admin)

        Returns:
            AuditLogResponse with list of overrides

        Raises:
            AuthorizationError: If current_user is not admin
        """
        # Authorization check
        if current_user and current_user.role != UserRole.ADMIN:
            raise AuthorizationError(
                "Only administrators can view the override audit log"
            )

        overrides = await self.override_repo.find_audit_log(
            faculty_id=faculty_id,
            subject_id=subject_id,
            from_date=from_date
        )

        return AuditLogResponse(
            overrides=overrides,
            total_count=len(overrides)
        )

    async def delete_override(
        self,
        override_id: str,
        current_user: User
    ) -> bool:
        """
        Delete an override by ID.

        Args:
            override_id: ID of the override to delete
            current_user: User making the request (must be admin)

        Returns:
            True if deleted, False otherwise

        Raises:
            AuthorizationError: If current_user is not admin
            ResourceNotFoundError: If override not found
        """
        # Authorization check
        if current_user.role != UserRole.ADMIN:
            raise AuthorizationError(
                "Only administrators can delete overrides"
            )

        # Verify override exists
        override = await self.override_repo.find_by_id(override_id)
        if not override:
            raise ResourceNotFoundError("Override", override_id)

        return await self.override_repo.delete(override_id)

    async def mark_generation_overrides_applied(
        self,
        semester: int,
        section: str,
        current_user: Optional[User] = None
    ) -> int:
        """
        Mark one-time overrides as applied after timetable generation.

        This is called by the timetable generator after successfully
        generating a timetable. Applied one-time overrides won't be
        used in future generations.

        Args:
            semester: Semester number
            section: Section identifier
            current_user: User making the request (must be admin)

        Returns:
            Number of overrides marked as applied

        Raises:
            AuthorizationError: If current_user is not admin
        """
        # Authorization check
        if current_user and current_user.role != UserRole.ADMIN:
            raise AuthorizationError(
                "Only administrators can mark overrides as applied"
            )

        return await self.override_repo.mark_one_time_applied(
            semester=semester,
            section=section
        )
