# Database Schema Refactor Design

## Overview
Production-level refactor of MongoDB schema for scalability and maintainability.

---

## 1. Collections

### 1.1 Timetables (REDESIGNED)

**Before:** One document per slot (~60 docs per semester-section)
**After:** One document per semester-section with version history

```javascript
{
  _id: ObjectId,
  semester: Number,           // 1-8
  section: String,            // "A", "B", etc.
  academic_year: String,      // "2024-2025"
  version: Number,            // Incrementing version
  is_active: Boolean,         // Only ONE active per sem/sec/year
  schedule: [
    {
      day: "MON"|"TUE"|"WED"|"THU"|"FRI"|"SAT",
      slots: [
        {
          slot: Number,           // 1-10
          subject_id: ObjectId,
          faculty_id: ObjectId,
          room: String            // Optional
        }
      ]
    }
  ],
  created_by: ObjectId,       // User who created this version
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
```javascript
// Primary lookup - active timetable only
db.timetables.createIndex(
  { semester: 1, section: 1, academic_year: 1, is_active: 1 },
  { partialFilterExpression: { is_active: true } }
)

// Faculty schedule lookup
db.timetables.createIndex({ "schedule.slots.faculty_id": 1 })

// Subject schedule lookup
db.timetables.createIndex({ "schedule.slots.subject_id": 1 })
```

---

### 1.2 Subject Assignments (NEW COLLECTION)

Replaces `Subject.sections` array. Supports multiple faculty per subject.

```javascript
{
  _id: ObjectId,
  subject_id: ObjectId,       // References subjects._id
  semester: Number,           // 1-8
  section: String,            // "A", "B", etc.
  faculty_id: ObjectId,       // References users._id
  academic_year: String,      // "2024-2025"
  is_primary: Boolean,        // Default: true (for multi-faculty scenarios)
  created_at: ISODate
}
```

**Indexes:**
```javascript
// Unique constraint - one assignment per subject/sem/section/faculty/year
db.subject_assignments.createIndex(
  { subject_id: 1, semester: 1, section: 1, faculty_id: 1, academic_year: 1 },
  { unique: true }
)

// Faculty's assigned subjects (for auth validation)
db.subject_assignments.createIndex({ faculty_id: 1, semester: 1 })

// Find all subjects for a semester-section
db.subject_assignments.createIndex({ semester: 1, section: 1, academic_year: 1 })

// Subject's assigned faculty
db.subject_assignments.createIndex({ subject_id: 1 })
```

---

### 1.3 Subjects (SIMPLIFIED)

**Removed:** `sections` array (moved to subject_assignments)
**Removed:** `faculty_id` (moved to subject_assignments)

```javascript
{
  _id: ObjectId,
  code: String,               // "CS101" (unique)
  name: String,               // "Introduction to Computing"
  subject_type: String,       // "theory" | "lab" | "elective" | "core"
  credits: Number,            // 1-6
  classes_per_week: Number,   // 1-10
  description: String,        // Optional
  syllabus: String,           // Optional
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
```javascript
db.subjects.createIndex({ code: 1 }, { unique: true })
db.subjects.createIndex({ subject_type: 1 })
```

---

### 1.4 Users (MINOR CHANGES)

**Added:** `employee_id` index

**Indexes:**
```javascript
db.users.createIndex({ email: 1 }, { unique: true })
db.users.createIndex({ roll_number: 1 }, { unique: true, sparse: true })
db.users.createIndex({ employee_id: 1 }, { sparse: true })  // ← NEW
db.users.createIndex({ role: 1 })
db.users.createIndex({ role: 1, semester: 1 })
```

---

### 1.5 Attendances (INDEX ADDITION)

```javascript
{
  _id: ObjectId,
  student_id: ObjectId,
  subject_id: ObjectId,
  faculty_id: ObjectId,       // Who marked attendance
  date: Date,                 // Class date
  status: String,             // "present" | "absent" | "excused"
  remarks: String,            // Optional
  marked_at: ISODate,
  updated_at: ISODate
}
```

**Indexes:**
```javascript
// Unique constraint - one record per student/subject/date
db.attendances.createIndex(
  { student_id: 1, subject_id: 1, date: 1 },
  { unique: true }
)

// Faculty's attendance marking history (for auth validation)
db.attendances.createIndex({ faculty_id: 1, date: 1 })  // ← NEW

// Subject attendance on a date
db.attendances.createIndex({ subject_id: 1, date: 1 })

// Student's attendance history
db.attendances.createIndex({ student_id: 1 })
```

---

### 1.6 Study Materials (INDEX ADDITION)

**Indexes:**
```javascript
db.study_materials.createIndex({ subject_id: 1, semester: 1 })
db.study_materials.createIndex({ faculty_id: 1 })
db.study_materials.createIndex({ semester: 1 })  // ← NEW
db.study_materials.createIndex({ uploaded_at: -1 })
```

---

## 2. Entity Models (Pydantic)

### 2.1 TimetableSlot

```python
@dataclass
class TimetableSlot:
    """Single time slot in schedule."""
    slot: int                    # 1-10
    subject_id: str              # References subject
    faculty_id: str              # References faculty
    room: Optional[str] = None
```

### 2.2 DaySchedule

```python
@dataclass
class DaySchedule:
    """Schedule for one day."""
    day: DayOfWeek               # MON, TUE, etc.
    slots: List[TimetableSlot]
```

### 2.3 Timetable (REDESIGNED)

```python
@dataclass
class Timetable:
    """Complete timetable for a semester-section."""
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
```

### 2.4 SubjectAssignment

```python
@dataclass
class SubjectAssignment:
    """Links subject to semester-section-faculty."""
    id: str
    subject_id: str
    semester: int
    section: str
    faculty_id: str
    academic_year: str
    is_primary: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### 2.5 Subject (SIMPLIFIED)

```python
@dataclass
class Subject:
    """Subject catalog entry."""
    id: str
    code: str
    name: str
    subject_type: SubjectType
    credits: int
    classes_per_week: int
    description: Optional[str] = None
    syllabus: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
```

---

## 3. Service Layer Changes

### 3.1 Faculty Assignment Validation

```python
class AttendanceUseCase:
    async def mark_attendance(
        self,
        faculty_id: str,
        subject_id: str,
        date: date,
        attendance_data: List[AttendanceRecord]
    ) -> None:
        # CRITICAL: Verify faculty is assigned to this subject
        assignment = await self.assignment_repo.find_faculty_assignment(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=self._extract_semester(attendance_data),
            section=self._extract_section(attendance_data)
        )

        if not assignment:
            raise PermissionDenied(
                f"Faculty is not assigned to teach this subject"
            )

        # Proceed with marking
        await self.attendance_repo.save_batch(attendance_data)
```

### 3.2 Timetable Version Management

```python
class TimetableUseCase:
    async def update_timetable(
        self,
        semester: int,
        section: str,
        new_schedule: List[DaySchedule],
        created_by: str
    ) -> Timetable:
        """Create new version, deactivate old version."""

        # Deactivate existing active timetable
        await self.timetable_repo.deactivate_active(
            semester=semester,
            section=section
        )

        # Get latest version number
        latest_version = await self.timetable_repo.get_latest_version(
            semester=semester,
            section=section
        )

        # Create new active version
        new_timetable = Timetable(
            semester=semester,
            section=section,
            academic_year=self.current_academic_year,
            version=latest_version + 1,
            is_active=True,
            schedule=new_schedule,
            created_by=created_by
        )

        return await self.timetable_repo.save(new_timetable)
```

---

## 4. Aggregation Queries (Optimized)

### 4.1 Enriched Timetable (Cached/Lazy)

```python
# Only enrich when needed (display), not for validation
async def get_timetable_enriched(
    semester: int,
    section: str
) -> dict:
    pipeline = [
        {"$match": {
            "semester": semester,
            "section": section,
            "is_active": True
        }},
        {"$lookup": {
            "from": "subjects",
            "let": {"subject_ids": "$schedule.slots.subject_id"},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$_id", "$$subject_ids"]}}}
            ],
            "as": "subjects"
        }},
        {"$lookup": {
            "from": "users",
            "let": {"faculty_ids": "$schedule.slots.faculty_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$in": ["$_id", "$$faculty_ids"]},
                    "role": "faculty"
                }},
                {"$project": {
                    "id": {"$toString": "$_id"},
                    "full_name": 1,
                    "email": 1
                }}
            ],
            "as": "faculty"
        }}
    ]
```

---

## 5. Migration Strategy

### Phase 1: Add New Collections (Zero Downtime)
```python
# 1. Create subject_assignments collection
# 2. Migrate data from subjects.sections array
async def migrate_subject_assignments():
    subjects = await db.subjects.find({"sections": {"$exists": true}}).to_list(None)

    for subject in subjects:
        for section in subject["sections"]:
            assignment = {
                "subject_id": subject["_id"],
                "semester": subject["semester"],
                "section": section,
                "faculty_id": subject["faculty_id"],
                "academic_year": "2024-2025",
                "is_primary": True,
                "created_at": datetime.utcnow()
            }
            await db.subject_assignments.insert_one(assignment)
```

### Phase 2: Redesign Timetable
```python
async def migrate_timetables():
    # 1. Read existing timetable entries
    entries = await db.timetable_entries.find({}).to_list(None)

    # 2. Group by semester-section-academic_year
    grouped = {}
    for entry in entries:
        key = (entry["semester"], entry["section"], entry.get("academic_year", "2024-2025"))
        if key not in grouped:
            grouped[key] = {"entries": [], "faculty": set(), "subjects": set()}
        grouped[key]["entries"].append(entry)

    # 3. Create new timetable documents
    for (sem, sec, year), data in grouped.items():
        schedule = build_schedule_from_entries(data["entries"])
        await db.timetables.insert_one({
            "semester": sem,
            "section": sec,
            "academic_year": year,
            "version": 1,
            "is_active": True,
            "schedule": schedule,
            "created_at": datetime.utcnow()
        })

    # 4. Drop old collection after verification
    await db.timetable_entries.drop()
```

### Phase 3: Update Indexes
```python
async def add_new_indexes():
    # Add new indexes
    await db.users.create_index({"employee_id": 1}, {"sparse": True})
    await db.attendances.create_index({"faculty_id": 1, "date": 1})
    await db.study_materials.create_index({"semester": 1})
```

### Phase 4: Clean Up
```python
async def cleanup_subject_collection():
    # Remove sections and faculty_id from subjects
    await db.subjects.update_many(
        {},
        {"$unset": {"sections": "", "faculty_id": ""}}
    )
```

---

## 6. Backward Compatibility

- **API Contracts:** Keep same response structures
- **Fallback Queries:** Check both old and new collections during transition
- **Feature Flag:** Use `settings.use_new_schema` config during migration
