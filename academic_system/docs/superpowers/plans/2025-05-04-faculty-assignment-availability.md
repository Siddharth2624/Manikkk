# Faculty Assignment & Availability System - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready system for admins to assign subjects to faculty, faculty to set their availability preferences, and admins to override availability with full audit logging.

**Architecture:** Clean separation with domain entities, use case services, FastAPI controllers, MongoDB repositories, and React components. Availability is per-subject-assignment (not global), with persistent and one-time admin overrides.

**Tech Stack:** Python 3.11+, FastAPI, Motor (MongoDB async), React 19, Tailwind CSS, Lucide icons, Pydantic

---

## File Structure Overview

### Backend (Python)
```
app/domain/entities/
  ├── faculty_availability.py          # NEW: Domain entity
  └── admin_override_log.py            # NEW: Domain entity

app/adapters/repositories/
  ├── faculty_availability_repository.py    # NEW: MongoDB repo
  └── admin_override_repository.py          # NEW: MongoDB repo

app/use_cases/
  ├── faculty_assignment.py             # NEW: Assignment service
  ├── faculty_availability.py           # NEW: Availability service
  └── admin_override.py                 # NEW: Override service

app/adapters/controllers/
  ├── faculty_assignment_controller.py  # NEW: Admin routes
  └── faculty_controller.py             # NEW: Faculty routes

app/domain/interfaces/repositories.py
  └── Add IFacultyAvailabilityRepository and IAdminOverrideRepository

app/infrastructure/database.py
  └── Add indexes for new collections
```

### Frontend (React)
```
frontend/src/
  ├── components/
  │   ├── ErrorBoundary.jsx             # NEW: Error wrapper
  │   ├── faculty/
  │   │   └── SubjectCard.jsx           # NEW: Accordion + slot grid
  │   ├── admin/
  │   │   └── AssignmentForm.jsx        # NEW: Assignment form
  │   └── shared/
  │       └── SlotGrid.jsx              # NEW: Reusable grid
  ├── pages/
  │   ├── faculty/
  │   │   └── my-subjects.jsx           # NEW: Faculty portal
  │   └── admin/
  │       └── assignments.jsx           # NEW: Admin assignment page
  ├── services/
  │   ├── facultyAssignment.js          # NEW: API client
  │   └── facultyAvailability.js        # NEW: API client
  ├── lib/
  │   └── api.js                        # MODIFY: Enhanced error handling
  └── utils/
      └── debounce.js                   # NEW: Utility
```

---

## Task 1: Create Domain Entities

**Files:**
- Create: `app/domain/entities/faculty_availability.py`
- Create: `app/domain/entities/admin_override_log.py`

- [ ] **Step 1: Create FacultyAvailability entity**

```python
"""Faculty availability domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from enum import Enum


class DayOfWeek(str, Enum):
    """Days of the week for availability slots."""
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"


@dataclass
class AvailableSlot:
    """Single available time slot."""
    day: DayOfWeek
    slot: int  # 1-10

    def __post_init__(self):
        if not 1 <= self.slot <= 10:
            raise ValueError("Slot must be between 1 and 10")


@dataclass
class FacultyAvailability:
    """
    Faculty availability for a specific subject assignment.

    One record per (faculty_id, subject_id, semester, section, academic_year).
    """
    id: str | None
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    academic_year: str
    available_slots: List[AvailableSlot]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")
        if not self.section or len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "faculty_id": self.faculty_id,
            "subject_id": self.subject_id,
            "semester": self.semester,
            "section": self.section,
            "academic_year": self.academic_year,
            "available_slots": [
                {"day": s.day.value, "slot": s.slot} for s in self.available_slots
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
```

- [ ] **Step 2: Create AdminOverrideLog entity**

```python
"""Admin override log domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal
from enum import Enum


class OverrideType(str, Enum):
    """Type of override."""
    PERSISTENT = "persistent"
    ONE_TIME = "one_time"


class OverrideAction(str, Enum):
    """Action for a slot override."""
    ADD = "add"      # Force include
    REMOVE = "remove" # Force exclude


@dataclass
class OverrideSlot:
    """Single slot in an override."""
    day: DayOfWeek  # From faculty_availability.py
    slot: int
    action: OverrideAction

    def __post_init__(self):
        if not 1 <= self.slot <= 10:
            raise ValueError("Slot must be between 1 and 10")

    def to_dict(self) -> dict:
        return {"day": self.day.value, "slot": self.slot, "action": self.action.value}


@dataclass
class AdminOverrideLog:
    """
    Audit log for admin availability overrides.

    Stores ALL overrides (persistent and one-time).
    Does NOT modify faculty_availability directly.
    """
    id: str | None
    admin_id: str
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    academic_year: str
    override_type: OverrideType
    applied: bool  # True if used in generation (one-time only)
    slots: List[OverrideSlot]
    timestamp: datetime

    def __post_init__(self):
        if not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "faculty_id": self.faculty_id,
            "subject_id": self.subject_id,
            "semester": self.semester,
            "section": self.section,
            "academic_year": self.academic_year,
            "override_type": self.override_type.value,
            "applied": self.applied,
            "slots": [s.to_dict() for s in self.slots],
            "timestamp": self.timestamp.isoformat()
        }
```

- [ ] **Step 3: Commit**

```bash
git add app/domain/entities/faculty_availability.py app/domain/entities/admin_override_log.py
git commit -m "feat: add FacultyAvailability and AdminOverrideLog domain entities"
```

---

## Task 2: Create Repository Interfaces

**Files:**
- Modify: `app/domain/interfaces/repositories.py`

- [ ] **Step 1: Add repository interfaces**

```python
# Add to existing repositories.py file

from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.entities.admin_override_log import AdminOverrideLog, OverrideType


class IFacultyAvailabilityRepository(ABC):
    """Repository for faculty availability records."""

    @abstractmethod
    async def save(self, availability: FacultyAvailability) -> FacultyAvailability:
        """Save or update availability record."""
        pass

    @abstractmethod
    async def find(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> Optional[FacultyAvailability]:
        """Find availability by unique key."""
        Pass

    @abstractmethod
    async def find_by_faculty(
        self, faculty_id: str, academic_year: Optional[str] = None
    ) -> List[FacultyAvailability]:
        """Find all availability for a faculty member."""
        Pass

    @abstractmethod
    async def update(self, availability: FacultyAvailability) -> FacultyAvailability:
        """Update existing availability record."""
        Pass

    @abstractmethod
    async def delete(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> bool:
        """Delete availability record."""
        Pass


class IAdminOverrideRepository(ABC):
    """Repository for admin override logs."""

    @abstractmethod
    async def save(self, override: AdminOverrideLog) -> AdminOverrideLog:
        """Save override log entry."""
        Pass

    @abstractmethod
    async def find_by_id(self, override_id: str) -> Optional[AdminOverrideLog]:
        """Find override by ID."""
        Pass

    @abstractmethod
    async def find_applicable(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> List[AdminOverrideLog]:
        """Find all applicable overrides (persistent + unapplied one-time)."""
        Pass

    @abstractmethod
    async def find_audit_log(
        self, faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None
    ) -> List[AdminOverrideLog]:
        """Find overrides for audit log view."""
        Pass

    @abstractmethod
    async def mark_one_time_applied(
        self, semester: int, section: str, academic_year: str
    ) -> int:
        """Mark one-time overrides as applied after generation."""
        Pass

    @abstractmethod
    async def delete(self, override_id: str) -> bool:
        """Delete override by ID."""
        Pass
```

- [ ] **Step 2: Commit**

```bash
git add app/domain/interfaces/repositories.py
git commit -m "feat: add IFacultyAvailabilityRepository and IAdminOverrideRepository interfaces"
```

---

## Task 3: Create MongoDB Repository Implementations

**Files:**
- Create: `app/adapters/repositories/faculty_availability_repository.py`
- Create: `app/adapters/repositories/admin_override_repository.py`

- [ ] **Step 1: Create FacultyAvailabilityRepository**

```python
"""MongoDB implementation of faculty availability repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClientSession

from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.interfaces.repositories import IFacultyAvailabilityRepository


class FacultyAvailabilityRepository(IFacultyAvailabilityRepository):
    """MongoDB implementation of faculty availability repository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.faculty_availability

    def _to_entity(self, document: dict) -> FacultyAvailability:
        """Convert MongoDB document to FacultyAvailability entity."""
        slots = [
            AvailableSlot(
                day=DayOfWeek(s["day"]),
                slot=s["slot"]
            )
            for s in document.get("available_slots", [])
        ]

        return FacultyAvailability(
            id=str(document["_id"]),
            faculty_id=str(document["faculty_id"]),
            subject_id=str(document["subject_id"]),
            semester=document["semester"],
            section=document["section"],
            academic_year=document["academic_year"],
            available_slots=slots,
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    def _to_document(self, availability: FacultyAvailability) -> dict:
        """Convert FacultyAvailability entity to MongoDB document."""
        return {
            "faculty_id": ObjectId(availability.faculty_id),
            "subject_id": ObjectId(availability.subject_id),
            "semester": availability.semester,
            "section": availability.section,
            "academic_year": availability.academic_year,
            "available_slots": [
                {"day": s.day.value, "slot": s.slot} for s in availability.available_slots
            ],
            "created_at": availability.created_at,
            "updated_at": availability.updated_at
        }

    async def save(
        self, availability: FacultyAvailability,
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> FacultyAvailability:
        """Save or update availability record."""
        doc = self._to_document(availability)

        if availability.id:
            # Update existing
            await self.collection.update_one(
                {"_id": ObjectId(availability.id)},
                {"$set": doc},
                session=session
            )
        else:
            # Insert new
            result = await self.collection.insert_one(doc, session=session)
            availability.id = str(result.inserted_id)

        return availability

    async def find(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> Optional[FacultyAvailability]:
        """Find availability by unique key."""
        document = await self.collection.find_one({
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section,
            "academic_year": academic_year
        })

        return self._to_entity(document) if document else None

    async def find_by_faculty(
        self, faculty_id: str, academic_year: Optional[str] = None
    ) -> List[FacultyAvailability]:
        """Find all availability for a faculty member."""
        query = {"faculty_id": ObjectId(faculty_id)}
        if academic_year:
            query["academic_year"] = academic_year

        cursor = self.collection.find(query).sort("semester", 1)
        documents = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in documents]

    async def update(self, availability: FacultyAvailability) -> FacultyAvailability:
        """Update existing availability record."""
        availability.updated_at = datetime.utcnow()
        doc = self._to_document(availability)

        await self.collection.update_one(
            {"_id": ObjectId(availability.id)},
            {"$set": doc}
        )

        return availability

    async def delete(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> bool:
        """Delete availability record."""
        result = await self.collection.delete_one({
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section,
            "academic_year": academic_year
        })

        return result.deleted_count > 0
```

- [ ] **Step 2: Create AdminOverrideRepository**

```python
"""MongoDB implementation of admin override repository."""

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.admin_override_log import (
    AdminOverrideLog, OverrideSlot, OverrideType,
    DayOfWeek, OverrideAction
)
from app.domain.interfaces.repositories import IAdminOverrideRepository


class AdminOverrideRepository(IAdminOverrideRepository):
    """MongoDB implementation of admin override repository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.admin_override_log

    def _to_entity(self, document: dict) -> AdminOverrideLog:
        """Convert MongoDB document to AdminOverrideLog entity."""
        slots = [
            OverrideSlot(
                day=DayOfWeek(s["day"]),
                slot=s["slot"],
                action=OverrideAction(s["action"])
            )
            for s in document.get("slots", [])
        ]

        return AdminOverrideLog(
            id=str(document["_id"]),
            admin_id=str(document["admin_id"]),
            faculty_id=str(document["faculty_id"]),
            subject_id=str(document["subject_id"]),
            semester=document["semester"],
            section=document["section"],
            academic_year=document["academic_year"],
            override_type=OverrideType(document["override_type"]),
            applied=document.get("applied", False),
            slots=slots,
            timestamp=document["timestamp"]
        )

    def _to_document(self, override: AdminOverrideLog) -> dict:
        """Convert AdminOverrideLog entity to MongoDB document."""
        return {
            "admin_id": ObjectId(override.admin_id),
            "faculty_id": ObjectId(override.faculty_id),
            "subject_id": ObjectId(override.subject_id),
            "semester": override.semester,
            "section": override.section,
            "academic_year": override.academic_year,
            "override_type": override.override_type.value,
            "applied": override.applied,
            "slots": [
                {"day": s.day.value, "slot": s.slot, "action": s.action.value}
                for s in override.slots
            ],
            "timestamp": override.timestamp
        }

    async def save(self, override: AdminOverrideLog) -> AdminOverrideLog:
        """Save override log entry."""
        doc = self._to_document(override)

        if override.id:
            await self.collection.update_one(
                {"_id": ObjectId(override.id)},
                {"$set": doc}
            )
        else:
            result = await self.collection.insert_one(doc)
            override.id = str(result.inserted_id)

        return override

    async def find_by_id(self, override_id: str) -> Optional[AdminOverrideLog]:
        """Find override by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(override_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_applicable(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> List[AdminOverrideLog]:
        """Find all applicable overrides (persistent + unapplied one-time)."""
        cursor = self.collection.find({
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section,
            "academic_year": academic_year,
            "$or": [
                {"override_type": "persistent"},
                {"override_type": "one_time", "applied": False}
            ]
        }).sort("timestamp", 1)

        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_audit_log(
        self, faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None
    ) -> List[AdminOverrideLog]:
        """Find overrides for audit log view."""
        query = {}
        if faculty_id:
            query["faculty_id"] = ObjectId(faculty_id)
        if subject_id:
            query["subject_id"] = ObjectId(subject_id)
        if from_date:
            query["timestamp"] = {"$gte": from_date}

        cursor = self.collection.find(query).sort("timestamp", -1)
        documents = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in documents]

    async def mark_one_time_applied(
        self, semester: int, section: str, academic_year: str
    ) -> int:
        """Mark one-time overrides as applied after generation."""
        result = await self.collection.update_many(
            {
                "semester": semester,
                "section": section,
                "academic_year": academic_year,
                "override_type": "one_time",
                "applied": False
            },
            {"$set": {"applied": True}}
        )

        return result.modified_count

    async def delete(self, override_id: str) -> bool:
        """Delete override by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(override_id)})
            return result.deleted_count > 0
        except Exception:
            return False
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/repositories/faculty_availability_repository.py app/adapters/repositories/admin_override_repository.py
git commit -m "feat: add MongoDB repository implementations for availability and overrides"
```

---

## Task 4: Create Database Indexes

**Files:**
- Modify: `app/infrastructure/database.py`

- [ ] **Step 1: Add index creation for new collections**

```python
# Add to existing database.py file, in the startup event or create_indexes function

async def create_faculty_availability_indexes(db):
    """Create indexes for faculty_availability collection."""
    collection = db.faculty_availability

    # Unique constraint
    await collection.create_index(
        [("faculty_id", 1), ("subject_id", 1), ("semester", 1),
         ("section", 1), ("academic_year", 1)],
        unique=True
    )

    # Query indexes
    await collection.create_index([
        ("faculty_id", 1), ("semester", 1), ("section", 1), ("academic_year", 1)
    ])
    await collection.create_index([
        ("subject_id", 1), ("semester", 1), ("section", 1), ("academic_year", 1)
    ])


async def create_admin_override_log_indexes(db):
    """Create indexes for admin_override_log collection."""
    collection = db.admin_override_log

    # Query index
    await collection.create_index([
        ("faculty_id", 1), ("subject_id", 1), ("semester", 1),
        ("section", 1), ("academic_year", 1)
    ])

    # Audit query index
    await collection.create_index([("faculty_id", 1), ("subject_id", 1)])

    # Timestamp index for sorting
    await collection.create_index([("timestamp", -1)])


# Add to startup event (if using FastAPI startup)
@app.on_event("startup")
async def startup_db_client():
    # Existing code...
    await create_faculty_availability_indexes(db)
    await create_admin_override_log_indexes(db)
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/database.py
git commit -m "feat: add indexes for faculty_availability and admin_override_log collections"
```

---

## Task 5: Create Faculty Assignment Use Case

**Files:**
- Create: `app/use_cases/faculty_assignment.py`

- [ ] **Step 1: Create FacultyAssignmentService**

```python
"""Faculty assignment use case service."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.entities.faculty_availability import FacultyAvailability
from app.domain.interfaces.repositories import (
    ISubjectAssignmentRepository, IFacultyAvailabilityRepository,
    ISubjectRepository
)


@dataclass
class AssignSubjectRequest:
    """Request to assign subject to faculty."""
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    academic_year: str


@dataclass
class AssignmentResponse:
    """Response from subject assignment."""
    assignment: SubjectAssignment
    availability: FacultyAvailability


class FacultyAssignmentService:
    """Service for managing faculty subject assignments."""

    def __init__(
        self,
        assignment_repo: ISubjectAssignmentRepository,
        availability_repo: IFacultyAvailabilityRepository,
        subject_repo: ISubjectRepository,
        db  # Motor database for transactions
    ):
        self.assignment_repo = assignment_repo
        self.availability_repo = availability_repo
        self.subject_repo = subject_repo
        self.db = db

    async def assign_subject(self, request: AssignSubjectRequest) -> AssignmentResponse:
        """
        Assign subject to faculty with transaction safety.

        Creates both SubjectAssignment and blank FacultyAvailability atomically.
        Validates unique constraint (one subject per faculty/semester/section).
        """
        # 1. Validate unique constraint
        existing = await self.assignment_repo.find_faculty_assignment(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year
        )

        # Check for ANY assignment in this semester/section
        faculty_assignments = await self.assignment_repo.find_by_faculty(
            faculty_id=request.faculty_id,
            academic_year=request.academic_year
        )

        conflict = next(
            (a for a in faculty_assignments
             if a.semester == request.semester and a.section == request.section),
            None
        )

        if conflict:
            raise ValueError(
                f"Faculty already assigned to subject {conflict.subject_id} "
                f"in semester {request.semester}, section {request.section}"
            )

        # 2. Validate subject exists
        subject = await self.subject_repo.find_by_id(request.subject_id)
        if not subject:
            raise ValueError("Subject not found")

        # 3. Use transaction for atomic creation
        async with await self.db.start_session() as session:
            async with session.start_transaction():
                # Create assignment
                assignment = SubjectAssignment(
                    id=None,
                    subject_id=request.subject_id,
                    faculty_id=request.faculty_id,
                    semester=request.semester,
                    section=request.section,
                    academic_year=request.academic_year,
                    is_primary=True
                )
                saved_assignment = await self.assignment_repo.save(assignment)

                # Create blank availability
                availability = FacultyAvailability(
                    id=None,
                    faculty_id=request.faculty_id,
                    subject_id=request.subject_id,
                    semester=request.semester,
                    section=request.section,
                    academic_year=request.academic_year,
                    available_slots=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                await self.availability_repo.save(availability, session=session)

        return AssignmentResponse(
            assignment=saved_assignment,
            availability=availability
        )

    async def get_faculty_assignments(
        self, faculty_id: str, academic_year: str
    ) -> List[dict]:
        """Get all assignments for a faculty with subject details."""
        assignments = await self.assignment_repo.find_by_faculty(
            faculty_id=faculty_id,
            academic_year=academic_year
        )

        result = []
        for assignment in assignments:
            subject = await self.subject_repo.find_by_id(assignment.subject_id)
            result.append({
                "id": assignment.id,
                "subject_id": assignment.subject_id,
                "subject_name": subject.name if subject else "Unknown",
                "subject_code": subject.code if subject else "",
                "subject_credits": subject.credits if subject else 0,
                "semester": assignment.semester,
                "section": assignment.section,
                "academic_year": assignment.academic_year
            })

        return result

    async def get_all_assignments(
        self, semester: Optional[int] = None,
        section: Optional[str] = None,
        academic_year: Optional[str] = None
    ) -> List[dict]:
        """Get all assignments with optional filters."""
        # Build query based on filters
        assignments = await self.assignment_repo.find_all()

        result = []
        for assignment in assignments:
            if semester and assignment.semester != semester:
                continue
            if section and assignment.section != section:
                continue
            if academic_year and assignment.academic_year != academic_year:
                continue

            subject = await self.subject_repo.find_by_id(assignment.subject_id)
            result.append({
                "id": assignment.id,
                "faculty_id": assignment.faculty_id,
                "subject_id": assignment.subject_id,
                "subject_name": subject.name if subject else "Unknown",
                "semester": assignment.semester,
                "section": assignment.section,
                "academic_year": assignment.academic_year
            })

        return result

    async def remove_assignment(self, assignment_id: str) -> bool:
        """Remove assignment and cascade to availability."""
        # First, get the assignment to find keys
        assignment = await self.assignment_repo.find_by_id(assignment_id)
        if not assignment:
            return False

        # Delete availability
        await self.availability_repo.delete(
            faculty_id=assignment.faculty_id,
            subject_id=assignment.subject_id,
            semester=assignment.semester,
            section=assignment.section,
            academic_year=assignment.academic_year
        )

        # Delete assignment
        return await self.assignment_repo.delete(assignment_id)
```

- [ ] **Step 2: Commit**

```bash
git add app/use_cases/faculty_assignment.py
git commit -m "feat: add FacultyAssignmentService with transaction-safe assignment"
```

---

## Task 6: Create Faculty Availability Use Case

**Files:**
- Create: `app/use_cases/faculty_availability.py`

- [ ] **Step 1: Create FacultyAvailabilityService**

```python
"""Faculty availability use case service."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime

from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.entities.admin_override_log import AdminOverrideLog
from app.domain.interfaces.repositories import (
    IFacultyAvailabilityRepository, IAdminOverrideRepository,
    ISubjectAssignmentRepository
)


@dataclass
class EffectiveAvailability:
    """Computed availability (base + overrides)."""
    base_slots: List[dict]
    overrides: List[dict]
    effective_slots: List[dict]


@dataclass
class UpdateAvailabilityRequest:
    """Request to update faculty availability."""
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    academic_year: str
    available_slots: List[dict]  # [{day, slot}]
    requesting_faculty_id: str  # From JWT for ownership check


class FacultyAvailabilityService:
    """Service for managing faculty availability."""

    def __init__(
        self,
        availability_repo: IFacultyAvailabilityRepository,
        override_repo: IAdminOverrideRepository,
        assignment_repo: ISubjectAssignmentRepository,
        subject_repo  # For validation
    ):
        self.availability_repo = availability_repo
        self.override_repo = override_repo
        self.assignment_repo = assignment_repo
        self.subject_repo = subject_repo

    async def update_availability(self, request: UpdateAvailabilityRequest) -> FacultyAvailability:
        """
        Update faculty's availability.

        UPDATES existing record if present (not create new).
        Validates ownership and minimum required slots.
        """
        # 1. Ownership check
        if request.faculty_id != request.requesting_faculty_id:
            raise PermissionError("Can only modify own availability")

        # 2. Verify assignment exists
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year
        )
        if not assignment:
            raise ValueError("No assignment found for this subject")

        # 3. Validate minimum slots (subject credits)
        subject = await self.subject_repo.find_by_id(request.subject_id)
        if subject and len(request.available_slots) < subject.credits:
            raise ValueError(
                f"Minimum {subject.credits} slots required for {subject.name} "
                f"(current: {len(request.available_slots)})"
            )

        # 4. Convert slots to entities
        slot_entities = [
            AvailableSlot(day=DayOfWeek(s["day"]), slot=s["slot"])
            for s in request.available_slots
        ]

        # 5. Find existing or create new
        existing = await self.availability_repo.find(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year
        )

        now = datetime.utcnow()
        if existing:
            # Update existing
            existing.available_slots = slot_entities
            existing.updated_at = now
            return await self.availability_repo.update(existing)
        else:
            # Create new (shouldn't happen if assignment created properly)
            availability = FacultyAvailability(
                id=None,
                faculty_id=request.faculty_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section,
                academic_year=request.academic_year,
                available_slots=slot_entities,
                created_at=now,
                updated_at=now
            )
            return await self.availability_repo.save(availability)

    async def get_effective_availability(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> EffectiveAvailability:
        """
        Compute effective availability (base + overrides).

        Returns sorted, unique slots.
        """
        # Get base availability
        base = await self.availability_repo.find(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section,
            academic_year=academic_year
        )
        base_slots = base.available_slots if base else []

        # Get applicable overrides, SORTED by timestamp
        overrides = await self.override_repo.find_applicable(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section,
            academic_year=academic_year
        )
        overrides.sort(key=lambda o: o.timestamp)  # Order matters

        # Compute effective slots
        effective = self._apply_overrides(base_slots, overrides)
        effective = self._dedupe_and_sort(effective)

        return EffectiveAvailability(
            base_slots=[{"day": s.day.value, "slot": s.slot} for s in base_slots],
            overrides=[self._override_to_dict(o) for o in overrides],
            effective_slots=[{"day": s.day.value, "slot": s.slot} for s in effective]
        )

    def _apply_overrides(
        self, base: List[AvailableSlot], overrides: List[AdminOverrideLog]
    ) -> List[AvailableSlot]:
        """
        Apply timestamp-sorted overrides to base slots.

        - action="add": Force include slot
        - action="remove": Force exclude slot
        - Later overrides override earlier ones
        """
        # Start with base slots
        slot_map = {(s.day.value, s.slot): "base" for s in base}

        # Apply overrides in order
        for override in overrides:
            for slot in override.slots:
                key = (slot.day.value, slot.slot)
                if slot.action.value == "remove":
                    slot_map[key] = "removed"
                elif slot.action.value == "add":
                    slot_map[key] = "added"

        # Filter to only included slots
        effective = [
            AvailableSlot(day=DayOfWeek(k[0]), slot=k[1])
            for k, v in slot_map.items()
            if v != "removed"
        ]

        return effective

    def _dedupe_and_sort(self, slots: List[AvailableSlot]) -> List[AvailableSlot]:
        """Remove duplicates and sort by day then slot."""
        unique = {(s.day.value, s.slot): s for s in slots}
        return [
            unique[key]
            for key in sorted(unique.keys(), key=lambda x: (x[0], x[1]))
        ]

    def _override_to_dict(self, override: AdminOverrideLog) -> dict:
        """Convert override to dict for response."""
        return {
            "admin_id": override.admin_id,
            "type": override.override_type.value,
            "slots": [
                {"day": s.day.value, "slot": s.slot, "action": s.action.value}
                for s in override.slots
            ],
            "timestamp": override.timestamp.isoformat()
        }
```

- [ ] **Step 2: Commit**

```bash
git add app/use_cases/faculty_availability.py
git commit -m "feat: add FacultyAvailabilityService with effective availability computation"
```

---

## Task 7: Create Admin Override Use Case

**Files:**
- Create: `app/use_cases/admin_override.py`

- [ ] **Step 1: Create AdminOverrideService**

```python
"""Admin override use case service."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from app.domain.entities.admin_override_log import (
    AdminOverrideLog, OverrideSlot, OverrideType,
    DayOfWeek, OverrideAction
)
from app.domain.interfaces.repositories import (
    IAdminOverrideRepository, ISubjectAssignmentRepository
)


@dataclass
class CreateOverrideRequest:
    """Request to create admin override."""
    faculty_id: str
    subject_id: str
    semester: int
    section: str
    academic_year: str
    override_type: OverrideType
    slots: List[dict]  # [{day, slot, action}]
    admin_id: str  # From JWT


@dataclass
class OverrideResponse:
    """Response from override creation."""
    override: AdminOverrideLog
    message: str


class AdminOverrideService:
    """Service for managing admin overrides."""

    def __init__(
        self,
        override_repo: IAdminOverrideRepository,
        assignment_repo: ISubjectAssignmentRepository
    ):
        self.override_repo = override_repo
        self.assignment_repo = assignment_repo

    async def create_override(self, request: CreateOverrideRequest) -> OverrideResponse:
        """
        Create admin override.

        Stores in admin_override_log only (does NOT modify faculty_availability).
        Validates assignment exists and slot format.
        """
        # 1. Validate assignment exists
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year
        )
        if not assignment:
            raise ValueError("No assignment found for override")

        # 2. Validate slot format
        slot_entities = []
        valid_days = {"MON", "TUE", "WED", "THU", "FRI", "SAT"}
        valid_actions = {"add", "remove"}

        for slot_data in request.slots:
            day = slot_data.get("day", "").upper()
            slot_num = slot_data.get("slot")
            action = slot_data.get("action", "")

            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}")
            if not isinstance(slot_num, int) or not 1 <= slot_num <= 10:
                raise ValueError(f"Invalid slot: {slot_num}")
            if action not in valid_actions:
                raise ValueError(f"Invalid action: {action}")

            slot_entities.append(OverrideSlot(
                day=DayOfWeek(day),
                slot=slot_num,
                action=OverrideAction(action)
            ))

        # 3. Create override
        override = AdminOverrideLog(
            id=None,
            admin_id=request.admin_id,
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year,
            override_type=request.override_type,
            applied=False,
            slots=slot_entities,
            timestamp=datetime.utcnow()
        )

        saved = await self.override_repo.save(override)

        return OverrideResponse(
            override=saved,
            message=f"Override created successfully"
        )

    async def get_audit_log(
        self,
        faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None
    ) -> List[dict]:
        """Get audit trail of overrides."""
        overrides = await self.override_repo.find_audit_log(
            faculty_id=faculty_id,
            subject_id=subject_id,
            from_date=from_date
        )

        return [o.to_dict() for o in overrides]

    async def delete_override(
        self, override_id: str, requesting_admin_id: str
    ) -> bool:
        """
        Remove override if not yet applied (one-time).

        Anyone with admin role can delete, but applied one-time overrides are locked.
        """
        override = await self.override_repo.find_by_id(override_id)
        if not override:
            raise ValueError("Override not found")

        if override.override_type == OverrideType.ONE_TIME and override.applied:
            raise ValueError("Cannot delete applied one-time override")

        return await self.override_repo.delete(override_id)

    async def mark_generation_overrides_applied(
        self, semester: int, section: str, academic_year: str
    ) -> int:
        """
        Mark one-time overrides as applied after timetable generation.

        Called by timetable service after successful generation.
        """
        return await self.override_repo.mark_one_time_applied(
            semester=semester,
            section=section,
            academic_year=academic_year
        )
```

- [ ] **Step 2: Commit**

```bash
git add app/use_cases/admin_override.py
git commit -m "feat: add AdminOverrideService with audit logging"
```

---

## Task 8: Create Pydantic DTOs

**Files:**
- Create: `app/adapters/controllers/dto/faculty_assignment.py`

- [ ] **Step 1: Create DTOs for API endpoints**

```python
"""DTOs for faculty assignment and availability APIs."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


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


# === Request DTOs ===

class SlotDTO(BaseModel):
    """Single slot in availability or override."""
    day: DayOfWeekEnum
    slot: int = Field(ge=1, le=10)


class OverrideSlotDTO(BaseModel):
    """Slot in an override with action."""
    day: DayOfWeekEnum
    slot: int = Field(ge=1, le=10)
    action: OverrideActionEnum


class AssignSubjectRequest(BaseModel):
    """Request to assign subject to faculty."""
    faculty_id: str
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)
    academic_year: str = "2024-2025"


class UpdateAvailabilityRequest(BaseModel):
    """Request to update faculty availability."""
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)
    academic_year: str = "2024-2025"
    available_slots: List[SlotDTO]


class CreateOverrideRequest(BaseModel):
    """Request to create admin override."""
    faculty_id: str
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)
    academic_year: str = "2024-2025"
    override_type: OverrideTypeEnum
    slots: List[OverrideSlotDTO]


# === Response DTOs ===

class AssignmentResponse(BaseModel):
    """Response from assignment creation."""
    id: str
    faculty_id: str
    subject_id: str
    subject_name: str
    semester: int
    section: str
    academic_year: str


class FacultyAssignmentResponse(BaseModel):
    """Response for faculty's assigned subjects."""
    assignments: List[dict]


class AvailabilityResponse(BaseModel):
    """Response for availability data."""
    available_slots: List[SlotDTO]


class EffectiveAvailabilityResponse(BaseModel):
    """Response for computed effective availability."""
    base_slots: List[SlotDTO]
    overrides: List[dict]
    effective_slots: List[SlotDTO]


class OverrideLogResponse(BaseModel):
    """Response for override audit log."""
    overrides: List[dict]


class OverrideResponse(BaseModel):
    """Response from override creation."""
    id: str
    admin_id: str
    faculty_id: str
    subject_id: str
    override_type: str
    slots: List[OverrideSlotDTO]
    timestamp: str
```

- [ ] **Step 2: Commit**

```bash
git add app/adapters/controllers/dto/faculty_assignment.py
git commit -m "feat: add Pydantic DTOs for faculty assignment APIs"
```

---

## Task 9: Create Admin Controller

**Files:**
- Create: `app/adapters/controllers/faculty_assignment_controller.py`

- [ ] **Step 1: Create admin assignment and override routes**

```python
"""Admin controller for faculty assignments and overrides."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User
from app.infrastructure.dependencies import get_current_admin, get_current_user, get_database
from app.use_cases.faculty_assignment import (
    FacultyAssignmentService, AssignSubjectRequest
)
from app.use_cases.admin_override import (
    AdminOverrideService, CreateOverrideRequest as OverrideRequest
)
from app.adapters.controllers.dto.faculty_assignment import (
    AssignSubjectRequest as AssignSubjectDTO,
    UpdateAvailabilityRequest,
    CreateOverrideRequest as CreateOverrideDTO,
    AssignmentResponse,
    FacultyAssignmentResponse,
    EffectiveAvailabilityResponse,
    OverrideLogResponse,
    OverrideResponse
)
from app.adapters.repositories import (
    SubjectAssignmentRepository, FacultyAvailabilityRepository,
    AdminOverrideRepository, SubjectRepository
)
from app.use_cases.faculty_availability import FacultyAvailabilityService

router = APIRouter(prefix="/admin", tags=["Admin: Faculty Assignments"])


# === Dependency Injection ===

async def get_assignment_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FacultyAssignmentService:
    """Get faculty assignment service."""
    assignment_repo = SubjectAssignmentRepository(db)
    availability_repo = FacultyAvailabilityRepository(db)
    subject_repo = SubjectRepository(db)
    return FacultyAssignmentService(
        assignment_repo=assignment_repo,
        availability_repo=availability_repo,
        subject_repo=subject_repo,
        db=db
    )


async def get_override_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> AdminOverrideService:
    """Get admin override service."""
    override_repo = AdminOverrideRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    return AdminOverrideService(
        override_repo=override_repo,
        assignment_repo=assignment_repo
    )


async def get_availability_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FacultyAvailabilityService:
    """Get faculty availability service."""
    availability_repo = FacultyAvailabilityRepository(db)
    override_repo = AdminOverrideRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    subject_repo = SubjectRepository(db)
    return FacultyAvailabilityService(
        availability_repo=availability_repo,
        override_repo=override_repo,
        assignment_repo=assignment_repo,
        subject_repo=subject_repo
    )


# === Assignment Endpoints ===

@router.post("/subject-assignments", response_model=AssignmentResponse, status_code=201)
async def assign_subject_to_faculty(
    request: AssignSubjectDTO,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_assignment_service)
):
    """Assign subject to faculty (creates blank availability record)."""
    try:
        use_case_request = AssignSubjectRequest(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year
        )

        result = await service.assign_subject(use_case_request)

        # Get subject name for response
        from app.adapters.repositories import SubjectRepository
        subject_repo = SubjectRepository(service.db)
        subject = await subject_repo.find_by_id(request.subject_id)

        return AssignmentResponse(
            id=result.assignment.id,
            faculty_id=result.assignment.faculty_id,
            subject_id=result.assignment.subject_id,
            subject_name=subject.name if subject else "Unknown",
            semester=result.assignment.semester,
            section=result.assignment.section,
            academic_year=result.assignment.academic_year
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/subject-assignments", response_model=FacultyAssignmentResponse)
async def list_assignments(
    semester: Optional[int] = Query(None, ge=1, le=8),
    section: Optional[str] = Query(None, min_length=1, max_length=2),
    academic_year: Optional[str] = Query("2024-2025"),
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_assignment_service)
):
    """List all assignments with optional filters."""
    assignments = await service.get_all_assignments(
        semester=semester,
        section=section,
        academic_year=academic_year
    )

    return FacultyAssignmentResponse(assignments=assignments)


@router.delete("/subject-assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_admin: User = Depends(get_current_admin),
    service: FacultyAssignmentService = Depends(get_assignment_service)
):
    """Remove assignment (cascades to availability)."""
    success = await service.remove_assignment(assignment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    return {"message": "Assignment deleted successfully"}


# === Override Endpoints ===

@router.post("/overrides", response_model=OverrideResponse, status_code=201)
async def create_override(
    request: CreateOverrideDTO,
    current_admin: User = Depends(get_current_admin),
    service: AdminOverrideService = Depends(get_override_service)
):
    """Create admin override (persistent or one-time)."""
    try:
        use_case_request = OverrideRequest(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year,
            override_type=request.override_type,
            slots=[s.model_dump() for s in request.slots],
            admin_id=current_admin.id
        )

        result = await service.create_override(use_case_request)

        return OverrideResponse(
            id=result.override.id,
            admin_id=result.override.admin_id,
            faculty_id=result.override.faculty_id,
            subject_id=result.override.subject_id,
            override_type=result.override.override_type.value,
            slots=[
                {
                    "day": s.day.value,
                    "slot": s.slot,
                    "action": s.action.value
                }
                for s in result.override.slots
            ],
            timestamp=result.override.timestamp.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/faculty-availability/effective", response_model=EffectiveAvailabilityResponse)
async def get_effective_availability(
    faculty_id: str = Query(...),
    subject_id: str = Query(...),
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    academic_year: str = Query("2024-2025"),
    current_admin: User = Depends(get_current_admin),
    service: FacultyAvailabilityService = Depends(get_availability_service)
):
    """Get computed effective availability (base + overrides)."""
    effective = await service.get_effective_availability(
        faculty_id=faculty_id,
        subject_id=subject_id,
        semester=semester,
        section=section,
        academic_year=academic_year
    )

    return EffectiveAvailabilityResponse(
        base_slots=effective.base_slots,
        overrides=effective.overrides,
        effective_slots=effective.effective_slots
    )


@router.get("/override-log", response_model=OverrideLogResponse)
async def get_override_log(
    faculty_id: Optional[str] = Query(None),
    subject_id: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
    service: AdminOverrideService = Depends(get_override_service)
):
    """View audit trail of overrides."""
    overrides = await service.get_audit_log(
        faculty_id=faculty_id,
        subject_id=subject_id
    )

    return OverrideLogResponse(overrides=overrides)


@router.delete("/override-log/{override_id}")
async def delete_override(
    override_id: str,
    current_admin: User = Depends(get_current_admin),
    service: AdminOverrideService = Depends(get_override_service)
):
    """Remove override (only if not yet applied for one-time)."""
    try:
        success = await service.delete_override(
            override_id=override_id,
            requesting_admin_id=current_admin.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Override not found"
            )

        return {"message": "Override deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

- [ ] **Step 2: Commit**

```bash
git add app/adapters/controllers/faculty_assignment_controller.py
git commit -m "feat: add admin controller for assignments and overrides"
```

---

## Task 10: Create Faculty Controller

**Files:**
- Create: `app/adapters/controllers/faculty_controller.py`

- [ ] **Step 1: Create faculty routes**

```python
"""Faculty controller for subject assignments and availability."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User
from app.infrastructure.dependencies import get_current_user, get_database
from app.use_cases.faculty_assignment import FacultyAssignmentService
from app.use_cases.faculty_availability import (
    FacultyAvailabilityService, UpdateAvailabilityRequest
)
from app.adapters.controllers.dto.faculty_assignment import (
    UpdateAvailabilityRequest as UpdateAvailabilityDTO,
    AvailabilityResponse,
    FacultyAssignmentResponse
)
from app.adapters.repositories import (
    SubjectAssignmentRepository, FacultyAvailabilityRepository,
    AdminOverrideRepository, SubjectRepository
)

router = APIRouter(prefix="/faculty", tags=["Faculty"])


# === Dependency Injection ===

async def get_assignment_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FacultyAssignmentService:
    """Get faculty assignment service."""
    assignment_repo = SubjectAssignmentRepository(db)
    availability_repo = FacultyAvailabilityRepository(db)
    subject_repo = SubjectRepository(db)
    return FacultyAssignmentService(
        assignment_repo=assignment_repo,
        availability_repo=availability_repo,
        subject_repo=subject_repo,
        db=db
    )


async def get_availability_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FacultyAvailabilityService:
    """Get faculty availability service."""
    availability_repo = FacultyAvailabilityRepository(db)
    override_repo = AdminOverrideRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    subject_repo = SubjectRepository(db)
    return FacultyAvailabilityService(
        availability_repo=availability_repo,
        override_repo=override_repo,
        assignment_repo=assignment_repo,
        subject_repo=subject_repo
    )


# === Subject Endpoints ===

@router.get("/subjects", response_model=FacultyAssignmentResponse)
async def get_my_subjects(
    academic_year: str = Query("2024-2025"),
    current_faculty: User = Depends(get_current_user),
    service: FacultyAssignmentService = Depends(get_assignment_service)
):
    """List subjects assigned to current faculty."""
    if not current_faculty.is_faculty():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can access this endpoint"
        )

    assignments = await service.get_faculty_assignments(
        faculty_id=current_faculty.id,
        academic_year=academic_year
    )

    return FacultyAssignmentResponse(assignments=assignments)


# === Availability Endpoints ===

@router.get("/availability/{subject_id}", response_model=AvailabilityResponse)
async def get_availability(
    subject_id: str,
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    academic_year: str = Query("2024-2025"),
    current_faculty: User = Depends(get_current_user),
    service: FacultyAvailabilityService = Depends(get_availability_service)
):
    """Get availability for a specific subject."""
    if not current_faculty.is_faculty():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can access this endpoint"
        )

    from app.domain.entities.faculty_availability import FacultyAvailability

    availability = await service.availability_repo.find(
        faculty_id=current_faculty.id,
        subject_id=subject_id,
        semester=semester,
        section=section,
        academic_year=academic_year
    )

    if not availability:
        return AvailabilityResponse(available_slots=[])

    return AvailabilityResponse(
        available_slots=[
            {"day": s.day.value, "slot": s.slot}
            for s in availability.available_slots
        ]
    )


@router.post("/availability", response_model=AvailabilityResponse)
async def update_availability(
    request: UpdateAvailabilityDTO,
    current_faculty: User = Depends(get_current_user),
    service: FacultyAvailabilityService = Depends(get_availability_service)
):
    """Update available slots for an assigned subject."""
    if not current_faculty.is_faculty():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can access this endpoint"
        )

    try:
        use_case_request = UpdateAvailabilityRequest(
            faculty_id=current_faculty.id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section,
            academic_year=request.academic_year,
            available_slots=[s.model_dump() for s in request.available_slots],
            requesting_faculty_id=current_faculty.id
        )

        availability = await service.update_availability(use_case_request)

        return AvailabilityResponse(
            available_slots=[
                {"day": s.day.value, "slot": s.slot}
                for s in availability.available_slots
            ]
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

- [ ] **Step 2: Register routers in main.py**

```python
# Add to main.py

from app.adapters.controllers.faculty_assignment_controller import router as admin_assignment_router
from app.adapters.controllers.faculty_controller import router as faculty_router

app.include_router(admin_assignment_router)
app.include_router(faculty_router)
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/controllers/faculty_controller.py main.py
git commit -m "feat: add faculty controller for subjects and availability"
```

---

## Task 11: Update Timetable Generator to Use Availability

**Files:**
- Modify: `app/adapters/services/timetable_generator.py`

- [ ] **Step 1: Update generator to use effective availability**

```python
# Add to imports in timetable_generator.py
from app.use_cases.faculty_availability import FacultyAvailabilityService

# Update TimetableGenerator class to accept availability service

class TimetableGenerator(ITimetableGenerator):
    """
    Timetable generation service using the new schema.

    Now integrates with faculty availability system.
    """

    # ... existing code ...

    def __init__(self, subjects: List[Subject], availability_service=None):
        """
        Initialize the generator with subjects and optional availability service.

        Args:
            subjects: List of subjects to schedule
            availability_service: Optional FacultyAvailabilityService for effective availability
        """
        self.subjects = subjects
        self.availability_service = availability_service
        self.time_slots = [TimeSlot(num, start, end)
                          for num, start, end in self.TIME_SLOTS]

    async def _get_faculty_availability(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str, academic_year: str
    ) -> List[Tuple[str, int]]:
        """
        Get effective availability for a faculty member.

        Returns: List of (day, slot) tuples that are available.
        """
        if not self.availability_service:
            # Return all slots if no availability service
            return [(d.value, s) for d in self.WORKING_DAYS for s in range(1, 11)]

        try:
            effective = await self.availability_service.get_effective_availability(
                faculty_id=faculty_id,
                subject_id=subject_id,
                semester=semester,
                section=section,
                academic_year=academic_year
            )

            return [(s["day"], s["slot"]) for s in effective.effective_slots]
        except Exception:
            # Fallback to all slots on error
            return [(d.value, s) for d in self.WORKING_DAYS for s in range(1, 11)]

    def _find_consecutive_slots(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        availability_set: set,  # Changed to set of (day, slot) tuples
        subject: Subject,
        section: str
    ) -> Optional[Tuple[DayOfWeek, int]]:
        """Find 2 consecutive available slots for a lab."""
        for day in self.WORKING_DAYS:
            for slot_num in range(1, 10):  # 1-9 for consecutive pairs
                # Check if this slot and next are free
                day_str = day.value
                if (
                    (day_str, slot_num) in availability_set and
                    (day_str, slot_num + 1) in availability_set and
                    slot_num not in self.LUNCH_SLOTS and
                    (slot_num + 1) not in self.LUNCH_SLOTS and
                    grid[day][slot_num] is None and
                    grid[day][slot_num + 1] is None
                ):
                    return (day, slot_num)

        return None

    def _find_available_slot(
        self,
        grid: Dict[DayOfWeek, Dict[int, Optional[TimetableSlot]]],
        availability_set: set,  # Changed to set of (day, slot) tuples
        subject: Subject,
        section: str,
        assigned_slots: set
    ) -> Optional[Tuple[DayOfWeek, int]]:
        """Find an available slot for a theory class."""
        for day in self.WORKING_DAYS:
            day_str = day.value
            for slot_num in range(1, 11):
                if (
                    slot_num not in self.LUNCH_SLOTS and
                    (day_str, slot_num) in availability_set and
                    grid[day][slot_num] is None and
                    (day, slot_num) not in assigned_slots
                ):
                    return (day, slot_num)

        return None
```

- [ ] **Step 2: Update use case to pass availability service**

```python
# Modify app/use_cases/timetable.py

# In the __init__ method of TimetableUseCase, accept availability_service
# And pass it to the generator when calling generate()

# Update generate_timetable to fetch and pass faculty availability
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/services/timetable_generator.py app/use_cases/timetable.py
git commit -m "feat: integrate faculty availability into timetable generation"
```

---

## Task 12: Frontend - Create Reusable SlotGrid Component

**Files:**
- Create: `frontend/src/components/shared/SlotGrid.jsx`
- Create: `frontend/src/utils/debounce.js`

- [ ] **Step 1: Create debounce utility**

```javascript
// frontend/src/utils/debounce.js

/**
 * Creates a debounced function that delays invoking func until after wait milliseconds.
 */
export function debounce(fn, delay) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}
```

- [ ] **Step 2: Create SlotGrid component**

```jsx
// frontend/src/components/shared/SlotGrid.jsx

import { cn } from '@/lib/utils';
import React from 'react';

const DEFAULT_DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI'];
const DEFAULT_SLOTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

/**
 * Reusable memoized slot grid component.
 * Handles keyboard navigation and accessibility.
 */
export const SlotGrid = React.memo(function SlotGrid({
  selectedSlots = [],
  onToggle,
  readonly = false,
  days = DEFAULT_DAYS,
  slots = DEFAULT_SLOTS,
  disabledSlots = [],
  className
}) {
  // Memoize computed values for performance
  const selectedSet = React.useMemo(
    () => new Set(selectedSlots.map(s => `${s.day}-${s.slot}`)),
    [selectedSlots]
  );

  const disabledSet = React.useMemo(
    () => new Set(disabledSlots.map(s => `${s.day}-${s.slot}`)),
    [disabledSlots]
  );

  const isSelected = (day, slot) => selectedSet.has(`${day}-${slot}`);
  const isDisabled = (day, slot) => readonly || disabledSet.has(`${day}-${slot}`);

  // Stable callback ref for keyboard handler
  const handleKeyDown = React.useCallback((day, slot, e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle(day, slot);
    }
  }, [onToggle]);

  return (
    <div className={cn("overflow-x-auto", className)}>
      <div className="inline-grid grid-cols-6 gap-1 min-w-max" role="grid">
        {/* Header row */}
        <div role="presentation" className="w-16" />
        {days.map(day => (
          <div
            key={day}
            className="w-10 text-center text-sm font-medium text-muted-foreground py-1"
            role="columnheader"
          >
            {day}
          </div>
        ))}

        {/* Slot rows */}
        {slots.map(slot => (
          <React.Fragment key={slot}>
            <div
              className="w-16 text-sm text-muted-foreground text-right pr-2 flex items-center justify-end"
              role="rowheader"
            >
              Slot {slot}
            </div>
            {days.map(day => {
              const selected = isSelected(day, slot);
              const disabled = isDisabled(day, slot);

              return (
                <button
                  key={`${day}-${slot}`}
                  type="button"
                  disabled={disabled}
                  onClick={() => onToggle(day, slot)}
                  onKeyDown={(e) => handleKeyDown(day, slot, e)}
                  role="gridcell"
                  aria-pressed={selected}
                  aria-label={`${day} slot ${slot}${selected ? ' selected' : ''}${disabled ? ' disabled' : ''}`}
                  aria-disabled={disabled}
                  tabIndex={disabled ? -1 : 0}
                  className={cn(
                    "h-9 w-10 rounded text-xs font-medium transition-all",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500",
                    disabled ? "cursor-not-allowed" : "cursor-pointer",
                    selected
                      ? "bg-violet-600 text-white hover:bg-violet-700 shadow-sm"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 hover:bg-gray-200 dark:hover:bg-gray-700",
                    disabled && "opacity-50"
                  )}
                >
                  {slot}
                </button>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
});

SlotGrid.displayName = 'SlotGrid';

// Helper hook for persistent academic year
export function useAcademicYear(defaultYear) {
  const currentYear = new Date().getFullYear();
  const yearToUse = defaultYear || `${currentYear}-${currentYear + 1}`;

  const [year, setYear] = React.useState(() => {
    const stored = localStorage.getItem('academic_year');
    return stored || yearToUse;
  });

  const updateYear = (newYear) => {
    setYear(newYear);
    localStorage.setItem('academic_year', newYear);
  };

  return [year, updateYear];
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/shared/SlotGrid.jsx frontend/src/utils/debounce.js
git commit -m "feat: add reusable SlotGrid component with accessibility"
```

---

## Task 13: Frontend - Create ErrorBoundary Component

**Files:**
- Create: `frontend/src/components/ErrorBoundary.jsx`

- [ ] **Step 1: Create ErrorBoundary component**

```jsx
// frontend/src/components/ErrorBoundary.jsx

import { Component } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';

/**
 * Error boundary component that catches React errors.
 * Provides a fallback UI and recovery option.
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center space-y-4 max-w-md">
            <div className="flex justify-center">
              <div className="h-16 w-16 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                <AlertCircle className="h-8 w-8 text-red-600" />
              </div>
            </div>
            <h2 className="text-xl font-semibold">Something went wrong</h2>
            <p className="text-muted-foreground">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <Button onClick={this.handleReset} variant="outline" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ErrorBoundary.jsx
git commit -m "feat: add ErrorBoundary component for crash recovery"
```

---

## Task 14: Frontend - Create SubjectCard Component

**Files:**
- Create: `frontend/src/components/faculty/SubjectCard.jsx`

- [ ] **Step 1: Create SubjectCard component**

```jsx
// frontend/src/components/faculty/SubjectCard.jsx

import { useState, useCallback, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SlotGrid } from '@/components/shared/SlotGrid';
import { Loader2, ChevronDown, ChevronUp, Check } from 'lucide-react';
import { facultyAvailabilityService } from '@/services/facultyAvailability';

/**
 * Accordion-style card for managing faculty availability per subject.
 * Includes loading guard, race-condition-proof toggle, and dirty checking.
 */
export function SubjectCard({
  subject,
  semester,
  section,
  academicYear,
  onError
}) {
  const [expanded, setExpanded] = useState(false);
  const [slots, setSlots] = useState([]);
  const [initialSlots, setInitialSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const loadingRef = useRef(false);

  const loadAvailability = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);

    try {
      const data = await facultyAvailabilityService.get(
        subject.id,
        semester,
        section,
        academicYear
      );
      const loadedSlots = data.available_slots || [];
      setSlots(loadedSlots);
      setInitialSlots(loadedSlots);
      setLoaded(true);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load availability';
      onError?.(errorMsg);
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [subject.id, semester, section, academicYear, onError]);

  useEffect(() => {
    if (expanded && !loaded && !loadingRef.current) {
      loadAvailability();
    }
  }, [expanded, loaded, loadAvailability]);

  // Race-condition-proof toggle using Map
  const toggleSlot = useCallback((day, slot) => {
    setSlots(prev => {
      const map = new Map(prev.map(s => [`${s.day}-${s.slot}`, s]));
      const key = `${day}-${slot}`;

      if (map.has(key)) {
        map.delete(key);
      } else {
        map.set(key, { day, slot });
      }

      return Array.from(map.values());
    });
    setSaved(false);
  }, []);

  const hasChanges = useCallback(() => {
    if (slots.length !== initialSlots.length) return true;
    const slotsKey = slots.map(s => `${s.day}-${s.slot}`).sort().join(',');
    const initialKey = initialSlots.map(s => `${s.day}-${s.slot}`).sort().join(',');
    return slotsKey !== initialKey;
  }, [slots, initialSlots]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);

    try {
      await facultyAvailabilityService.update({
        subject_id: subject.id,
        semester,
        section,
        academic_year: academicYear,
        available_slots: slots
      });
      setInitialSlots([...slots]);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to save availability';
      onError?.(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const minSlotsRequired = subject.credits || 1;
  const isValid = slots.length >= minSlotsRequired;
  const isDirty = hasChanges();

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex-1 text-left">
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {subject.name}
            </h3>
            <p className="text-sm text-muted-foreground">
              {subject.code} • Semester {semester}, Section {section} • {subject.credits} credits
            </p>
          </div>
          <Badge
            variant={slots.length >= minSlotsRequired ? "default" : "outline"}
            className="shrink-0"
          >
            {slots.length} / {minSlotsRequired}+ slots
          </Badge>
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-muted-foreground ml-2" />
        ) : (
          <ChevronDown className="h-5 w-5 text-muted-foreground ml-2" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-800 p-4">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-violet-600" />
            </div>
          ) : (
            <>
              <SlotGrid
                selectedSlots={slots}
                onToggle={toggleSlot}
                days={['MON', 'TUE', 'WED', 'THU', 'FRI']}
                slots={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
              />

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
                <p className="text-sm text-muted-foreground">
                  {isValid
                    ? `${slots.length} slots selected`
                    : `Minimum ${minSlotsRequired} slots required (current: ${slots.length})`
                  }
                </p>
                <Button
                  onClick={handleSave}
                  disabled={saving || !isDirty || !isValid}
                  className="gap-2"
                >
                  {saved ? (
                    <>
                      <Check className="h-4 w-4" />
                      Saved
                    </>
                  ) : (
                    <>
                      {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                      {saving ? 'Saving...' : 'Save Availability'}
                    </>
                  )}
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/faculty/SubjectCard.jsx
git commit -m "feat: add SubjectCard component with availability management"
```

---

## Task 15: Frontend - Create Faculty Portal Page

**Files:**
- Create: `frontend/src/pages/faculty/my-subjects.jsx`

- [ ] **Step 1: Create faculty subjects page**

```jsx
// frontend/src/pages/faculty/my-subjects.jsx

import { useState, useEffect } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { SubjectCard } from '@/components/faculty/SubjectCard';
import { useAcademicYear } from '@/components/shared/SlotGrid';
import { facultyAssignmentService } from '@/services/facultyAssignment';
import { Loader2, AlertCircle } from 'lucide-react';

function FacultySubjectsContent() {
  const [academicYear, setAcademicYear] = useAcademicYear();
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAssignedSubjects();
  }, [academicYear]);

  const fetchAssignedSubjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await facultyAssignmentService.getMySubjects(academicYear);
      setSubjects(data.assignments || []);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load assigned subjects';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleError = (message) => {
    setError(message);
    setTimeout(() => setError(null), 5000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">My Subjects</h1>
        <p className="text-muted-foreground">
          Manage your availability for assigned subjects
        </p>
      </div>

      <div className="flex items-center gap-4">
        <label className="text-sm font-medium">Academic Year:</label>
        <select
          value={academicYear}
          onChange={(e) => setAcademicYear(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="2024-2025">2024-2025</option>
          <option value="2025-2026">2025-2026</option>
          <option value="2026-2027">2026-2027</option>
        </select>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {subjects.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">
            No subjects assigned yet. Contact admin for assignment.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {subjects.map((assignment) => (
            <ErrorBoundary key={assignment.id}>
              <SubjectCard
                subject={assignment.subject}
                semester={assignment.semester}
                section={assignment.section}
                academicYear={academicYear}
                onError={handleError}
              />
            </ErrorBoundary>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FacultySubjectsPage() {
  return (
    <ErrorBoundary>
      <FacultySubjectsContent />
    </ErrorBoundary>
  );
}
```

- [ ] **Step 2: Add route to App.jsx**

```jsx
// Add to App.jsx routes
import FacultySubjectsPage from '@/pages/faculty/my-subjects';

// Add route for faculty
{user?.role === 'faculty' && (
  <Route path="/faculty/subjects" element={<FacultySubjectsPage />} />
)}
```

- [ ] **Step 3: Add navbar link**

```jsx
// Add to navbar.jsx navItems
{
  label: 'My Subjects',
  href: '/faculty/subjects',
  icon: BookOpen,  // or appropriate icon
  show: currentRole === 'faculty'
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/faculty/my-subjects.jsx frontend/src/App.jsx frontend/src/components/layout/navbar.jsx
git commit -m "feat: add faculty portal page for managing availability"
```

---

## Task 16: Frontend - Create Admin Assignment Form

**Files:**
- Create: `frontend/src/components/admin/AssignmentForm.jsx`
- Create: `frontend/src/pages/admin/assignments.jsx`

- [ ] **Step 1: Create AssignmentForm component**

```jsx
// frontend/src/components/admin/AssignmentForm.jsx

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { facultyAssignmentService } from '@/services/facultyAssignment';
import { adminService } from '@/services/admin';
import { Loader2, Check, AlertCircle } from 'lucide-react';

export function AssignmentForm({ onSuccess, onError }) {
  const [faculty, setFaculty] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [existingAssignments, setExistingAssignments] = useState([]);

  const [selectedFaculty, setSelectedFaculty] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [semester, setSemester] = useState(1);
  const [section, setSection] = useState('A');
  const [academicYear, setAcademicYear] = useState('2024-2025');

  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [facultyData, subjectsData, assignmentsData] = await Promise.all([
        adminService.getUsers({ role: 'faculty' }),
        fetch(`${import.meta.env.VITE_API_URL}/admin/subjects`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        }).then(r => r.json()),
        facultyAssignmentService.getAll()
      ]);

      setFaculty(facultyData.users || []);
      setSubjects(subjectsData.subjects || []);
      setExistingAssignments(assignmentsData.assignments || []);
    } catch (err) {
      setError('Failed to load required data');
      onError?.('Failed to load required data');
    } finally {
      setLoading(false);
    }
  };

  const hasExistingAssignment = () => {
    return existingAssignments.some(
      a => a.faculty_id === selectedFaculty &&
           a.semester === semester &&
           a.section === section &&
           a.academic_year === academicYear
    );
  };

  const getExistingAssignment = () => {
    return existingAssignments.find(
      a => a.faculty_id === selectedFaculty &&
           a.semester === semester &&
           a.section === section &&
           a.academic_year === academicYear
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const existing = hasExistingAssignment();
    if (existing) {
      const assignment = getExistingAssignment();
      setError(
        `Faculty is already assigned to ${assignment.subject_name} ` +
        `in semester ${semester}, section ${section}. Remove it first.`
      );
      return;
    }

    setAssigning(true);
    try {
      await facultyAssignmentService.assign({
        faculty_id: selectedFaculty,
        subject_id: selectedSubject,
        semester,
        section,
        academic_year: academicYear
      });

      setSuccess(true);
      onSuccess?.();

      // Reset form
      setSelectedFaculty('');
      setSelectedSubject('');
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Assignment failed';
      setError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setAssigning(false);
    }
  };

  const assignedSubjectIds = existingAssignments
    .filter(a => a.faculty_id === selectedFaculty && a.academic_year === academicYear)
    .map(a => a.subject_id);

  const availableSubjects = subjects.filter(
    s => !assignedSubjectIds.includes(s.id)
  );

  const existing = getExistingAssignment();

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-violet-600" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assign Subject to Faculty</CardTitle>
        <p className="text-sm text-muted-foreground">
          One faculty per subject per semester/section
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="faculty">Faculty *</Label>
            <Select value={selectedFaculty} onValueChange={setSelectedFaculty} required>
              <SelectTrigger id="faculty">
                <SelectValue placeholder="Select faculty member" />
              </SelectTrigger>
              <SelectContent>
                {faculty.map(f => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.full_name} ({f.email})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="semester">Semester *</Label>
              <Select value={String(semester)} onValueChange={(v) => setSemester(parseInt(v))} required>
                <SelectTrigger id="semester">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                    <SelectItem key={s} value={String(s)}>Semester {s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="section">Section *</Label>
              <Select value={section} onValueChange={setSection} required>
                <SelectTrigger id="section">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {['A', 'B', 'C'].map(s => (
                    <SelectItem key={s} value={s}>Section {s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="year">Academic Year *</Label>
              <Input
                id="year"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                placeholder="2024-2025"
                required
              />
            </div>
          </div>

          {existing && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0" />
              <p className="text-sm text-amber-800 dark:text-amber-300">
                Already assigned: <strong>{existing.subject_name}</strong>
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="subject">Subject *</Label>
            <Select
              value={selectedSubject}
              onValueChange={setSelectedSubject}
              disabled={!selectedFaculty || existing}
              required
            >
              <SelectTrigger id="subject">
                <SelectValue placeholder={selectedFaculty ? "Select subject" : "Select faculty first"} />
              </SelectTrigger>
              <SelectContent>
                {availableSubjects.length > 0 ? (
                  availableSubjects.map(s => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.code} - {s.name} ({s.credits} credits)
                    </SelectItem>
                  ))
                ) : (
                  <div className="p-2 text-sm text-muted-foreground text-center">
                    {selectedFaculty ? 'All subjects assigned' : 'Select faculty first'}
                  </div>
                )}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
              <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
              <p className="text-sm text-green-800 dark:text-green-300">
                Subject assigned successfully!
              </p>
            </div>
          )}

          <Button
            type="submit"
            disabled={assigning || !selectedFaculty || !selectedSubject || existing}
            className="w-full"
          >
            {assigning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Assigning...
              </>
            ) : (
              'Assign Subject to Faculty'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create admin assignments page**

```jsx
// frontend/src/pages/admin/assignments.jsx

import { useState, useEffect } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AssignmentForm } from '@/components/admin/AssignmentForm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { facultyAssignmentService } from '@/services/facultyAssignment';
import { Loader2, Trash2, AlertCircle } from 'lucide-react';

function AssignmentsContent() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchAssignments();
  }, [refreshKey]);

  const fetchAssignments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await facultyAssignmentService.getAll();
      setAssignments(data.assignments || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load assignments');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (assignmentId) => {
    if (!confirm('Are you sure you want to remove this assignment?')) return;

    try {
      await facultyAssignmentService.delete(assignmentId);
      setRefreshKey(prev => prev + 1);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete assignment');
    }
  };

  const handleSuccess = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleError = (msg) => {
    setError(msg);
    setTimeout(() => setError(null), 5000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Faculty Assignments</h1>
        <p className="text-muted-foreground">
          Assign subjects to faculty and manage their availability
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <AssignmentForm onSuccess={handleSuccess} onError={handleError} />

        <Card>
          <CardHeader>
            <CardTitle>Current Assignments</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-6 w-6 animate-spin text-violet-600" />
              </div>
            ) : assignments.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No assignments yet
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {assignments.map((assignment) => (
                  <div
                    key={assignment.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800"
                  >
                    <div>
                      <p className="font-medium">{assignment.subject_name}</p>
                      <p className="text-sm text-muted-foreground">
                        Semester {assignment.semester}, Section {assignment.section}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(assignment.id)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function AdminAssignmentsPage() {
  return (
    <ErrorBoundary>
      <AssignmentsContent />
    </ErrorBoundary>
  );
}
```

- [ ] **Step 3: Add route to App.jsx**

```jsx
// Add to App.jsx
import AdminAssignmentsPage from '@/pages/admin/assignments';

// Add route
{user?.role === 'admin' && (
  <Route path="/admin/assignments" element={<AdminAssignmentsPage />} />
)}
```

- [ ] **Step 4: Add navbar link**

```jsx
// Add to navbar.jsx navItems
{
  label: 'Assignments',
  href: '/admin/assignments',
  icon: Users,
  show: currentRole === 'admin'
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/admin/AssignmentForm.jsx frontend/src/pages/admin/assignments.jsx frontend/src/App.jsx frontend/src/components/layout/navbar.jsx
git commit -m "feat: add admin assignment management page"
```

---

## Task 17: Frontend - Create API Services

**Files:**
- Create: `frontend/src/services/facultyAssignment.js`
- Create: `frontend/src/services/facultyAvailability.js`
- Modify: `frontend/src/lib/api.js`

- [ ] **Step 1: Enhance api.js with better error handling**

```javascript
// frontend/src/lib/api.js

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Core API client with auth and error handling.
 * Always includes Authorization header and proper error handling.
 */
export async function api(endpoint, options = {}) {
  const token = localStorage.getItem('access_token');

  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  };

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);

    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }

    // Handle non-JSON responses
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.text();
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || `HTTP ${response.status}`);
    }

    return data;
  } catch (error) {
    // Enhance error with response details
    if (error.name === 'SyntaxError') {
      throw new Error('Invalid response from server');
    }
    throw error;
  }
}

// Convenience methods
export const apiClient = {
  get: (endpoint, options) => api(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, data, options) => api(endpoint, {
    ...options,
    method: 'POST',
    body: JSON.stringify(data),
  }),
  put: (endpoint, data, options) => api(endpoint, {
    ...options,
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (endpoint, options) => api(endpoint, { ...options, method: 'DELETE' }),
};
```

- [ ] **Step 2: Create facultyAssignment service**

```javascript
// frontend/src/services/facultyAssignment.js

import { api, apiClient } from '@/lib/api';

export const facultyAssignmentService = {
  // Faculty: Get my assigned subjects
  getMySubjects: async (academicYear = '2024-2025') => {
    return await api(`/faculty/subjects?academic_year=${academicYear}`);
  },

  // Admin: Create assignment
  assign: async (data) => {
    return await api('/admin/subject-assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Admin: Get all assignments
  getAll: async (filters = {}) => {
    const params = new URLSearchParams(filters).toString();
    return await api(`/admin/subject-assignments${params ? '?' + params : ''}`);
  },

  // Admin: Delete assignment
  delete: async (assignmentId) => {
    return await api(`/admin/subject-assignments/${assignmentId}`, {
      method: 'DELETE',
    });
  },
};
```

- [ ] **Step 3: Create facultyAvailability service**

```javascript
// frontend/src/services/facultyAvailability.js

import { api } from '@/lib/api';

export const facultyAvailabilityService = {
  // Faculty: Get availability for a subject
  get: async (subjectId, semester, section, academicYear = '2024-2025') => {
    const params = new URLSearchParams({
      semester,
      section,
      academic_year: academicYear,
    }).toString();
    return await api(`/faculty/availability/${subjectId}?${params}`);
  },

  // Faculty: Update availability
  update: async (data) => {
    return await api('/faculty/availability', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Admin: Get effective availability
  getEffective: async (filters) => {
    const params = new URLSearchParams(filters).toString();
    return await api(`/admin/faculty-availability/effective?${params}`);
  },

  // Admin: Create override
  createOverride: async (data) => {
    return await api('/admin/overrides', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Admin: Get override log
  getOverrides: async (filters = {}) => {
    const params = new URLSearchParams(filters).toString();
    return await api(`/admin/override-log${params ? '?' + params : ''}`);
  },

  // Admin: Delete override
  deleteOverride: async (overrideId) => {
    return await api(`/admin/override-log/${overrideId}`, {
      method: 'DELETE',
    });
  },
};
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.js frontend/src/services/facultyAssignment.js frontend/src/services/facultyAvailability.js
git commit -m "feat: add API services for faculty assignment and availability"
```

---

## Task 18: Write Tests for Backend Services

**Files:**
- Create: `tests/test_faculty_assignment.py`
- Create: `tests/test_faculty_availability.py`
- Create: `tests/test_admin_override.py`

- [ ] **Step 1: Create tests for faculty assignment service**

```python
# tests/test_faculty_assignment.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.use_cases.faculty_assignment import (
    FacultyAssignmentService, AssignSubjectRequest
)
from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.entities.faculty_availability import FacultyAvailability
from app.domain.exceptions import ValidationError


@pytest.fixture
def mock_repos():
    """Mock repositories."""
    assignment_repo = AsyncMock()
    availability_repo = AsyncMock()
    subject_repo = AsyncMock()
    db = AsyncMock()

    # Setup transaction context manager
    session = AsyncMock()
    session.start_transaction = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
    db.start_session = AsyncMock(return_value=session)
    db.start_session.return_value.__aenter__.return_value.start_transaction = AsyncMock()

    return {
        "assignment": assignment_repo,
        "availability": availability_repo,
        "subject": subject_repo,
        "db": db
    }


@pytest.fixture
def service(mock_repos):
    """Create service with mocked repositories."""
    return FacultyAssignmentService(
        assignment_repo=mock_repos["assignment"],
        availability_repo=mock_repos["availability"],
        subject_repo=mock_repos["subject"],
        db=mock_repos["db"]
    )


@pytest.mark.asyncio
async def test_assign_subject_success(service, mock_repos):
    """Test successful subject assignment."""
    # Setup mocks
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=None)
    mock_repos.assignment.find_by_faculty = AsyncMock(return_value=[])

    subject = MagicMock()
    subject.id = "subj123"
    mock_repos.subject.find_by_id = AsyncMock(return_value=subject)

    mock_repos.assignment.save = AsyncMock(return_value=MagicMock(id="assign123"))
    mock_repos.availability.save = AsyncMock(return_value=MagicMock())

    # Execute
    request = AssignSubjectRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025"
    )

    result = await service.assign_subject(request)

    # Verify
    mock_repos.assignment.save.assert_called_once()
    mock_repos.availability.save.assert_called_once()


@pytest.mark.asyncio
async def test_assign_subject_duplicate_fails(service, mock_repos):
    """Test that duplicate assignment fails."""
    # Setup mock for existing assignment
    existing = MagicMock()
    existing.subject_id = "other_subj"
    existing.semester = 1
    existing.section = "A"

    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=None)
    mock_repos.assignment.find_by_faculty = AsyncMock(return_value=[existing])

    # Execute
    request = AssignSubjectRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025"
    )

    # Verify raises error
    with pytest.raises(ValueError, match="already assigned"):
        await service.assign_subject(request)


@pytest.mark.asyncio
async def test_assign_subject_not_found_fails(service, mock_repos):
    """Test that assigning non-existent subject fails."""
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=None)
    mock_repos.assignment.find_by_faculty = AsyncMock(return_value=[])
    mock_repos.subject.find_by_id = AsyncMock(return_value=None)

    request = AssignSubjectRequest(
        faculty_id="fac123",
        subject_id="nonexistent",
        semester=1,
        section="A",
        academic_year="2024-2025"
    )

    with pytest.raises(ValueError, match="Subject not found"):
        await service.assign_subject(request)
```

- [ ] **Step 2: Create tests for faculty availability service**

```python
# tests/test_faculty_availability.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.use_cases.faculty_availability import (
    FacultyAvailabilityService, UpdateAvailabilityRequest, EffectiveAvailability
)
from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.entities.admin_override_log import AdminOverrideLog, OverrideSlot, OverrideType, OverrideAction


@pytest.fixture
def mock_repos():
    """Mock repositories."""
    availability_repo = AsyncMock()
    override_repo = AsyncMock()
    assignment_repo = AsyncMock()
    subject_repo = AsyncMock()
    return {
        "availability": availability_repo,
        "override": override_repo,
        "assignment": assignment_repo,
        "subject": subject_repo
    }


@pytest.fixture
def service(mock_repos):
    """Create service with mocked repositories."""
    # Attach repos directly for test access
    svc = FacultyAvailabilityService(
        availability_repo=mock_repos["availability"],
        override_repo=mock_repos["override"],
        assignment_repo=mock_repos["assignment"],
        subject_repo=mock_repos["subject"]
    )
    svc.availability_repo = mock_repos["availability"]
    svc.override_repo = mock_repos["override"]
    svc.assignment_repo = mock_repos["assignment"]
    svc.subject_repo = mock_repos["subject"]
    return svc


@pytest.mark.asyncio
async def test_update_availability_success(service, mock_repos):
    """Test successful availability update."""
    # Setup mocks
    assignment = MagicMock()
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=assignment)

    subject = MagicMock()
    subject.credits = 3
    mock_repos.subject.find_by_id = AsyncMock(return_value=subject)

    existing = MagicMock()
    existing.available_slots = []
    mock_repos.availability.find = AsyncMock(return_value=existing)
    mock_repos.availability.update = AsyncMock(return_value=existing)

    request = UpdateAvailabilityRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 1}
        ],
        requesting_faculty_id="fac123"
    )

    result = await service.update_availability(request)

    mock_repos.availability.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_availability_ownership_fails(service, mock_repos):
    """Test that faculty can only modify own availability."""
    assignment = MagicMock()
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=assignment)

    request = UpdateAvailabilityRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025",
        available_slots=[],
        requesting_faculty_id="other_faculty"  # Different user
    )

    with pytest.raises(PermissionError, match="Can only modify own availability"):
        await service.update_availability(request)


@pytest.mark.asyncio
async def test_update_availability_min_slots_fails(service, mock_repos):
    """Test that minimum slot validation works."""
    assignment = MagicMock()
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=assignment)

    subject = MagicMock()
    subject.credits = 3  # Requires 3 slots
    mock_repos.subject.find_by_id = AsyncMock(return_value=subject)

    request = UpdateAvailabilityRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025",
        available_slots=[{"day": "MON", "slot": 1}],  # Only 1 slot
        requesting_faculty_id="fac123"
    )

    with pytest.raises(ValueError, match="Minimum 3 slots required"):
        await service.update_availability(request)


@pytest.mark.asyncio
async def test_get_effective_availability_with_overrides(service, mock_repos):
    """Test effective availability computation with overrides."""
    # Base slots: MON-1, MON-2
    base = MagicMock()
    base.available_slots = [
        AvailableSlot(day=DayOfWeek.MON, slot=1),
        AvailableSlot(day=DayOfWeek.MON, slot=2)
    ]
    mock_repos.availability.find = AsyncMock(return_value=base)

    # Override: remove MON-2, add TUE-1
    override = MagicMock()
    override.slots = [
        OverrideSlot(day=DayOfWeek.MON, slot=2, action=OverrideAction.REMOVE),
        OverrideSlot(day=DayOfWeek.TUE, slot=1, action=OverrideAction.ADD)
    ]
    override.timestamp = datetime(2025, 1, 1, 10, 0, 0)
    mock_repos.override.find_applicable = AsyncMock(return_value=[override])

    result = await service.get_effective_availability(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025"
    )

    # Result should have MON-1 (kept), TUE-1 (added), but not MON-2 (removed)
    assert len(result.effective_slots) == 2
    assert {"day": "MON", "slot": 1} in result.effective_slots
    assert {"day": "TUE", "slot": 1} in result.effective_slots
```

- [ ] **Step 3: Create tests for admin override service**

```python
# tests/test_admin_override.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.use_cases.admin_override import (
    AdminOverrideService, CreateOverrideRequest
)
from app.domain.entities.admin_override_log import OverrideType


@pytest.fixture
def mock_repos():
    """Mock repositories."""
    override_repo = AsyncMock()
    assignment_repo = AsyncMock()
    return {
        "override": override_repo,
        "assignment": assignment_repo
    }


@pytest.fixture
def service(mock_repos):
    """Create service with mocked repositories."""
    return AdminOverrideService(
        override_repo=mock_repos["override"],
        assignment_repo=mock_repos["assignment"]
    )


@pytest.mark.asyncio
async def test_create_override_persistent_success(service, mock_repos):
    """Test successful persistent override creation."""
    assignment = MagicMock()
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=assignment)

    override = MagicMock()
    override.id = "override123"
    mock_repos.override.save = AsyncMock(return_value=override)

    request = CreateOverrideRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025",
        override_type=OverrideType.PERSISTENT,
        slots=[
            {"day": "MON", "slot": 3, "action": "add"}
        ],
        admin_id="admin123"
    )

    result = await service.create_override(request)

    mock_repos.override.save.assert_called_once()
    assert result.message == "Override created successfully"


@pytest.mark.asyncio
async def test_create_override_invalid_slot_fails(service, mock_repos):
    """Test that invalid slot format is rejected."""
    assignment = MagicMock()
    mock_repos.assignment.find_faculty_assignment = AsyncMock(return_value=assignment)

    request = CreateOverrideRequest(
        faculty_id="fac123",
        subject_id="subj123",
        semester=1,
        section="A",
        academic_year="2024-2025",
        override_type=OverrideType.PERSISTENT,
        slots=[
            {"day": "INVALID", "slot": 3, "action": "add"}  # Invalid day
        ],
        admin_id="admin123"
    )

    with pytest.raises(ValueError, match="Invalid day"):
        await service.create_override(request)


@pytest.mark.asyncio
async def test_delete_applied_override_fails(service, mock_repos):
    """Test that applied one-time overrides cannot be deleted."""
    override = MagicMock()
    override.override_type = OverrideType.ONE_TIME
    override.applied = True
    mock_repos.override.find_by_id = AsyncMock(return_value=override)

    with pytest.raises(ValueError, match="Cannot delete applied"):
        await service.delete_override("override123", "admin123")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
# Run all new tests
pytest tests/test_faculty_assignment.py -v
pytest tests/test_faculty_availability.py -v
pytest tests/test_admin_override.py -v

# Expected: All tests PASS
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_faculty_assignment.py tests/test_faculty_availability.py tests/test_admin_override.py
git commit -m "test: add tests for faculty assignment and availability services"
```

---

## Task 19: Create Migration Script for Existing Data

**Files:**
- Create: `app/migrations/migration_003_faculty_assignment_availability.py`

- [ ] **Step 1: Create migration for existing assignments**

```python
# app/migrations/migration_003_faculty_assignment_availability.py

"""
Migration 003: Create faculty_availability collection for existing assignments.

Creates blank availability records for all existing subject assignments.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime


async def upgrade(db: AsyncIOMotorDatabase) -> None:
    """Create blank availability records for existing assignments."""
    print("Migration 003: Creating faculty availability records...")

    # Get all existing subject assignments
    assignments = await db.subject_assignments.find({}).to_list(length=None)

    created_count = 0
    skipped_count = 0

    for assignment in assignments:
        # Check if availability already exists
        existing = await db.faculty_availability.find_one({
            "faculty_id": assignment["faculty_id"],
            "subject_id": assignment["subject_id"],
            "semester": assignment["semester"],
            "section": assignment["section"],
            "academic_year": assignment.get("academic_year", "2024-2025")
        })

        if existing:
            skipped_count += 1
            continue

        # Create blank availability record
        await db.faculty_availability.insert_one({
            "faculty_id": assignment["faculty_id"],
            "subject_id": assignment["subject_id"],
            "semester": assignment["semester"],
            "section": assignment["section"],
            "academic_year": assignment.get("academic_year", "2024-2025"),
            "available_slots": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        created_count += 1

    print(f"Migration 003 complete: Created {created_count} records, skipped {skipped_count}")


async def downgrade(db: AsyncIOMotorDatabase) -> None:
    """Remove faculty availability collection."""
    print("Migration 003 downgrade: Dropping faculty_availability collection...")
    await db.faculty_availability.drop()
    print("Migration 003 downgrade complete")
```

- [ ] **Step 2: Update migrations runner to include new migration**

```python
# Add to migrations/__init__.py or main migration runner

MIGRATIONS = [
    # ... existing migrations ...
    "migration_003_faculty_assignment_availability"
]
```

- [ ] **Step 3: Commit**

```bash
git add app/migrations/migration_003_faculty_assignment_availability.py
git commit -m "feat: add migration to create availability records for existing assignments"
```

---

## Task 20: Update README Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add feature documentation to README**

```markdown
# Faculty Assignment & Availability System

## Overview

The system includes a faculty assignment and availability management feature that allows:
- Admins to assign subjects to faculty
- Faculty to set their preferred available time slots
- Admins to override faculty availability when needed
- Full audit logging of all admin actions

## API Endpoints

### Admin Endpoints
- `POST /admin/subject-assignments` - Assign subject to faculty
- `GET /admin/subject-assignments` - List all assignments
- `DELETE /admin/subject-assignments/{id}` - Remove assignment
- `POST /admin/overrides` - Create availability override
- `GET /admin/faculty-availability/effective` - Get computed availability
- `GET /admin/override-log` - View audit trail

### Faculty Endpoints
- `GET /faculty/subjects` - List assigned subjects
- `GET /faculty/availability/{subject_id}` - Get availability
- `POST /faculty/availability` - Update availability

## Database Collections

### faculty_availability
Stores faculty's preferred available slots per subject assignment.

### admin_override_log
Audit log for all admin availability overrides.

## Constraints

- One faculty = One subject per semester/section (enforced via unique index)
- Availability is per-subject-assignment (not global)
- Minimum slots = subject credits
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add faculty assignment and availability feature documentation"
```

---

## Summary

This implementation plan covers:

1. **Backend** (Tasks 1-11):
   - Domain entities for availability and overrides
   - Repository interfaces and MongoDB implementations
   - Service layer with transaction safety
   - FastAPI controllers with RBAC
   - Integration with timetable generator

2. **Frontend** (Tasks 12-17):
   - Reusable SlotGrid component with accessibility
   - ErrorBoundary for crash recovery
   - SubjectCard for per-subject availability management
   - Faculty portal page
   - Admin assignment management page
   - API services with error handling

3. **Testing & Migration** (Tasks 18-19):
   - Unit tests for all services
   - Migration for existing data

4. **Documentation** (Task 20):
   - README updates

Total: 20 tasks, each with detailed steps and code.
