"""Timetable use cases - updated for single-document schema with versioning."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.entities.timetable import (
    Timetable, TimetableSlot, DaySchedule, DayOfWeek
)
from app.domain.entities.subject import Subject
from app.domain.entities.feasibility import (
    FeasibilityReport,
    FeasibilityStatus,
    GenerationTelemetry,
    WarningCollection,
)
from app.domain.exceptions import FeasibilityError
from app.domain.interfaces.repositories import ISubjectRepository
from app.domain.interfaces.timetable_generator import ITimetableGenerator

logger = logging.getLogger(__name__)


@dataclass
class GenerateTimetableRequest:
    """Request to generate a timetable."""
    semester: int
    section: str
    subject_ids: List[str]
    faculty_availability: Dict[str, Dict[str, List[int]]]  # {faculty_id: {day: [slots]}}
    subject_faculty_map: Dict[str, str] = field(default_factory=dict)  # {subject_id: faculty_id}
    faculty_names: Dict[str, str] = field(default_factory=dict)  # {faculty_id: faculty_name}
    created_by: str = "system"  # User ID of creator


@dataclass
class GenerateTimetableResponse:
    """Response from timetable generation."""
    timetable: Timetable
    warnings: List[str] = field(default_factory=list)
    feasibility_warnings: Optional[WarningCollection] = None
    confidence_score: Optional[int] = None
    recoverability: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class ViewTimetableRequest:
    """Request to view a timetable."""
    semester: int
    section: str
    version: Optional[int] = None  # None = latest active version


@dataclass
class FacultyScheduleRequest:
    """Request to get faculty schedule."""
    faculty_id: str


@dataclass
class UpdateTimetableRequest:
    """Request to update an existing timetable slot."""
    timetable_id: str
    day: DayOfWeek
    slot: int
    subject_id: Optional[str]
    faculty_id: Optional[str]
    room: Optional[str]


@dataclass
class CreateVersionRequest:
    """Request to create a new version of a timetable."""
    semester: int
    section: str
    created_by: str


class TimetableUseCase:
    """Use case for timetable operations."""

    def __init__(
        self,
        subject_repository: ISubjectRepository,
        timetable_repository,  # TimetableRepository (no interface needed for new schema)
        timetable_generator: Optional[ITimetableGenerator] = None,
        assignment_repo=None,  # SubjectAssignmentRepository for auto-detection
        user_repo=None,  # UserRepository for fetching faculty details
        faculty_availability_repo=None,  # FacultyAvailabilityRepository for fetching availability
        availability_service=None,  # FacultyAvailabilityService for effective availability
        override_repo=None,  # AdminOverrideRepository for marking one-time overrides as applied
        feasibility_analyzer=None,  # FeasibilityAnalyzer for pre-generation analysis
        telemetry_repo=None  # GenerationTelemetryRepository for storing telemetry
    ):
        self.subject_repository = subject_repository
        self.timetable_repository = timetable_repository
        self.timetable_generator = timetable_generator
        self.assignment_repo = assignment_repo
        self.user_repo = user_repo
        self.faculty_availability_repo = faculty_availability_repo
        self.availability_service = availability_service
        self.override_repo = override_repo
        self.feasibility_analyzer = feasibility_analyzer
        self.telemetry_repo = telemetry_repo

    async def generate_timetable(
        self,
        request: GenerateTimetableRequest
    ) -> GenerateTimetableResponse:
        """
        Generate a timetable for the given parameters.

        Creates a new version (deactivates existing active versions).

        Args:
            request: Timetable generation request

        Returns:
            Generated timetable response

        Raises:
            ValueError: If generation fails
        """
        # Fetch subjects
        subjects = []
        for subject_id in request.subject_ids:
            subject = await self.subject_repository.find_by_id(subject_id)
            if subject:
                subjects.append(subject)

        if not subjects:
            raise ValueError("No valid subjects found")

        # Convert availability format (string days to DayOfWeek)
        availability = {}
        day_map = {
            "MON": DayOfWeek.MONDAY,
            "TUE": DayOfWeek.TUESDAY,
            "WED": DayOfWeek.WEDNESDAY,
            "THU": DayOfWeek.THURSDAY,
            "FRI": DayOfWeek.FRIDAY
        }

        for faculty_id, days in request.faculty_availability.items():
            availability[faculty_id] = {}
            for day_str, slots in days.items():
                day = day_map.get(day_str.upper())
                if day:
                    availability[faculty_id][day] = slots

        # Initialize validation result
        validation = {"valid": True, "warnings": [], "errors": []}

        # Use generator if provided
        if self.timetable_generator:
            # Update generator with subjects BEFORE validation
            if hasattr(self.timetable_generator, 'subjects'):
                self.timetable_generator.subjects = subjects

            validation = await self.timetable_generator.validate_constraints(
                semester=request.semester,
                sections=[request.section],
                subject_ids=request.subject_ids,
                faculty_availability=availability
            )

            if not validation["valid"]:
                raise ValueError(f"Validation failed: {', '.join(validation['errors'])}")

            occupied_slots = await self._get_semester_occupied_slots(
                semester=request.semester,
                exclude_section=request.section
            )

            generated = await self.timetable_generator.generate(
                semester=request.semester,
                sections=[request.section],
                subject_ids=request.subject_ids,
                faculty_availability=availability,
                subject_faculty_map=request.subject_faculty_map,
                faculty_names=request.faculty_names,
                occupied_slots=occupied_slots
            )
            # Extract schedule from generated result
            schedule = generated.schedule
            self._validate_daily_lunch_breaks(schedule)
        else:
            # Create empty schedule structure
            schedule = self._create_empty_schedule()

        # Create new Timetable entity
        timetable = Timetable(
            id="",  # Will be set on save
            semester=request.semester,
            section=request.section,
            version=1,  # Will be incremented on save
            is_active=True,
            schedule=schedule,
            created_by=request.created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Save (automatically deactivates old versions and sets version number)
        saved = await self.timetable_repository.save(timetable)

        # Mark one-time overrides as applied after successful generation
        # Note: This is best-effort. If marking fails, overrides will remain applied=false
        # and will be applied again in next generation. The ADD/REMOVE operations are
        # idempotent, so double-application is safe.
        if self.override_repo:
            try:
                await self.override_repo.mark_one_time_applied(
                    semester=request.semester,
                    section=request.section
                )
            except Exception as e:
                # Log but don't fail the generation - timetable is already saved
                logger.warning(f"Failed to mark one-time overrides as applied: {e}")

        return GenerateTimetableResponse(
            timetable=saved,
            warnings=validation.get("warnings", []) if self.timetable_generator else []
        )

    def _validate_daily_lunch_breaks(self, schedule: List[DaySchedule]) -> None:
        """Ensure each generated working day has exactly one lunch break."""
        for day_schedule in schedule:
            lunch_slots = [
                slot.slot
                for slot in day_schedule.slots
                if slot.is_lunch()
            ]

            if len(lunch_slots) != 1 or lunch_slots[0] not in {5, 6}:
                day = (
                    day_schedule.day.value
                    if hasattr(day_schedule.day, "value")
                    else str(day_schedule.day)
                )
                raise ValueError(
                    "Conflict: Invalid lunch placement for "
                    f"{day}. Exactly one lunch break is required in either "
                    "slot 5 (12:20 - 13:10) or slot 6 (13:10 - 14:00)."
                )

    async def _get_semester_occupied_slots(
        self,
        semester: int,
        exclude_section: str
    ) -> List[Dict[str, Any]]:
        """
        Return class slots already used by other active sections in the semester.

        The project models one classroom capacity per semester, so Section A and
        Section B cannot hold classes at the same day/slot.
        """
        find_active_by_semester = getattr(self.timetable_repository, "find_active_by_semester", None)
        if not callable(find_active_by_semester):
            return []

        timetables = await find_active_by_semester(
            semester=semester,
            exclude_section=exclude_section
        )
        if not isinstance(timetables, list):
            return []

        occupied = []
        subject_cache: Dict[str, Dict[str, Optional[str]]] = {}
        faculty_cache: Dict[str, Optional[str]] = {}

        async def _subject_info(subject_id: Optional[str]) -> Dict[str, Optional[str]]:
            if not subject_id:
                return {"name": None, "code": None, "subject_type": None}
            if subject_id not in subject_cache:
                subject_cache[subject_id] = {"name": None, "code": None, "subject_type": None}
                try:
                    subject = await self.subject_repository.find_by_id(subject_id)
                    if subject:
                        subject_cache[subject_id] = {
                            "name": subject.name,
                            "code": subject.code,
                            "subject_type": (
                                subject.subject_type.value
                                if hasattr(subject.subject_type, "value")
                                else str(subject.subject_type)
                            ),
                        }
                except Exception:
                    pass
            return subject_cache[subject_id]

        async def _faculty_name(faculty_id: Optional[str]) -> Optional[str]:
            if not faculty_id or not self.user_repo:
                return None
            if faculty_id not in faculty_cache:
                faculty_cache[faculty_id] = None
                try:
                    faculty = await self.user_repo.find_by_id(faculty_id)
                    if faculty:
                        faculty_cache[faculty_id] = faculty.full_name
                except Exception:
                    pass
            return faculty_cache[faculty_id]

        for timetable in timetables:
            for day_schedule in timetable.schedule:
                for slot in day_schedule.slots:
                    if not slot.subject_id:
                        continue
                    subject_info = await _subject_info(slot.subject_id)
                    faculty_name = await _faculty_name(slot.faculty_id)
                    occupied.append({
                        "day": day_schedule.day,
                        "slot": slot.slot,
                        "section": timetable.section,
                        "subject_id": slot.subject_id,
                        "faculty_id": slot.faculty_id,
                        "subject_name": subject_info.get("name"),
                        "subject_code": subject_info.get("code"),
                        "subject_type": subject_info.get("subject_type"),
                        "faculty_name": faculty_name,
                    })

        return occupied

    def _create_empty_schedule(self) -> List[DaySchedule]:
        """Create empty schedule structure for all days."""
        days = [
            DayOfWeek.MONDAY,
            DayOfWeek.TUESDAY,
            DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY,
            DayOfWeek.SATURDAY
        ]

        schedule = []
        for day in days:
            # Create 10 slots per day
            slots = [
                TimetableSlot(slot=i, subject_id=None, faculty_id=None, room=None)
                for i in range(1, 11)
            ]
            schedule.append(DaySchedule(day=day, slots=slots))

        return schedule

    async def view_timetable(
        self,
        request: ViewTimetableRequest
    ) -> Optional[Dict[str, Any]]:
        """
        View timetable for a semester and section.

        If version is specified, returns that version.
        Otherwise returns the active version with subject/faculty details joined.

        Args:
            request: View timetable request

        Returns:
            Timetable data with joined details if found, None otherwise
        """
        if request.version:
            # Get specific version
            all_versions = await self.timetable_repository.find_all_versions(
                semester=request.semester,
                section=request.section
            )
            for tt in all_versions:
                if tt.version == request.version:
                    return self._timetable_to_dict(tt)
            return None

        # Get active version with joined details
        return await self.timetable_repository.get_with_subject_details(
            semester=request.semester,
            section=request.section
        )

    def _timetable_to_dict(self, timetable: Timetable) -> Dict[str, Any]:
        """Convert Timetable entity to dictionary."""
        return {
            "id": timetable.id,
            "semester": timetable.semester,
            "section": timetable.section,
            "version": timetable.version,
            "is_active": timetable.is_active,
            "schedule": [
                {
                    "day": ds.day.value,
                    "slots": [
                        {
                            "slot": s.slot,
                            "subject_id": s.subject_id,
                            "faculty_id": s.faculty_id,
                            "room": s.room
                        }
                        for s in ds.slots
                    ]
                }
                for ds in timetable.schedule
            ],
            "created_by": timetable.created_by,
            "created_at": timetable.created_at.isoformat(),
            "updated_at": timetable.updated_at.isoformat()
        }

    async def get_faculty_schedule(
        self,
        request: FacultyScheduleRequest
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get schedule for a faculty member.

        Args:
            request: Faculty schedule request

        Returns:
            Schedule grouped by day with subject details
        """
        entries = await self.timetable_repository.find_by_faculty(request.faculty_id)

        # Group by day
        schedule = {}
        for entry in entries:
            day = entry["day"]
            if day not in schedule:
                schedule[day] = []

            schedule[day].append({
                "slot": entry["slot"],
                "time": self._slot_to_time(entry["slot"]),
                "subject_id": entry.get("subject_id"),
                "faculty_id": entry.get("faculty_id"),
                "room": entry.get("room"),
                "semester": entry["semester"],
                "section": entry["section"]
            })

        return schedule

    def _slot_to_time(self, slot: int) -> str:
        """Convert slot number to time string."""
        hour = 9 + (slot - 1) // 2
        minute = "00" if (slot - 1) % 2 == 0 else "30"
        return f"{hour}:{minute}"

    async def update_slot(
        self,
        request: UpdateTimetableRequest
    ) -> Optional[Timetable]:
        """
        Update a single slot in an existing timetable.

        Creates a new version to preserve history.

        Args:
            request: Update slot request

        Returns:
            Updated timetable if found, None otherwise
        """
        timetable = await self.timetable_repository.find_by_id(request.timetable_id)
        if not timetable:
            return None

        # Find and update the slot
        for day_schedule in timetable.schedule:
            if day_schedule.day == request.day:
                day_schedule.set_slot(
                    request.slot,
                    TimetableSlot(
                        slot=request.slot,
                        subject_id=request.subject_id,
                        faculty_id=request.faculty_id,
                        room=request.room
                    )
                )
                break

        # Save as new version (deactivates current, creates new)
        timetable.id = ""  # Clear ID to create new version
        return await self.timetable_repository.save(timetable)

    async def create_new_version(
        self,
        request: CreateVersionRequest
    ) -> Optional[Timetable]:
        """
        Create a new version of an existing timetable.

        Copies the current active timetable and increments version.

        Args:
            request: Create version request

        Returns:
            New timetable version if one existed, None otherwise
        """
        current = await self.timetable_repository.find_by_semester_and_section(
            semester=request.semester,
            section=request.section
        )

        if not current:
            return None

        # Create copy with new version
        new_timetable = Timetable(
            id="",  # Will be assigned on save
            semester=current.semester,
            section=current.section,
            version=current.version + 1,  # Will be set by repo
            is_active=True,
            schedule=current.schedule,  # Copy schedule
            created_by=request.created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        return await self.timetable_repository.save(new_timetable)

    async def activate_version(
        self,
        timetable_id: str,
        semester: int,
        section: str
    ) -> bool:
        """
        Activate a specific timetable version.

        Deactivates all other versions for this semester-section.

        Args:
            timetable_id: ID of timetable to activate
            semester: Semester number
            section: Section identifier

        Returns:
            True if successful, False otherwise
        """
        return await self.timetable_repository.activate_version(
            timetable_id=timetable_id,
            semester=semester,
            section=section
        )

    async def list_all_timetables(self) -> List[Dict[str, Any]]:
        """Get all semester-section combinations with active timetables."""
        return await self.timetable_repository.get_all_semesters_sections()

    async def list_versions(
        self,
        semester: int,
        section: str
    ) -> List[Dict[str, Any]]:
        """
        List all versions of a timetable.

        Args:
            semester: Semester number
            section: Section identifier

        Returns:
            List of timetable versions
        """
        timetables = await self.timetable_repository.find_all_versions(
            semester=semester,
            section=section
        )

        return [
            {
                "id": tt.id,
                "version": tt.version,
                "is_active": tt.is_active,
                "created_by": tt.created_by,
                "created_at": tt.created_at.isoformat(),
                "updated_at": tt.updated_at.isoformat()
            }
            for tt in timetables
        ]

    async def delete_timetable(
        self,
        semester: int,
        section: str
    ) -> int:
        """
        Delete all versions of a timetable.

        Args:
            semester: Semester number
            section: Section identifier

        Returns:
            Number of documents deleted
        """
        return await self.timetable_repository.delete_by_semester_and_section(
            semester=semester,
            section=section
        )

    async def check_conflicts(
        self,
        semester: int,
        section: str,
        day: DayOfWeek,
        slot: int
    ) -> List[Dict[str, Any]]:
        """
        Check for conflicts at a specific day and slot.

        Args:
            semester: Semester number
            section: Section identifier
            day: Day of week
            slot: Slot number

        Returns:
            List of conflicting entries
        """
        return await self.timetable_repository.find_conflicts(
            semester=semester,
            section=section,
            day=day,
            slot=slot
        )

    async def check_faculty_conflicts(
        self,
        faculty_id: str,
        day: DayOfWeek,
        slot: int,
        exclude_timetable_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check if faculty is already booked at this day/slot.

        Args:
            faculty_id: Faculty ID
            day: Day of week
            slot: Slot number
            exclude_timetable_id: Optional timetable ID to exclude

        Returns:
            List of conflicting timetables
        """
        return await self.timetable_repository.find_slot_conflicts_for_faculty(
            faculty_id=faculty_id,
            day=day,
            slot=slot,
            exclude_timetable_id=exclude_timetable_id
        )

    async def check_room_conflicts(
        self,
        room: str,
        day: DayOfWeek,
        slot: int,
        exclude_timetable_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check if room is already booked at this day/slot.

        Args:
            room: Room identifier
            day: Day of week
            slot: Slot number
            exclude_timetable_id: Optional timetable ID to exclude

        Returns:
            List of conflicting timetables
        """
        return await self.timetable_repository.find_slot_conflicts_for_room(
            room=room,
            day=day,
            slot=slot,
            exclude_timetable_id=exclude_timetable_id
        )

    async def get_assignments_for_timetable(
        self,
        semester: int,
        section: str
    ) -> List[Dict[str, Any]]:
        """
        Get subject assignments for a semester/section with faculty details.

        Args:
            semester: Semester number
            section: Section identifier

        Returns:
            List of assignments with subject and faculty details
        """
        if not self.assignment_repo or not self.user_repo:
            raise ValueError("Assignment repository not configured")

        # Get assignments for this semester/section
        assignments = await self.assignment_repo.find_all(
            semester=semester,
            section=section
        )

        result = []
        for assignment in assignments:
            # Get subject details
            subject = await self.subject_repository.find_by_id(assignment.subject_id)
            # Get faculty details
            faculty = await self.user_repo.find_by_id(assignment.faculty_id)

            result.append({
                "assignment_id": assignment.id,
                "subject_id": assignment.subject_id,
                "subject_name": subject.name if subject else "Unknown",
                "subject_code": subject.code if subject else "Unknown",
                "credits": subject.credits if subject else 0,
                "faculty_id": assignment.faculty_id,
                "faculty_name": faculty.full_name if faculty else "Unknown",
                "semester": assignment.semester,
                "section": assignment.section
            })

        return result

    async def detect_assignments_for_timetable(
        self,
        semester: int,
        section: str
    ) -> Dict[str, Any]:
        """
        Auto-detect subject IDs and faculty availability for timetable generation.

        Args:
            semester: Semester number
            section: Section identifier

        Returns:
            Dictionary with subject_ids, faculty_availability, and subject_faculty_map
        """
        if not self.assignment_repo:
            raise ValueError("Assignment repository not configured")

        # Get assignments for this semester/section
        assignments = await self.assignment_repo.find_all(
            semester=semester,
            section=section
        )

        if not assignments:
            raise ValueError(
                f"No subject assignments found for semester {semester}, "
                f"section {section}. "
                f"Please assign subjects to faculty first."
            )

        # Extract unique subject IDs and build subject->faculty mapping
        subject_ids = []
        subject_faculty_map = {}
        faculty_names = {}
        for assignment in assignments:
            subject_id = str(assignment.subject_id)
            faculty_id = str(assignment.faculty_id)
            if subject_id not in subject_ids:
                subject_ids.append(subject_id)
            subject_faculty_map[subject_id] = faculty_id
            # Fetch faculty name if not already cached
            if faculty_id not in faculty_names and self.user_repo:
                try:
                    faculty = await self.user_repo.find_by_id(faculty_id)
                    if faculty:
                        faculty_names[faculty_id] = faculty.full_name
                except Exception:
                    faculty_names[faculty_id] = f"Faculty_{faculty_id[-4:]}"
            elif faculty_id not in faculty_names:
                faculty_names[faculty_id] = f"Faculty_{faculty_id[-4:]}"

        # Build faculty availability using effective availability (base + overrides)
        faculty_availability = {}
        if self.availability_service:
            day_map = {
                "MON": DayOfWeek.MONDAY,
                "TUE": DayOfWeek.TUESDAY,
                "WED": DayOfWeek.WEDNESDAY,
                "THU": DayOfWeek.THURSDAY,
                "FRI": DayOfWeek.FRIDAY
            }

            for assignment in assignments:
                faculty_id = str(assignment.faculty_id)
                subject_id = str(assignment.subject_id)

                # DEBUG: Log query parameters
                logger.info(f"[DEBUG TIMETABLE] Getting effective availability for faculty_id={faculty_id}, subject_id={subject_id}, semester={semester}, section={section}")

                # Get EFFECTIVE availability (base + overrides applied)
                try:
                    effective_resp = await self.availability_service.get_effective_availability(
                        faculty_id=faculty_id,
                        subject_id=subject_id,
                        semester=semester,
                        section=section,
                        requesting_user=None
                    )

                    # DEBUG: Log response
                    if effective_resp:
                        logger.info(f"[DEBUG TIMETABLE] Got {len(effective_resp.effective_slots)} effective slots, {len(effective_resp.applied_overrides)} overrides applied")

                    if effective_resp and effective_resp.effective_slots:
                        if faculty_id not in faculty_availability:
                            faculty_availability[faculty_id] = {}

                        for slot in effective_resp.effective_slots:
                            day_str = day_map.get(slot.day.value) or slot.day.value
                            if day_str not in faculty_availability[faculty_id]:
                                faculty_availability[faculty_id][day_str] = []
                            faculty_availability[faculty_id][day_str].append(slot.slot)
                except Exception as e:
                    # If effective availability fails, fall back to no availability for this faculty
                    logger.warning(f"Could not get effective availability for {faculty_id}: {e}")
                    continue

        return {
            "subject_ids": subject_ids,
            "faculty_availability": faculty_availability,
            "subject_faculty_map": subject_faculty_map,
            "faculty_names": faculty_names
        }

    async def generate_timetable_simple(
        self,
        semester: int,
        section: str,
        created_by: str
    ) -> GenerateTimetableResponse:
        """
        Generate timetable with automatic detection (simplified version).

        Only requires semester and section.
        Automatically detects subjects, faculty, and their availability from assignments.
        Performs feasibility analysis before generation.

        Args:
            semester: Semester number
            section: Section identifier
            created_by: User ID of creator

        Returns:
            Generated timetable response with feasibility metadata

        Raises:
            ValueError: If no assignments found or generation fails
            FeasibilityError: If feasibility analysis fails
        """
        start_time = time.time()
        generation_seed = str(uuid.uuid4())

        # Auto-detect assignments
        detected = await self.detect_assignments_for_timetable(
            semester=semester,
            section=section
        )

        # Fetch subjects for feasibility analysis
        subjects = []
        for subject_id in detected["subject_ids"]:
            subject = await self.subject_repository.find_by_id(subject_id)
            if subject:
                subjects.append(subject)

        # Run feasibility analysis BEFORE generation
        feasibility_report: Optional[FeasibilityReport] = None
        constraint_scores = None

        logger.info(f"[DEBUG] feasibility_analyzer is None: {self.feasibility_analyzer is None}")

        if self.feasibility_analyzer:
            try:
                logger.info(f"[DEBUG] Running feasibility analysis for {len(subjects)} subjects")
                feasibility_report = await self.feasibility_analyzer.analyze(
                    semester=semester,
                    section=section,
                    subjects=subjects,
                    faculty_availability=detected["faculty_availability"],
                    subject_faculty_map=detected["subject_faculty_map"],
                    faculty_names=detected.get("faculty_names", {}),
                )
                logger.info(f"[DEBUG] Feasibility report status: {feasibility_report.status}, confidence: {feasibility_report.confidence_score}")

                # Raise FeasibilityError if status is FAIL
                if feasibility_report.status == FeasibilityStatus.FAIL:
                    logger.info(f"[DEBUG] Raising FeasibilityError due to FAIL status")
                    await self._store_generation_telemetry(
                        semester=semester,
                        section=section,
                        feasibility_confidence=feasibility_report.confidence_score,
                        generation_seed=generation_seed,
                        success=False,
                        duration_ms=int((time.time() - start_time) * 1000),
                        bottleneck_subjects=[],
                    )
                    raise FeasibilityError(
                        message=f"Feasibility analysis failed: {feasibility_report.status.value}",
                        report=feasibility_report
                    )

                # Attach constraint_scores for heuristic scheduling
                constraint_scores = feasibility_report.constraint_scores

            except FeasibilityError:
                # Re-raise FeasibilityError
                raise
            except Exception as e:
                # Log but don't fail on feasibility analysis errors
                logger.warning(f"Feasibility analysis failed: {e}")

        # Create generation request
        request = GenerateTimetableRequest(
            semester=semester,
            section=section,
            subject_ids=detected["subject_ids"],
            faculty_availability=detected["faculty_availability"],
            subject_faculty_map=detected["subject_faculty_map"],
            faculty_names=detected.get("faculty_names", {}),
            created_by=created_by
        )

        # Generate timetable
        response = await self.generate_timetable(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Attach feasibility metadata to response
        if feasibility_report:
            response.feasibility_warnings = feasibility_report.warnings
            response.confidence_score = feasibility_report.confidence_score
            response.recoverability = feasibility_report.recoverability.value if feasibility_report.recoverability else None
        response.duration_ms = duration_ms

        # Store telemetry after successful generation
        await self._store_generation_telemetry(
            semester=semester,
            section=section,
            feasibility_confidence=feasibility_report.confidence_score if feasibility_report else 50,
            generation_seed=generation_seed,
            success=True,
            duration_ms=duration_ms,
            bottleneck_subjects=[],
        )

        return response

    async def _store_generation_telemetry(
        self,
        semester: int,
        section: str,
        feasibility_confidence: int,
        generation_seed: str,
        success: bool,
        duration_ms: int,
        bottleneck_subjects: List[str],
    ) -> None:
        """
        Store generation telemetry if repository is configured.

        Stores telemetry for BOTH successful AND failed generations.
        """
        if not self.telemetry_repo:
            return

        telemetry = GenerationTelemetry(
            generation_timestamp=datetime.utcnow(),
            semester=semester,
            section=section,
            feasibility_confidence=feasibility_confidence,
            generation_seed=generation_seed,
            actual_attempts_used=1,  # Will be updated by generator if available
            success=success,
            duration_ms=duration_ms,
            bottleneck_subjects=bottleneck_subjects,
            total_backtracks=0,  # Will be updated by generator if available
            backtrack_by_reason={},  # Will be updated by generator if available
            conflict_hotspots=[],  # Will be updated by generator if available
        )

        try:
            await self.telemetry_repo.save(telemetry)
        except Exception as e:
            # Log but don't fail the generation on telemetry errors
            logger.warning(f"Failed to store generation telemetry: {e}")
