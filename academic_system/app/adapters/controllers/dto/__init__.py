"""DTOs for faculty assignment and availability APIs."""

from app.adapters.controllers.dto.faculty_assignment import (
    DayOfWeekEnum,
    OverrideActionEnum,
    OverrideTypeEnum,
    SlotDTO,
    OverrideSlotDTO,
    AssignSubjectRequest,
    UpdateAvailabilityRequest,
    CreateOverrideRequest,
    AssignmentResponse,
    FacultyAssignmentResponse,
    AvailabilityResponse,
    EffectiveAvailabilityResponse,
    OverrideLogResponse,
    OverrideResponse
)

__all__ = [
    "DayOfWeekEnum",
    "OverrideActionEnum",
    "OverrideTypeEnum",
    "SlotDTO",
    "OverrideSlotDTO",
    "AssignSubjectRequest",
    "UpdateAvailabilityRequest",
    "CreateOverrideRequest",
    "AssignmentResponse",
    "FacultyAssignmentResponse",
    "AvailabilityResponse",
    "EffectiveAvailabilityResponse",
    "OverrideLogResponse",
    "OverrideResponse"
]
