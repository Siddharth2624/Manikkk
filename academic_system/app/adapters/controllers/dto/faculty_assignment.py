"""DTOs for faculty assignment and availability APIs."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class DayOfWeekEnum(str, Enum):
    """Valid days for availability."""
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"


class OverrideActionEnum(str, Enum):
    """Override actions."""
    ADD = "add"
    REMOVE = "remove"


class OverrideTypeEnum(str, Enum):
    """Override types."""
    PERSISTENT = "persistent"
    ONE_TIME = "one_time"


# Request DTOs
class SlotDTO(BaseModel):
    day: DayOfWeekEnum
    slot: int = Field(ge=1, le=10)


class OverrideSlotDTO(BaseModel):
    day: DayOfWeekEnum
    slot: int = Field(ge=1, le=10)
    action: OverrideActionEnum


class AssignSubjectRequest(BaseModel):
    faculty_id: str
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)


class UpdateAvailabilityRequest(BaseModel):
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)
    available_slots: List[SlotDTO]


class CreateOverrideRequest(BaseModel):
    faculty_id: str
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)
    override_type: OverrideTypeEnum
    slots: List[OverrideSlotDTO]


# Response DTOs
class AssignmentResponse(BaseModel):
    id: str
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    created_at: datetime


class SubjectInfo(BaseModel):
    """Subject information nested in assignment response."""
    id: str
    code: str
    name: str
    credits: int = 3


class MySubjectResponse(BaseModel):
    """Response for faculty's assigned subjects endpoint - matches frontend expectations."""
    subject: SubjectInfo
    semester: int
    section: str
    available_slots: List[str] = []


class FacultyAssignmentResponse(BaseModel):
    id: str
    faculty_id: str
    faculty_name: str = ""
    faculty_email: str = ""
    subject_id: str
    subject_name: str = ""
    subject_code: str = ""
    semester: int
    section: str
    created_at: datetime


class AvailabilityResponse(BaseModel):
    available_slots: List[SlotDTO]


class OverrideDetail(BaseModel):
    """Detailed override information for debugging."""
    id: str
    override_type: str  # "persistent" or "one_time"
    slots: List[OverrideSlotDTO]
    admin_id: str
    timestamp: str
    applied: bool


class EffectiveAvailabilityResponse(BaseModel):
    base_slots: List[SlotDTO]
    effective_slots: List[SlotDTO]
    # Separated for debugging
    persistent_overrides: List[OverrideDetail]
    one_time_overrides: List[OverrideDetail]


class OverrideLogResponse(BaseModel):
    id: str
    faculty_id: str
    faculty_name: str = ""
    subject_id: str
    subject_name: str = ""
    semester: int
    section: str
    override_type: str
    slots: List[OverrideSlotDTO]
    admin_id: str
    admin_name: str = ""
    timestamp: datetime
    applied: bool


class OverrideResponse(BaseModel):
    id: str
    admin_id: str
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    override_type: str
    slots: List[OverrideSlotDTO]
    timestamp: datetime
    applied: bool
