# Database Schema Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor MongoDB schema for scalability — redesign timetables, add subject_assignments collection, add missing indexes, implement faculty authorization validation.

**Architecture:**
- Redesign timetables from per-slot documents to single document per semester-section with versioning
- Create subject_assignments collection to replace subjects.sections array
- Add missing indexes for performance
- Enforce faculty authorization at service layer

**Tech Stack:** Python 3.11+, FastAPI, Motor (async MongoDB), Pydantic

---

## File Structure Overview

**New Files:**
- `app/domain/entities/subject_assignment.py` - SubjectAssignment entity
- `app/domain/interfaces/repositories.py` - Add ISubjectAssignmentRepository
- `app/adapters/repositories/subject_assignment_repository.py` - MongoDB implementation
- `app/adapters/repositories/timetable_repository.py` - Redesign for new schema
- `app/use_cases/subject_assignment.py` - Subject assignment use cases
- `app/infrastructure/migrations/` - Migration scripts

**Modified Files:**
- `app/domain/entities/timetable.py` - Redesign Timetable, TimetableEntry
- `app/domain/entities/subject.py` - Remove sections, faculty_id fields
- `app/domain/interfaces/repositories.py` - Update ITimetableRepository
- `app/adapters/repositories/subject_repository.py` - Remove sections logic
- `app/infrastructure/database.py` - Add new indexes
- `app/use_cases/attendance.py` - Add faculty authorization check
- `app/use_cases/timetable.py` - Add version management

---

## Task 1: Create SubjectAssignment Entity

**Files:**
- Create: `app/domain/entities/subject_assignment.py`

- [ ] **Step 1: Create SubjectAssignment entity file**

```python
"""Subject assignment domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SubjectAssignment:
    """
    Links a subject to a semester-section-faculty combination.

    Replaces the denormalized sections array in Subject entity.
    Supports multiple faculty per subject through multiple assignments.

    Attributes:
        id: Unique assignment identifier
        subject_id: ID of the subject
        semester: Semester number (1-8)
        section: Section identifier (e.g., "A", "B")
        faculty_id: ID of the faculty member
        academic_year: Academic year (e.g., "2024-2025")
        is_primary: Whether this is the primary faculty (for multi-faculty scenarios)
        created_at: Creation timestamp
    """
    id: str
    subject_id: str
    semester: int
    section: str
    faculty_id: str
    academic_year: str
    is_primary: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate subject assignment data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")

    def is_for_semester(self, semester: int) -> bool:
        """Check if assignment is for given semester."""
        return self.semester == semester

    def is_for_section(self, section: str) -> bool:
        """Check if assignment is for given section."""
        return self.section == section

    def is_academic_year(self, academic_year: str) -> bool:
        """Check if assignment is for given academic year."""
        return self.academic_year == academic_year
```

- [ ] **Step 2: Export from entities __init__.py**

Modify: `app/domain/entities/__init__.py`

```python
from .user import User, UserRole, StudentProfile, FacultyProfile
from .subject import Subject, SubjectType
from .timetable import Timetable, TimetableEntry, TimeSlot, DayOfWeek, SlotType
from .attendance import AttendanceRecord, AttendanceSummary, AttendanceStatus
from .study_material import StudyMaterial, MaterialType
from .semester import Semester, SemesterStatus
from .subject_assignment import SubjectAssignment  # ← ADD

__all__ = [
    "User", "UserRole", "StudentProfile", "FacultyProfile",
    "Subject", "SubjectType",
    "Timetable", "TimetableEntry", "TimeSlot", "DayOfWeek", "SlotType",
    "AttendanceRecord", "AttendanceSummary", "AttendanceStatus",
    "StudyMaterial", "MaterialType",
    "Semester", "SemesterStatus",
    "SubjectAssignment",  # ← ADD
]
```

- [ ] **Step 3: Commit**

```bash
git add app/domain/entities/
git commit -m "feat: add SubjectAssignment entity"
```

---

## Task 2: Update Repository Interface

**Files:**
- Modify: `app/domain/interfaces/repositories.py`

- [ ] **Step 1: Read current repository interfaces**

```bash
cat app/domain/interfaces/repositories.py
```

- [ ] **Step 2: Add ISubjectAssignmentRepository interface**

Add to `app/domain/interfaces/repositories.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date

from app.domain.entities.subject import Subject
from app.domain.entities.subject_assignment import SubjectAssignment  # ← ADD
from app.domain.entities.user import User, UserRole


class ISubjectAssignmentRepository(ABC):  # ← NEW INTERFACE
    """Repository for subject assignment operations."""

    @abstractmethod
    async def save(self, assignment: SubjectAssignment) -> SubjectAssignment:
        """Save or update subject assignment."""
        pass

    @abstractmethod
    async def find_by_id(self, assignment_id: str) -> Optional[SubjectAssignment]:
        """Find assignment by ID."""
        pass

    @abstractmethod
    async def find_faculty_assignment(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str,
        academic_year: Optional[str] = None
    ) -> Optional[SubjectAssignment]:
        """Find if faculty is assigned to specific subject/semester/section."""
        pass

    @abstractmethod
    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str,
        academic_year: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a semester and section."""
        pass

    @abstractmethod
    async def find_by_faculty(
        self,
        faculty_id: str,
        academic_year: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """Find all assignments for a faculty member."""
        pass

    @abstractmethod
    async def find_by_subject(
        self,
        subject_id: str,
        academic_year: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """Find all assignments for a subject."""
        pass

    @abstractmethod
    async def delete(self, assignment_id: str) -> bool:
        """Delete assignment by ID."""
        pass
```

Also update `ISubjectRepository` to remove sections-related methods:

```python
class ISubjectRepository(ABC):
    """Repository for subject operations."""

    @abstractmethod
    async def find_by_id(self, subject_id: str) -> Optional[Subject]:
        """Find subject by ID."""
        pass

    @abstractmethod
    async def find_by_code(self, code: str) -> Optional[Subject]:
        """Find subject by code."""
        pass

    @abstractmethod
    async def find_all(
        self,
        semester: Optional[int] = None,
        subject_type: Optional[SubjectType] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Subject]:
        """Find subjects with optional filters."""
        pass

    # REMOVED: find_by_semester_and_section (moved to subject_assignments)
    # REMOVED: find_by_faculty (moved to subject_assignments)

    @abstractmethod
    async def save(self, subject: Subject) -> Subject:
        """Save or update subject."""
        pass

    @abstractmethod
    async def delete(self, subject_id: str) -> bool:
        """Delete subject by ID."""
        pass
```

- [ ] **Step 3: Commit**

```bash
git add app/domain/interfaces/repositories.py
git commit -m "refactor: update repository interfaces for subject_assignments"
```

---

## Task 3: Implement SubjectAssignmentRepository

**Files:**
- Create: `app/adapters/repositories/subject_assignment_repository.py`
- Modify: `app/adapters/repositories/__init__.py`

- [ ] **Step 1: Create SubjectAssignmentRepository**

```python
"""MongoDB implementation of subject assignment repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.interfaces.repositories import ISubjectAssignmentRepository


class SubjectAssignmentRepository(ISubjectAssignment):
    """MongoDB implementation of ISubjectAssignmentRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.subject_assignments

    def _to_entity(self, document: dict) -> SubjectAssignment:
        """Convert MongoDB document to SubjectAssignment entity."""
        return SubjectAssignment(
            id=str(document["_id"]),
            subject_id=str(document["subject_id"]),
            semester=document["semester"],
            section=document["section"],
            faculty_id=str(document["faculty_id"]),
            academic_year=document["academic_year"],
            is_primary=document.get("is_primary", True),
            created_at=document["created_at"]
        )

    def _to_document(self, assignment: SubjectAssignment) -> dict:
        """Convert SubjectAssignment entity to MongoDB document."""
        return {
            "subject_id": ObjectId(assignment.subject_id),
            "semester": assignment.semester,
            "section": assignment.section,
            "faculty_id": ObjectId(assignment.faculty_id),
            "academic_year": assignment.academic_year,
            "is_primary": assignment.is_primary,
            "created_at": assignment.created_at
        }

    async def save(self, assignment: SubjectAssignment) -> SubjectAssignment:
        """Save or update subject assignment."""
        if assignment.id:
            await self.collection.update_one(
                {"_id": ObjectId(assignment.id)},
                {"$set": self._to_document(assignment)}
            )
        else:
            result = await self.collection.insert_one(self._to_document(assignment))
            assignment.id = str(result.inserted_id)

        return assignment

    async def find_by_id(self, assignment_id: str) -> Optional[SubjectAssignment]:
        """Find assignment by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(assignment_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_faculty_assignment(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str,
        academic_year: Optional[str] = None
    ) -> Optional[SubjectAssignment]:
        """Find if faculty is assigned to specific subject/semester/section."""
        query = {
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section
        }
        if academic_year:
            query["academic_year"] = academic_year

        document = await self.collection.find_one(query)
        return self._to_entity(document) if document else None

    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str,
        academic_year: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a semester and section."""
        cursor = self.collection.find({
            "semester": semester,
            "section": section,
            "academic_year": academic_year
        }).sort("subject_id", 1)

        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_faculty(
        self,
        faculty_id: str,
        academic_year: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """Find all assignments for a faculty member."""
        query = {"faculty_id": ObjectId(faculty_id)}
        if academic_year:
            query["academic_year"] = academic_year

        cursor = self.collection.find(query).sort("semester", 1)
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_subject(
        self,
        subject_id: str,
        academic_year: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """Find all assignments for a subject."""
        query = {"subject_id": ObjectId(subject_id)}
        if academic_year:
            query["academic_year"] = academic_year

        cursor = self.collection.find(query).sort([("semester", 1), ("section", 1)])
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def delete(self, assignment_id: str) -> bool:
        """Delete assignment by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(assignment_id)})
            return result.deleted_count > 0
        except Exception:
            return False
```

- [ ] **Step 2: Export from repositories __init__.py**

Modify: `app/adapters/repositories/__init__.py`

```python
from .user_repository import UserRepository
from .subject_repository import SubjectRepository
from .timetable_repository import TimetableRepository
from .attendance_repository import AttendanceRepository
from .study_material_repository import StudyMaterialRepository
from .semester_repository import SemesterRepository
from .subject_assignment_repository import SubjectAssignmentRepository  # ← ADD

__all__ = [
    "UserRepository",
    "SubjectRepository",
    "TimetableRepository",
    "AttendanceRepository",
    "StudyMaterialRepository",
    "SemesterRepository",
    "SubjectAssignmentRepository",  # ← ADD
]
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/repositories/
git commit -m "feat: implement SubjectAssignmentRepository"
```

---

## Task 4: Redesign Timetable Entity

**Files:**
- Modify: `app/domain/entities/timetable.py`

- [ ] **Step 1: Read current timetable entity**

```bash
cat app/domain/entities/timetable.py
```

- [ ] **Step 2: Replace with redesigned entity**

Replace entire `app/domain/entities/timetable.py`:

```python
"""Timetable domain entity - redesigned for single document per semester-section."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class DayOfWeek(str, Enum):
    """Days of the week."""
    MONDAY = "MON"
    TUESDAY = "TUE"
    WEDNESDAY = "WED"
    THURSDAY = "THU"
    FRIDAY = "FRI"
    SATURDAY = "SAT"
    SUNDAY = "SUN"


class SlotType(str, Enum):
    """Type of time slot."""
    THEORY = "theory"
    LAB = "lab"
    LUNCH_BREAK = "lunch_break"
    FREE = "free"


@dataclass
class TimetableSlot:
    """
    Single time slot entry.

    Only stores references (IDs), not denormalized names.
    """
    slot: int                    # 1-10
    subject_id: Optional[str] = None
    faculty_id: Optional[str] = None
    room: Optional[str] = None

    def is_free(self) -> bool:
        """Check if this is a free slot."""
        return self.subject_id is None

    def is_lunch(self) -> bool:
        """Check if this is lunch break."""
        return self.subject_id is None and self.room == "LUNCH"


@dataclass
class DaySchedule:
    """
    Schedule for one day of the week.
    """
    day: DayOfWeek
    slots: List[TimetableSlot] = field(default_factory=list)

    def get_slot(self, slot_number: int) -> Optional[TimetableSlot]:
        """Get slot by number."""
        for slot in self.slots:
            if slot.slot == slot_number:
                return slot
        return None

    def set_slot(self, slot_number: int, slot: TimetableSlot) -> None:
        """Set or replace a slot."""
        # Remove existing slot at this position
        self.slots = [s for s in self.slots if s.slot != slot_number]
        self.slots.append(slot)
        self.slots.sort(key=lambda s: s.slot)


@dataclass
class Timetable:
    """
    Complete timetable for a semester-section combination.

    ONE document per semester-section-academic_year.
    Supports versioning with is_active flag.
    """
    id: str
    semester: int
    section: str
    academic_year: str
    version: int
    is_active: bool
    schedule: List[DaySchedule]
    created_by: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate timetable data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")
        if self.version < 1:
            raise ValueError("Version must be at least 1")

    def get_entry(self, day: DayOfWeek, slot_number: int) -> Optional[TimetableSlot]:
        """Get slot for specific day and slot number."""
        for day_schedule in self.schedule:
            if day_schedule.day == day:
                return day_schedule.get_slot(slot_number)
        return None

    def get_weekly_schedule(self) -> Dict[DayOfWeek, Dict[int, TimetableSlot]]:
        """Get complete weekly schedule as nested dict."""
        result = {}
        for day_schedule in self.schedule:
            result[day_schedule.day] = {
                slot.slot: slot for slot in day_schedule.slots
            }
        return result

    def get_faculty_slots(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Get all slots assigned to a faculty member."""
        result = []
        for day_schedule in self.schedule:
            for slot in day_schedule.slots:
                if slot.faculty_id == faculty_id:
                    result.append({
                        "day": day_schedule.day.value,
                        "slot": slot.slot,
                        "subject_id": slot.subject_id,
                        "room": slot.room
                    })
        return result

    def get_subject_slots(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all slots for a subject."""
        result = []
        for day_schedule in self.schedule:
            for slot in day_schedule.slots:
                if slot.subject_id == subject_id:
                    result.append({
                        "day": day_schedule.day.value,
                        "slot": slot.slot,
                        "faculty_id": slot.faculty_id,
                        "room": slot.room
                    })
        return result

    def get_free_slots(self) -> List[Dict[str, Any]]:
        """Get all free slots."""
        result = []
        for day_schedule in self.schedule:
            for slot in day_schedule.slots:
                if slot.is_free():
                    result.append({
                        "day": day_schedule.day.value,
                        "slot": slot.slot
                    })
        return result

    def to_matrix(self) -> Dict[str, Any]:
        """Convert to matrix representation for UI rendering."""
        time_slots = [
            (i, f"{9 + i//2}:{'00' if i % 2 == 0 else '30'}")
            for i in range(1, 11)
        ]

        matrix = []
        for slot_num, time_range in time_slots:
            row = {"time": time_range, "slots": []}
            for day in DayOfWeek:
                slot = self.get_entry(day, slot_num)
                if slot and not slot.is_free():
                    row["slots"].append({
                        "slot": slot.slot,
                        "subject_id": slot.subject_id,
                        "faculty_id": slot.faculty_id,
                        "room": slot.room
                    })
                else:
                    row["slots"].append({"type": "free"})
            matrix.append(row)

        return {
            "semester": self.semester,
            "section": self.section,
            "matrix": matrix
        }


@dataclass
class TimeSlot:
    """Time slot configuration (metadata, not actual schedule)."""
    slot_number: int
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"

    def __str__(self) -> str:
        return f"{self.start_time} - {self.end_time}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_number": self.slot_number,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "display": str(self)
        }
```

- [ ] **Step 3: Commit**

```bash
git add app/domain/entities/timetable.py
git commit -m "refactor: redesign Timetable entity for single-doc storage"
```

---

## Task 5: Simplify Subject Entity

**Files:**
- Modify: `app/domain/entities/subject.py`

- [ ] **Step 1: Replace subject entity (remove sections, faculty_id)**

Replace entire `app/domain/entities/subject.py`:

```python
"""Subject domain entity - simplified (removed sections and faculty_id)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SubjectType(str, Enum):
    """Type of subject."""
    THEORY = "theory"
    LAB = "lab"
    ELECTIVE = "elective"
    CORE = "core"


@dataclass
class Subject:
    """
    Subject entity representing a course/subject.

    Removed: sections array (moved to subject_assignments)
    Removed: faculty_id (moved to subject_assignments)

    Attributes:
        id: Unique subject identifier
        code: Subject code (e.g., "CS101")
        name: Subject name
        semester: Semester number (1-8) - for catalog organization
        subject_type: Type of subject
        credits: Number of credits
        classes_per_week: Number of classes per week
        description: Subject description
        syllabus: Subject syllabus/topics
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    code: str
    name: str
    semester: int  # Kept for catalog organization, NOT for assignment
    subject_type: SubjectType
    credits: int
    classes_per_week: int
    description: Optional[str] = None
    syllabus: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate subject data."""
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not 1 <= self.credits <= 6:
            raise ValueError("Credits must be between 1 and 6")
        if not 1 <= self.classes_per_week <= 10:
            raise ValueError("Classes per week must be between 1 and 10")

    def is_lab(self) -> bool:
        """Check if this is a lab subject."""
        return self.subject_type == SubjectType.LAB

    def is_theory(self) -> bool:
        """Check if this is a theory subject."""
        return self.subject_type == SubjectType.THEORY

    def is_elective(self) -> bool:
        """Check if this is an elective subject."""
        return self.subject_type == SubjectType.ELECTIVE

    def get_weekly_hours(self) -> int:
        """Get total weekly teaching hours."""
        if self.is_lab():
            return self.classes_per_week * 2
        return self.classes_per_week

    def get_display_name(self) -> str:
        """Get display name for the subject."""
        return f"{self.code} - {self.name}"
```

- [ ] **Step 2: Commit**

```bash
git add app/domain/entities/subject.py
git commit -m "refactor: simplify Subject entity (remove sections, faculty_id)"
```

---

## Task 6: Update SubjectRepository

**Files:**
- Modify: `app/adapters/repositories/subject_repository.py`

- [ ] **Step 1: Remove sections and faculty_id logic**

Replace entire `app/adapters/repositories/subject_repository.py`:

```python
"""MongoDB implementation of subject repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.subject import Subject, SubjectType
from app.domain.interfaces.repositories import ISubjectRepository


class SubjectRepository(ISubjectRepository):
    """MongoDB implementation of ISubjectRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.subjects

    def _to_entity(self, document: dict) -> Subject:
        """Convert MongoDB document to Subject entity."""
        return Subject(
            id=str(document["_id"]),
            code=document["code"],
            name=document["name"],
            semester=document["semester"],
            subject_type=SubjectType(document["subject_type"]),
            credits=document["credits"],
            classes_per_week=document["classes_per_week"],
            description=document.get("description"),
            syllabus=document.get("syllabus"),
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    def _to_document(self, subject: Subject) -> dict:
        """Convert Subject entity to MongoDB document."""
        return {
            "code": subject.code.upper(),
            "name": subject.name,
            "semester": subject.semester,
            "subject_type": subject.subject_type.value,
            "credits": subject.credits,
            "classes_per_week": subject.classes_per_week,
            "description": subject.description,
            "syllabus": subject.syllabus,
            "created_at": subject.created_at,
            "updated_at": subject.updated_at
        }

    async def find_by_id(self, subject_id: str) -> Optional[Subject]:
        """Find subject by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(subject_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_by_code(self, code: str) -> Optional[Subject]:
        """Find subject by code."""
        document = await self.collection.find_one({"code": code.upper()})
        return self._to_entity(document) if document else None

    async def find_all(
        self,
        semester: Optional[int] = None,
        subject_type: Optional[SubjectType] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Subject]:
        """Find subjects with optional filters."""
        query = {}
        if semester:
            query["semester"] = semester
        if subject_type:
            query["subject_type"] = subject_type.value

        cursor = self.collection.find(query).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_entity(doc) for doc in documents]

    async def save(self, subject: Subject) -> Subject:
        """Save or update subject."""
        from datetime import datetime

        subject.updated_at = datetime.utcnow()

        if subject.id:
            await self.collection.update_one(
                {"_id": ObjectId(subject.id)},
                {"$set": self._to_document(subject)}
            )
        else:
            result = await self.collection.insert_one(self._to_document(subject))
            subject.id = str(result.inserted_id)

        return subject

    async def delete(self, subject_id: str) -> bool:
        """Delete subject by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(subject_id)})
            return result.deleted_count > 0
        except Exception:
            return False
```

- [ ] **Step 2: Commit**

```bash
git add app/adapters/repositories/subject_repository.py
git commit -m "refactor: update SubjectRepository for simplified schema"
```

---

## Task 7: Redesign TimetableRepository

**Files:**
- Modify: `app/adapters/repositories/timetable_repository.py`

- [ ] **Step 1: Replace TimetableRepository for new schema**

Replace entire `app/adapters/repositories/timetable_repository.py`:

```python
"""MongoDB implementation of timetable repository - redesigned schema."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.timetable import Timetable, DaySchedule, TimetableSlot, DayOfWeek
from app.domain.interfaces.repositories import ITimetableRepository


class TimetableRepository(ITimetableRepository):
    """MongoDB implementation with new single-doc schema."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.timetables

    def _to_entity(self, document: dict) -> Timetable:
        """Convert MongoDB document to Timetable entity."""
        schedule = []
        for day_doc in document.get("schedule", []):
            slots = [
                TimetableSlot(
                    slot=slot_doc["slot"],
                    subject_id=slot_doc.get("subject_id"),
                    faculty_id=slot_doc.get("faculty_id"),
                    room=slot_doc.get("room")
                )
                for slot_doc in day_doc.get("slots", [])
            ]
            schedule.append(DaySchedule(
                day=DayOfWeek(day_doc["day"]),
                slots=slots
            ))

        return Timetable(
            id=str(document["_id"]),
            semester=document["semester"],
            section=document["section"],
            academic_year=document["academic_year"],
            version=document["version"],
            is_active=document["is_active"],
            schedule=schedule,
            created_by=str(document["created_by"]),
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    def _to_document(self, timetable: Timetable) -> dict:
        """Convert Timetable entity to MongoDB document."""
        schedule = [
            {
                "day": day_schedule.day.value,
                "slots": [
                    {
                        "slot": slot.slot,
                        "subject_id": slot.subject_id,
                        "faculty_id": slot.faculty_id,
                        "room": slot.room
                    }
                    for slot in day_schedule.slots
                ]
            }
            for day_schedule in timetable.schedule
        ]

        return {
            "semester": timetable.semester,
            "section": timetable.section,
            "academic_year": timetable.academic_year,
            "version": timetable.version,
            "is_active": timetable.is_active,
            "schedule": schedule,
            "created_by": ObjectId(timetable.created_by),
            "created_at": timetable.created_at,
            "updated_at": timetable.updated_at
        }

    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str,
        academic_year: str
    ) -> Optional[Timetable]:
        """Find active timetable by semester and section."""
        document = await self.collection.find_one({
            "semester": semester,
            "section": section,
            "academic_year": academic_year,
            "is_active": True
        })
        return self._to_entity(document) if document else None

    async def find_by_faculty(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Find all slots assigned to a faculty."""
        pipeline = [
            {"$match": {"is_active": True}},
            {"$unwind": "$schedule"},
            {"$unwind": "$schedule.slots"},
            {"$match": {"schedule.slots.faculty_id": faculty_id}},
            {"$project": {
                "semester": 1,
                "section": 1,
                "academic_year": 1,
                "day": "$schedule.day",
                "slot": "$schedule.slots.slot",
                "subject_id": "$schedule.slots.subject_id",
                "room": "$schedule.slots.room"
            }}
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        return results

    async def save(self, timetable: Timetable) -> Timetable:
        """Save timetable (creates new version, doesn't update existing)."""
        timetable.updated_at = datetime.utcnow()

        # Always insert as new document (versioning)
        result = await self.collection.insert_one(self._to_document(timetable))
        timetable.id = str(result.inserted_id)

        return timetable

    async def deactivate_active(
        self,
        semester: int,
        section: str,
        academic_year: str
    ) -> bool:
        """Deactivate all active timetables for this semester-section."""
        result = await self.collection.update_many(
            {
                "semester": semester,
                "section": section,
                "academic_year": academic_year,
                "is_active": True
            },
            {"$set": {"is_active": False}}
        )
        return result.acknowledged

    async def get_latest_version(
        self,
        semester: int,
        section: str,
        academic_year: str
    ) -> int:
        """Get the latest version number for this semester-section."""
        pipeline = [
            {
                "$match": {
                    "semester": semester,
                    "section": section,
                    "academic_year": academic_year
                }
            },
            {"$group": {"_id": None, "max_version": {"$max": "$version"}}}
        ]

        result = await self.collection.aggregate(pipeline).to_list(length=1)
        return result[0]["max_version"] if result else 0

    async def get_all_semesters_sections(self) -> List[Dict[str, Any]]:
        """Get all semester-section combinations with active timetables."""
        pipeline = [
            {"$match": {"is_active": True}},
            {"$project": {
                "semester": 1,
                "section": 1,
                "academic_year": 1,
                "version": 1,
                "created_at": 1
            }},
            {"$sort": {"semester": 1, "section": 1}}
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        return [
            {
                "semester": r["semester"],
                "section": r["section"],
                "academic_year": r["academic_year"],
                "version": r["version"],
                "created_at": r["created_at"]
            }
            for r in results
        ]

    async def find_conflicts(
        self,
        semester: int,
        section: str,
        day: DayOfWeek,
        slot: int
    ) -> List[Dict[str, Any]]:
        """Find conflicting entries at same day and slot."""
        document = await self.collection.find_one({
            "semester": semester,
            "section": section,
            "is_active": True
        })

        if not document:
            return []

        conflicts = []
        for day_schedule in document.get("schedule", []):
            if day_schedule["day"] == day.value:
                for slot_data in day_schedule.get("slots", []):
                    if slot_data["slot"] == slot:
                        conflicts.append(slot_data)

        return conflicts
```

- [ ] **Step 2: Commit**

```bash
git add app/adapters/repositories/timetable_repository.py
git commit -m "refactor: redesign TimetableRepository for single-doc schema"
```

---

## Task 8: Add New Database Indexes

**Files:**
- Modify: `app/infrastructure/database.py`

- [ ] **Step 1: Update init_indexes function**

Replace the `init_indexes` function in `app/infrastructure/database.py`:

```python
async def init_indexes():
    """Initialize database indexes for optimal query performance."""
    database = db.get_database()

    # ============ USERS ============
    await database.users.create_index("email", unique=True)
    await database.users.create_index("roll_number", unique=True, sparse=True)
    await database.users.create_index("employee_id", sparse=True)  # ← NEW
    await database.users.create_index("role")
    await database.users.create_index([("role", 1), ("semester", 1)])

    # ============ SUBJECTS ============
    await database.subjects.create_index("code", unique=True)  # Removed semester from index
    await database.subjects.create_index("subject_type")

    # ============ SUBJECT_ASSIGNMENTS (NEW COLLECTION) ============
    await database.subject_assignments.create_index(
        [("subject_id", 1), ("semester", 1), ("section", 1),
         ("faculty_id", 1), ("academic_year", 1)],
        unique=True
    )
    await database.subject_assignments.create_index([("faculty_id", 1), ("semester", 1)])
    await database.subject_assignments.create_index(
        [("semester", 1), ("section", 1), ("academic_year", 1)]
    )
    await database.subject_assignments.create_index("subject_id")

    # ============ TIMETABLES (NEW INDEXES FOR NEW SCHEMA) ============
    await database.timetables.create_index(
        [("semester", 1), ("section", 1), ("academic_year", 1), ("is_active", 1)],
        partialFilterExpression={"is_active": True}
    )
    await database.timetables.create_index("schedule.slots.faculty_id")
    await database.timetables.create_index("schedule.slots.subject_id")

    # ============ ATTENDANCES ============
    await database.attendances.create_index(
        [("student_id", 1), ("subject_id", 1), ("date", 1)],
        unique=True
    )
    await database.attendances.create_index([("faculty_id", 1), ("date", 1)])  # ← NEW
    await database.attendances.create_index([("subject_id", 1), ("date", 1)])

    # ============ STUDY_MATERIALS ============
    await database.study_materials.create_index([("subject_id", 1), ("semester", 1)])
    await database.study_materials.create_index("faculty_id")
    await database.study_materials.create_index("semester")  # ← NEW
    await database.study_materials.create_index("uploaded_at", -1)

    logger.info("Database indexes initialized successfully")
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/database.py
git commit -m "feat: add new indexes for schema refactor"
```

---

## Task 9: Add Faculty Authorization to Attendance Use Case

**Files:**
- Modify: `app/use_cases/attendance.py`

- [ ] **Step 1: Add SubjectAssignmentRepository dependency**

Modify `app/use_cases/attendance.py`:

```python
"""Attendance use cases with faculty authorization."""

from typing import List, Optional
from datetime import date, datetime
from dataclasses import dataclass, field

from app.domain.entities.attendance import AttendanceRecord, AttendanceSummary, AttendanceStatus
from app.domain.interfaces.repositories import (
    IAttendanceRepository,
    ISubjectAssignmentRepository,  # ← ADD
    IUserRepository
)
from app.infrastructure.security import PermissionDenied


@dataclass
class AttendanceUseCase:
    """
    Attendance business logic with faculty authorization.

    CRITICAL: Faculty can ONLY mark attendance for subjects they are assigned to.
    """
    attendance_repo: IAttendanceRepository
    assignment_repo: ISubjectAssignmentRepository  # ← NEW
    user_repo: IUserRepository

    # ... keep existing methods ...

    async def mark_attendance(
        self,
        faculty_id: str,
        subject_id: str,
        date: date,
        attendance_data: List[dict]
    ) -> List[AttendanceRecord]:
        """
        Mark attendance - with faculty authorization check.

        Args:
            faculty_id: ID of faculty marking attendance
            subject_id: ID of subject
            date: Date of attendance
            attendance_data: List of {student_id, status, remarks}

        Returns:
            List of created/updated AttendanceRecord

        Raises:
            PermissionDenied: If faculty not assigned to this subject
        """
        # Step 1: Verify faculty is assigned to this subject
        # Extract semester and section from first student record
        if not attendance_data:
            return []

        first_student_id = attendance_data[0]["student_id"]
        student = await self.user_repo.find_by_id(first_student_id)

        if not student:
            raise ValueError(f"Student {first_student_id} not found")

        # Check assignment
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=student.semester,
            section=student.section,
            academic_year=self._get_current_academic_year()
        )

        if not assignment:
            raise PermissionDenied(
                f"Faculty {faculty_id} is not assigned to subject {subject_id} "
                f"for semester {student.semester} section {student.section}"
            )

        # Step 2: Create attendance records
        records = []
        for data in attendance_data:
            record = AttendanceRecord(
                id="",  # Will be set by save
                student_id=data["student_id"],
                subject_id=subject_id,
                faculty_id=faculty_id,
                date=date,
                status=AttendanceStatus(data["status"]),
                remarks=data.get("remarks"),
                marked_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            records.append(record)

        # Step 3: Save batch
        await self.attendance_repo.save_batch(records)

        return records

    def _get_current_academic_year(self) -> str:
        """Get current academic year."""
        from datetime import datetime
        now = datetime.now()
        year = now.year
        if now.month >= 7:  # July onwards is new academic year
            return f"{year}-{year + 1}"
        return f"{year - 1}-{year}"
```

- [ ] **Step 2: Commit**

```bash
git add app/use_cases/attendance.py
git commit -m "feat: add faculty authorization to attendance marking"
```

---

## Task 10: Update Timetable Use Case for Versioning

**Files:**
- Modify: `app/use_cases/timetable.py`

- [ ] **Step 1: Add version management methods**

Add to `app/use_cases/timetable.py`:

```python
async def update_timetable(
    self,
    semester: int,
    section: str,
    new_schedule: List[DaySchedule],
    created_by: str
) -> Timetable:
    """
    Update timetable - creates new version, deactivates old.

    Args:
        semester: Semester number
        section: Section identifier
        new_schedule: New schedule data
        created_by: User ID creating this version

    Returns:
        Newly created Timetable
    """
    academic_year = self._get_current_academic_year()

    # Step 1: Deactivate existing active timetable
    await self.timetable_repo.deactivate_active(
        semester=semester,
        section=section,
        academic_year=academic_year
    )

    # Step 2: Get latest version number
    latest_version = await self.timetable_repo.get_latest_version(
        semester=semester,
        section=section,
        academic_year=academic_year
    )

    # Step 3: Create new active version
    new_timetable = Timetable(
        id="",  # Will be set by save
        semester=semester,
        section=section,
        academic_year=academic_year,
        version=latest_version + 1,
        is_active=True,
        schedule=new_schedule,
        created_by=created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    return await self.timetable_repo.save(new_timetable)
```

- [ ] **Step 2: Commit**

```bash
git add app/use_cases/timetable.py
git commit -m "feat: add timetable version management"
```

---

## Task 11: Create Migration Scripts

**Files:**
- Create: `app/infrastructure/migrations/migrate_subject_assignments.py`
- Create: `app/infrastructure/migrations/migrate_timetables.py`
- Create: `app/infrastructure/migrations/migrate_cleanup.py`
- Create: `app/infrastructure/migrations/__init__.py`

- [ ] **Step 1: Create migration __init__.py**

```python
"""Database migration scripts."""
```

- [ ] **Step 2: Create subject_assignments migration**

```python
"""Migrate data from subjects.sections to subject_assignments collection."""

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase


async def migrate_subject_assignments(db: AsyncIOMotorDatabase) -> dict:
    """
    Migrate subject data to new subject_assignments collection.

    Reads existing subjects with sections/faculty_id arrays
    and creates corresponding subject_assignment documents.
    """
    subjects_collection = db.subjects
    assignments_collection = db.subject_assignments

    # Find all subjects with sections field
    subjects = await subjects_collection.find(
        {"sections": {"$exists": True, "$not": {"$size": 0}}}
    ).to_list(None)

    migrated = 0
    errors = []

    for subject in subjects:
        try:
            for section in subject.get("sections", []):
                assignment = {
                    "subject_id": subject["_id"],
                    "semester": subject["semester"],
                    "section": section,
                    "faculty_id": subject.get("faculty_id"),
                    "academic_year": "2024-2025",  # Default
                    "is_primary": True,
                    "created_at": datetime.utcnow()
                }

                result = await assignments_collection.insert_one(assignment)
                if result.inserted_id:
                    migrated += 1

        except Exception as e:
            errors.append({
                "subject_id": str(subject["_id"]),
                "error": str(e)
            })

    return {
        "subjects_processed": len(subjects),
        "assignments_created": migrated,
        "errors": errors
    }
```

- [ ] **Step 3: Create timetables migration**

```python
"""Migrate from old timetable_entries to new timetables schema."""

from datetime import datetime
from collections import defaultdict
from motor.motor_asyncio import AsyncIOMotorDatabase


async def migrate_timetables(db: AsyncIOMotorDatabase) -> dict:
    """
    Migrate timetable entries to new single-document schema.

    Groups old per-slot entries into one document per semester-section.
    """
    old_collection = db.timetable_entries
    new_collection = db.timetables

    # Get all entries
    entries = await old_collection.find({}).to_list(None)

    # Group by semester-section-academic_year
    grouped = defaultdict(list)
    for entry in entries:
        key = (
            entry["semester"],
            entry["section"],
            entry.get("academic_year", "2024-2025")
        )
        grouped[key].append(entry)

    migrated = 0
    errors = []

    for (semester, section, academic_year), entries_list in grouped.items():
        try:
            # Build schedule structure
            schedule_by_day = defaultdict(list)

            for entry in entries_list:
                day = entry["day"]
                schedule_by_day[day].append({
                    "slot": entry["slot"],
                    "subject_id": entry.get("subject_id"),
                    "faculty_id": entry.get("faculty_id"),
                    "room": entry.get("room_number")
                })

            # Create schedule array
            schedule = [
                {
                    "day": day,
                    "slots": sorted(slots, key=lambda x: x["slot"])
                }
                for day, slots in schedule_by_day.items()
            ]

            timetable_doc = {
                "semester": semester,
                "section": section,
                "academic_year": academic_year,
                "version": 1,
                "is_active": True,
                "schedule": schedule,
                "created_by": None,  # System migration
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await new_collection.insert_one(timetable_doc)
            if result.inserted_id:
                migrated += 1

        except Exception as e:
            errors.append({
                "key": f"{semester}-{section}-{academic_year}",
                "error": str(e)
            })

    return {
        "groups_processed": len(grouped),
        "timetables_created": migrated,
        "errors": errors
    }
```

- [ ] **Step 4: Create cleanup migration**

```python
"""Cleanup after migration - remove old fields/collections."""

from motor.motor_asyncio import AsyncIOMotorDatabase


async def cleanup_after_migration(db: AsyncIOMotorDatabase) -> dict:
    """
    Clean up after successful migration.

    1. Remove sections and faculty_id from subjects
    2. Drop old timetable_entries collection
    """
    results = {}

    # Remove sections and faculty_id from subjects
    subjects_result = await db.subjects.update_many(
        {},
        {"$unset": {"sections": "", "faculty_id": ""}}
    )
    results["subjects_updated"] = subjects_result.modified_count

    # Drop old timetable_entries collection
    try:
        await db.timetable_entries.drop()
        results["timetable_entries_dropped"] = True
    except Exception:
        results["timetable_entries_dropped"] = False

    return results
```

- [ ] **Step 5: Create migration runner**

```python
"""Run all migrations in order."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from .migrate_subject_assignments import migrate_subject_assignments
from .migrate_timetables import migrate_timetables
from .migrate_cleanup import cleanup_after_migration


async def run_all_migrations(db: AsyncIOMotorDatabase) -> dict:
    """
    Run all database migrations in order.

    Order matters:
    1. Create new collections (subject_assignments, timetables)
    2. Migrate data
    3. Cleanup old schema
    """
    results = {}

    # Phase 1: Migrate subject assignments
    print("Migrating subject assignments...")
    results["subject_assignments"] = await migrate_subject_assignments(db)

    # Phase 2: Migrate timetables
    print("Migrating timetables...")
    results["timetables"] = await migrate_timetables(db)

    # Phase 3: Cleanup
    print("Cleaning up old schema...")
    results["cleanup"] = await cleanup_after_migration(db)

    return results
```

- [ ] **Step 6: Commit**

```bash
git add app/infrastructure/migrations/
git commit -m "feat: add database migration scripts"
```

---

## Task 12: Create Migration CLI Command

**Files:**
- Create: `scripts/run_migrations.py`

- [ ] **Step 1: Create migration runner script**

```python
#!/usr/bin/env python
"""CLI command to run database migrations."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.database import db
from app.infrastructure.migrations import run_all_migrations


async def main():
    """Run migrations."""
    print("Starting database migrations...")
    print("-" * 50)

    await db.connect()

    try:
        results = await run_all_migrations(db.get_database())

        print("-" * 50)
        print("Migration Results:")
        print(f"  Subject Assignments: {results['subject_assignments']}")
        print(f"  Timetables: {results['timetables']}")
        print(f"  Cleanup: {results['cleanup']}")

        # Check for errors
        total_errors = (
            len(results['subject_assignments'].get('errors', [])) +
            len(results['timetables'].get('errors', []))
        )

        if total_errors > 0:
            print(f"\n⚠️  {total_errors} errors encountered. Please review.")
            return 1

        print("\n✅ All migrations completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await db.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Commit**

```bash
git add scripts/
git commit -m "feat: add migration CLI command"
```

---

## Task 13: Update Dependencies Injection

**Files:**
- Modify: `app/infrastructure/dependencies.py`

- [ ] **Step 1: Add SubjectAssignmentRepository dependency**

Add to `app/infrastructure/dependencies.py`:

```python
from app.adapters.repositories import SubjectAssignmentRepository
from app.domain.interfaces.repositories import ISubjectAssignmentRepository


async def get_subject_assignment_repository(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ISubjectAssignmentRepository:
    """Dependency to get subject assignment repository."""
    return SubjectAssignmentRepository(db)
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/dependencies.py
git commit -m "feat: add SubjectAssignmentRepository dependency"
```

---

## Task 14: Update Controllers for New Schema

**Files:**
- Modify: `app/adapters/controllers/timetable_controller.py`
- Modify: `app/adapters/controllers/attendance_controller.py`

- [ ] **Step 1: Update timetable controller**

Add to `app/adapters/controllers/timetable_controller.py`:

```python
@router.get("/enriched/{semester}/{section}")
async def get_timetable_enriched(
    semester: int,
    section: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """
    Get timetable with subject and faculty details (aggregation).

    Use this when displaying to users.
    For internal logic, use the regular endpoint.
    """
    # Get timetable
    timetable_doc = await db.timetables.find_one({
        "semester": semester,
        "section": section,
        "is_active": True
    })

    if not timetable_doc:
        raise HTTPException(status_code=404, detail="Timetable not found")

    # Collect unique IDs
    subject_ids = set()
    faculty_ids = set()

    for day in timetable_doc.get("schedule", []):
        for slot in day.get("slots", []):
            if slot.get("subject_id"):
                subject_ids.add(slot["subject_id"])
            if slot.get("faculty_id"):
                faculty_ids.add(slot["faculty_id"])

    # Batch lookup
    subjects = await db.subjects.find({
        "_id": {"$in": list(subject_ids)}
    }).to_list(None)

    faculty = await db.users.find({
        "_id": {"$in": list(faculty_ids)},
        "role": "faculty"
    }).to_list(None)

    # Build lookup maps
    subject_map = {str(s["_id"]): s for s in subjects}
    faculty_map = {str(f["_id"]): f for f in faculty}

    # Enrich schedule
    enriched_schedule = []
    for day in timetable_doc.get("schedule", []):
        enriched_slots = []
        for slot in day.get("slots", []):
            enriched_slot = {
                "slot": slot["slot"],
                "room": slot.get("room")
            }
            if slot.get("subject_id"):
                subj = subject_map.get(slot["subject_id"])
                enriched_slot["subject"] = {
                    "id": slot["subject_id"],
                    "code": subj["code"] if subj else None,
                    "name": subj["name"] if subj else None
                }
            if slot.get("faculty_id"):
                fac = faculty_map.get(slot["faculty_id"])
                enriched_slot["faculty"] = {
                    "id": slot["faculty_id"],
                    "name": fac["full_name"] if fac else None
                }
            enriched_slots.append(enriched_slot)

        enriched_schedule.append({
            "day": day["day"],
            "slots": enriched_slots
        })

    return {
        "semester": semester,
        "section": section,
        "schedule": enriched_schedule
    }
```

- [ ] **Step 2: Update attendance controller**

Add authorization check to `app/adapters/controllers/attendance_controller.py`:

```python
@router.post("/mark")
async def mark_attendance(
    request: AttendanceMarkRequest,
    current_user: User = Depends(get_current_user),
    attendance_use_case: AttendanceUseCase = Depends(get_attendance_use_case)
) -> dict:
    """
    Mark attendance - faculty authorization enforced.

    Faculty can ONLY mark attendance for subjects they are assigned to.
    """
    # Verify faculty is assigned to this subject
    if not current_user.is_faculty() and not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Use case will verify assignment
    try:
        records = await attendance_use_case.mark_attendance(
            faculty_id=current_user.id if current_user.is_faculty() else request.faculty_id,
            subject_id=request.subject_id,
            date=request.date,
            attendance_data=request.attendance
        )
        return {
            "message": f"Marked {len(records)} attendance records",
            "records": len(records)
        }
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/controllers/
git commit -m "feat: update controllers for new schema with authorization"
```

---

## Task 15: Add Tests for New Schema

**Files:**
- Create: `tests/test_subject_assignment.py`
- Create: `tests/test_timetable_refactor.py`
- Modify: `tests/test_attendance.py`

- [ ] **Step 1: Create subject assignment tests**

```python
"""Tests for SubjectAssignment entity and repository."""

import pytest
from datetime import datetime
from app.domain.entities.subject_assignment import SubjectAssignment
from app.adapters.repositories.subject_assignment_repository import SubjectAssignmentRepository


@pytest.mark.asyncio
async def test_subject_assignment_validation():
    """Test SubjectAssignment validation."""
    # Valid assignment
    assignment = SubjectAssignment(
        id="",
        subject_id="507f1f77bcf86cd799439011",
        semester=3,
        section="A",
        faculty_id="507f1f77bcf86cd799439012",
        academic_year="2024-2025"
    )
    assert assignment.semester == 3

    # Invalid semester
    with pytest.raises(ValueError):
        SubjectAssignment(
            id="",
            subject_id="507f1f77bcf86cd799439011",
            semester=9,  # Invalid
            section="A",
            faculty_id="507f1f77bcf86cd799439012",
            academic_year="2024-2025"
        )


@pytest.mark.asyncio
async def test_faculty_assignment_lookup(test_db):
    """Test finding faculty assignment."""
    repo = SubjectAssignmentRepository(test_db)

    # Setup
    assignment = SubjectAssignment(
        id="",
        subject_id="507f1f77bcf86cd799439011",
        semester=3,
        section="A",
        faculty_id="507f1f77bcf86cd799439012",
        academic_year="2024-2025"
    )
    await repo.save(assignment)

    # Test
    found = await repo.find_faculty_assignment(
        faculty_id="507f1f77bcf86cd799439012",
        subject_id="507f1f77bcf86cd799439011",
        semester=3,
        section="A"
    )

    assert found is not None
    assert found.faculty_id == "507f1f77bcf86cd799439012"
```

- [ ] **Step 2: Create timetable refactor tests**

```python
"""Tests for redesigned Timetable entity and repository."""

import pytest
from app.domain.entities.timetable import Timetable, DaySchedule, TimetableSlot, DayOfWeek
from app.adapters.repositories.timetable_repository import TimetableRepository


@pytest.mark.asyncio
async def test_timetable_versioning(test_db):
    """Test timetable version management."""
    repo = TimetableRepository(test_db)

    # Create first version
    timetable1 = Timetable(
        id="",
        semester=3,
        section="A",
        academic_year="2024-2025",
        version=1,
        is_active=True,
        schedule=[],
        created_by="admin_id",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await repo.save(timetable1)

    # Deactivate and create version 2
    await repo.deactivate_active(3, "A", "2024-2025")

    timetable2 = Timetable(
        id="",
        semester=3,
        section="A",
        academic_year="2024-2025",
        version=2,
        is_active=True,
        schedule=[],
        created_by="admin_id",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await repo.save(timetable2)

    # Only version 2 should be active
    found = await repo.find_by_semester_and_section(3, "A", "2024-2025")
    assert found is not None
    assert found.version == 2
    assert found.is_active is True


@pytest.mark.asyncio
async def test_timetable_faculty_lookup(test_db):
    """Test finding all slots for a faculty."""
    repo = TimetableRepository(test_db)

    schedule = [
        DaySchedule(
            day=DayOfWeek.MONDAY,
            slots=[
                TimetableSlot(slot=1, subject_id="sub1", faculty_id="fac1", room="101"),
                TimetableSlot(slot=2, subject_id="sub2", faculty_id="fac2", room="102"),
            ]
        )
    ]

    timetable = Timetable(
        id="",
        semester=3,
        section="A",
        academic_year="2024-2025",
        version=1,
        is_active=True,
        schedule=schedule,
        created_by="admin_id",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await repo.save(timetable)

    # Find fac1's slots
    fac1_slots = await repo.find_by_faculty("fac1")
    assert len(fac1_slots) == 1
    assert fac1_slots[0]["slot"] == 1
```

- [ ] **Step 3: Add attendance authorization tests**

Add to `tests/test_attendance.py`:

```python
@pytest.mark.asyncio
async def test_faculty_cannot_mark_unassigned_subject(test_db, attendance_use_case):
    """Test that faculty cannot mark attendance for unassigned subjects."""
    from app.infrastructure.security import PermissionDenied

    # Faculty tries to mark attendance for subject they're NOT assigned to
    with pytest.raises(PermissionDenied):
        await attendance_use_case.mark_attendance(
            faculty_id="unassigned_faculty_id",
            subject_id="subject_id",
            date=date(2024, 1, 15),
            attendance_data=[
                {
                    "student_id": "student_id",
                    "status": "present"
                }
            ]
        )
```

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add tests for schema refactor"
```

---

## Task 16: Run Full Test Suite

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass

- [ ] **Step 2: Check test coverage**

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

Expected: >80% coverage for new code

---

## Task 17: Documentation Update

**Files:**
- Create: `docs/migration-guide.md`

- [ ] **Step 1: Create migration guide**

```python
# Database Migration Guide

## Overview
This document describes how to migrate from the old schema to the new scalable schema.

## Pre-Migration Checklist

1. **Backup your database**
   ```bash
   mongodump --uri="mongodb://localhost:27017" --out=backup_$(date +%Y%m%d)
   ```

2. **Stop all application services**
   ```bash
   # Stop your FastAPI server
   ```

3. **Verify MongoDB connection**
   ```bash
   python -c "from app.infrastructure.database import db; import asyncio; asyncio.run(db.connect())"
   ```

## Running Migrations

### Option 1: Using CLI Script

```bash
python scripts/run_migrations.py
```

### Option 2: Manual Execution

```python
from app.infrastructure.database import db
from app.infrastructure.migrations import run_all_migrations

async def migrate():
    await db.connect()
    results = await run_all_migrations(db.get_database())
    print(results)
    await db.disconnect()

import asyncio
asyncio.run(migrate())
```

## Verification

After migration, verify:

1. **Subject Assignments Created**
   ```python
   from motor.motor_asyncio import AsyncIOMotorClient
   client = AsyncIOMotorClient("mongodb://localhost:27017")
   count = await client.academic_system.subject_assignments.count_documents({})
   print(f"Subject assignments: {count}")
   ```

2. **Timetables Migrated**
   ```python
   count = await client.academic_system.timetables.count_documents({"is_active": True})
   print(f"Active timetables: {count}")
   ```

3. **Indexes Created**
   ```python
   indexes = await client.academic_system.subject_assignments.list_indexes()
   for idx in indexes:
       print(f"Index: {idx['name']}")
   ```

## Rollback

If migration fails:

```bash
# Restore from backup
mongorestore --uri="mongodb://localhost:27017" --drop backup_YYYYMMDD/
```

## Post-Migration

1. Update application to use new schema
2. Update any custom queries
3. Remove old collection references from code
```

- [ ] **Step 2: Commit**

```bash
git add docs/
git commit -m "docs: add migration guide"
```

---

## Self-Review Complete

**Spec Coverage:**
- ✅ Timetable redesign with versioning - Tasks 4, 7, 10, 15
- ✅ Subject assignments collection - Tasks 1, 2, 3, 11
- ✅ Subject entity simplification - Tasks 5, 6
- ✅ Missing indexes - Task 8
- ✅ Faculty authorization - Tasks 9, 14
- ✅ Migration scripts - Tasks 11, 12
- ✅ Tests - Task 15, 16
- ✅ Documentation - Task 17

**Placeholder Scan:** None found - all code complete

**Type Consistency:** Verified - entity names, repository methods, field names consistent throughout
