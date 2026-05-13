"""Faculty availability service for managing and computing availability."""

import logging
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from copy import deepcopy

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

from app.domain.entities.faculty_availability import (
    FacultyAvailability, AvailableSlot, DayOfWeek
)
from app.domain.entities.admin_override_log import (
    AdminOverrideLog, OverrideSlot, OverrideAction, OverrideType
)
from app.domain.entities.user import User, UserRole
from app.domain.exceptions import ValidationError, ResourceNotFoundError, AuthorizationError
from app.domain.interfaces.repositories import (
    IFacultyAvailabilityRepository,
    IAdminOverrideRepository,
    ISubjectAssignmentRepository,
    IUserRepository
)


@dataclass
class UpdateAvailabilityRequest:
    """Request to update faculty availability."""
    subject_id: str
    semester: int
    section: str
    available_slots: List[dict]  # List of {"day": "MON", "slot": 1}


@dataclass
class EffectiveAvailabilityResponse:
    """Response with effective availability (base + overrides)."""
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    base_slots: List[AvailableSlot]
    effective_slots: List[AvailableSlot]
    applied_overrides: List[dict]


class FacultyAvailabilityService:
    """Service for managing faculty availability with override support."""

    MIN_REQUIRED_SLOTS = 3  # Minimum slots a faculty must provide

    def __init__(
        self,
        availability_repo: IFacultyAvailabilityRepository,
        override_repo: IAdminOverrideRepository,
        assignment_repo: ISubjectAssignmentRepository,
        user_repo: IUserRepository,
        db: AsyncIOMotorDatabase
    ):
        self.availability_repo = availability_repo
        self.override_repo = override_repo
        self.assignment_repo = assignment_repo
        self.user_repo = user_repo
        self.db = db

    async def update_availability(
        self,
        request: UpdateAvailabilityRequest,
        faculty_id: str,
        current_user: User
    ) -> FacultyAvailability:
        """
        Update faculty availability with ownership check and min slots validation.

        Args:
            request: Availability update details
            faculty_id: ID of the faculty member
            current_user: User making the request

        Returns:
            Updated FacultyAvailability

        Raises:
            AuthorizationError: If current_user is not the faculty or admin
            ValidationError: If validation fails (min slots, assignment exists, etc.)
            ResourceNotFoundError: If faculty or subject not found
        """
        # Authorization: faculty can update own availability, admins can update any
        if current_user.role == UserRole.FACULTY and current_user.id != faculty_id:
            raise AuthorizationError(
                "Faculty members can only update their own availability"
            )
        elif current_user.role not in (UserRole.FACULTY, UserRole.ADMIN):
            raise AuthorizationError(
                "Unauthorized to update faculty availability"
            )

        # Verify faculty exists
        faculty = await self.user_repo.find_by_id(faculty_id)
        if not faculty or faculty.role != UserRole.FACULTY:
            raise ResourceNotFoundError("Faculty", faculty_id)

        # Validate slot count
        if len(request.available_slots) < self.MIN_REQUIRED_SLOTS:
            raise ValidationError(
                f"Must provide at least {self.MIN_REQUIRED_SLOTS} available slots"
            )

        # Verify the faculty is assigned to this subject
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section
        )

        if not assignment:
            raise ValidationError(
                "Faculty is not assigned to this subject for the given semester/section"
            )

        # Validate raw slot input before constructing domain entities so API
        # callers receive a clean ValidationError instead of a raw ValueError.
        available_slots = []
        for slot in request.available_slots:
            day = slot.get("day")
            slot_number = slot.get("slot")

            try:
                slot_number = int(slot_number)
            except (TypeError, ValueError):
                raise ValidationError(f"Slot must be an integer, got {slot_number}")

            if not 1 <= slot_number <= 10:
                raise ValidationError(f"Slot must be between 1 and 10, got {slot_number}")

            try:
                day_of_week = DayOfWeek(day)
            except ValueError:
                raise ValidationError(f"Invalid day of week: {day}")

            available_slots.append(
                AvailableSlot(
                    day=day_of_week,
                    slot=slot_number
                )
            )

        # Check for duplicates
        slot_keys = {(s.day.value, s.slot) for s in available_slots}
        if len(slot_keys) != len(available_slots):
            raise ValidationError("Duplicate slots detected")

        # Find existing or create new
        existing = await self.availability_repo.find(
            faculty_id=faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section
        )

        now = datetime.utcnow()

        if existing:
            # Update existing
            existing.available_slots = available_slots
            existing.updated_at = now
            return await self.availability_repo.update(existing)
        else:
            # Create new
            availability = FacultyAvailability(
                id=None,
                faculty_id=faculty_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section,
                available_slots=available_slots,
                created_at=now,
                updated_at=now
            )
            return await self.availability_repo.save(availability)

    async def get_occupied_slots(
        self,
        semester: int,
        section: str,
        exclude_faculty_id: Optional[str] = None
    ) -> dict:
        """
        Get slots that appear in other faculty availability for a semester/section.

        This is informational only. Faculty availability is not a reservation;
        the timetable generator resolves real scheduling conflicts later.

        Args:
            semester: Semester number
            section: Section identifier
            exclude_faculty_id: Optional faculty ID to exclude (e.g., current faculty)

        Returns:
            Dict with (day_value, slot_number) as key, faculty_name as value
        """
        # Get all availability records for this semester/section
        all_availability = await self.availability_repo.find_by_semester_and_section(
            semester=semester,
            section=section
        )

        occupied = {}
        for avail in all_availability:
            # Skip the excluded faculty (e.g., current faculty updating their own)
            if exclude_faculty_id and avail.faculty_id == exclude_faculty_id:
                continue

            # Get faculty name
            faculty = await self.user_repo.find_by_id(avail.faculty_id)
            faculty_name = faculty.full_name if faculty else f"Faculty_{avail.faculty_id[-4:]}"

            # Add each slot to the occupied map
            for slot in avail.available_slots:
                slot_key = (slot.day.value, slot.slot)
                occupied[slot_key] = faculty_name

        return occupied

    async def get_effective_availability(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str,
        requesting_user: Optional[User] = None
    ) -> EffectiveAvailabilityResponse:
        """
        Compute effective availability (base + overrides applied).

        Args:
            faculty_id: ID of the faculty member
            subject_id: ID of the subject
            semester: Semester number
            section: Section identifier
            requesting_user: User making the request (for authorization)

        Returns:
            EffectiveAvailabilityResponse with base and effective slots

        Raises:
            AuthorizationError: If requesting_user is not authorized
        """
        # Authorization check
        if requesting_user and requesting_user.role == UserRole.FACULTY:
            if requesting_user.id != faculty_id:
                raise AuthorizationError(
                    "Faculty members can only view their own availability"
                )

        # Get base availability
        logger.info(f"[DEBUG AVAILABILITY] Querying base availability for faculty_id={faculty_id}, subject_id={subject_id}, semester={semester}, section={section}")
        base = await self.availability_repo.find(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section
        )

        base_slots = base.available_slots if base else []
        logger.info(f"[DEBUG AVAILABILITY] Found {len(base_slots)} base slots")

        # Get applicable overrides
        logger.info(f"[DEBUG AVAILABILITY] Querying overrides for faculty_id={faculty_id}, subject_id={subject_id}, semester={semester}, section={section}")
        overrides = await self.override_repo.find_applicable(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section
        )
        logger.info(f"[DEBUG AVAILABILITY] Found {len(overrides)} applicable overrides")

        # Apply overrides to get effective slots
        effective_slots = self._apply_overrides(base_slots, overrides)

        # Dedupe and sort
        effective_slots = self._dedupe_and_sort(effective_slots)

        return EffectiveAvailabilityResponse(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section,
            base_slots=base_slots,
            effective_slots=effective_slots,
            applied_overrides=[
                {
                    "id": o.id,
                    "type": o.override_type.value,
                    "slots": [s.to_dict() for s in o.slots],
                    "admin_id": o.admin_id,
                    "timestamp": o.timestamp.isoformat(),
                    "applied": o.applied
                }
                for o in overrides
            ]
        )

    def _apply_overrides(
        self,
        base_slots: List[AvailableSlot],
        overrides: List[AdminOverrideLog]
    ) -> List[AvailableSlot]:
        """
        Apply overrides to base availability slots.

        - ADD action: Adds slot (if not exists)
        - REMOVE action: Removes slot (if exists)

        Args:
            base_slots: Base availability from faculty
            overrides: List of applicable overrides

        Returns:
            List of AvailableSlot after applying overrides
        """
        # Start with base slots
        effective: Set[Tuple[str, int]] = {
            (slot.day.value, slot.slot) for slot in base_slots
        }

        # Apply each override
        for override in overrides:
            for override_slot in override.slots:
                key = (override_slot.day.value, override_slot.slot)

                if override_slot.action == OverrideAction.ADD:
                    effective.add(key)
                elif override_slot.action == OverrideAction.REMOVE:
                    effective.discard(key)

        # Convert back to AvailableSlot objects
        return [
            AvailableSlot(day=DayOfWeek(day), slot=slot)
            for day, slot in effective
        ]

    def _dedupe_and_sort(self, slots: List[AvailableSlot]) -> List[AvailableSlot]:
        """
        Remove duplicates and sort slots by day then slot number.

        Args:
            slots: List of slots (may have duplicates)

        Returns:
            Deduplicated and sorted list of slots
        """
        # Dedupe using set
        seen: Set[Tuple[str, int]] = set()
        unique = []
        for slot in slots:
            key = (slot.day.value, slot.slot)
            if key not in seen:
                seen.add(key)
                unique.append(slot)

        # Sort by day (MON-FRI) then slot number
        day_order = {d.value: i for i, d in enumerate(DayOfWeek)}
        unique.sort(key=lambda s: (day_order[s.day.value], s.slot))

        return unique
