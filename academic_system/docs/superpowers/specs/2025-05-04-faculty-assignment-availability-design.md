# Faculty Assignment & Availability System - Design Document

**Date:** 2025-05-04
**Status:** Approved
**Version:** 1.0

---

## Executive Summary

A production-ready system for managing faculty subject assignments and availability preferences in the academic timetable management system. The system enables admins to assign subjects to faculty, faculty to specify their preferred time slots, and admins to override availability when needed—all with full audit logging.

**Key Constraints:**
- One faculty = One subject per semester/section
- Availability is per-subject-assignment (not global)
- Two override types: persistent and one-time
- Full audit trail for all admin actions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (React)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │    Admin    │  │   Faculty   │  │      Shared Components      │ │
│  │  Pages      │  │   Pages     │  │  (SlotGrid, ErrorBoundary)  │ │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┬───────────────┘ │
│         │                │                      │                   │
│         └────────────────┴──────────────────────┘                   │
│                            │                                         │
│                    ┌───────▼────────┐                               │
│                    │  API Services  │                               │
│                    │  (apiClient)   │                               │
│                    └───────┬────────┘                               │
└────────────────────────────┼─────────────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────┼─────────────────────────────────────────┐
│                    ┌───────▼────────┐                               │
│                    │ FastAPI Routes │                               │
│                    │ (Controllers)  │                               │
│                    └───────┬────────┘                               │
│                            │                                         │
│              ┌─────────────┼─────────────┐                          │
│              │             │             │                          │
│      ┌───────▼──────┐ ┌───▼────┐ ┌─────▼─────┐                    │
│      │   Assignment  │ │  Avail.│ │  Override  │                    │
│      │   Service     │ │ Service│ │  Service   │                    │
│      └───────┬──────┘ └───┬────┘ └─────┬─────┘                    │
│              │             │             │                          │
│              └─────────────┼─────────────┘                          │
│                            │                                        │
│                    ┌───────▼────────┐                               │
│              │   Repositories   │                               │
│              │   (MongoDB)      │                               │
│              └──────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### 1. Collection: `subject_assignments`

Stores the link between faculty and subjects for a specific semester/section.

```javascript
// UNIQUE Index: {faculty_id: 1, semester: 1, section: 1, academic_year: 1}
// Index: {subject_id: 1, semester: 1, section: 1, academic_year: 1}

{
  _id: ObjectId,
  subject_id: ObjectId,      // References subjects collection
  faculty_id: ObjectId,      // References users collection
  semester: Number,          // 1-8
  section: String,           // "A", "B", "C"
  academic_year: String,     // "2024-2025"
  created_at: DateTime
}
```

**Constraints:**
- Unique: `(faculty_id, semester, section, academic_year)`
- One faculty teaches only ONE subject per semester/section

---

### 2. Collection: `faculty_availability`

Stores faculty's preferred available slots for each subject assignment.

```javascript
// UNIQUE Index: {faculty_id: 1, subject_id: 1, semester: 1, section: 1, academic_year: 1}
// Index: {faculty_id: 1, semester: 1, section: 1, academic_year: 1}
// Index: {subject_id: 1, semester: 1, section: 1, academic_year: 1}

{
  _id: ObjectId,
  faculty_id: ObjectId,      // References users
  subject_id: ObjectId,      // References subjects
  semester: Number,
  section: String,
  academic_year: String,
  available_slots: [
    {
      day: "MON" | "TUE" | "WED" | "THU" | "FRI" | "SAT",
      slot: Number           // 1-10
    }
  ],
  created_at: DateTime,
  updated_at: DateTime
}
```

**Constraints:**
- Unique per subject assignment
- `day` is restricted to MON-SAT enum
- `slot` is restricted to 1-10 range

---

### 3. Collection: `admin_override_log`

Audit log for all admin availability overrides.

```javascript
// Index: {faculty_id: 1, subject_id: 1, semester: 1, section: 1, academic_year: 1}
// Index: {faculty_id: 1, subject_id: 1}
// Index: {timestamp: -1}

{
  _id: ObjectId,
  admin_id: ObjectId,        // Who made the override
  faculty_id: ObjectId,      // Target faculty
  subject_id: ObjectId,
  semester: Number,
  section: String,
  academic_year: String,
  override_type: "persistent" | "one_time",
  applied: Boolean,          // True = used in generation (one-time only)
  slots: [
    {
      day: "MON" | "TUE" | "WED" | "THU" | "FRI" | "SAT",
      slot: Number,          // 1-10
      action: "add" | "remove"  // add=force include, remove=force exclude
    }
  ],
  timestamp: DateTime
}
```

**Override Semantics:**
- `action: "add"` → Force include this slot
- `action: "remove"` → Force exclude this slot
- `persistent` → Remains in effect until deleted
- `one_time` → Marked `applied=true` after timetable generation

---

## API Endpoints

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/subject-assignments` | Assign subject to faculty (creates blank availability) |
| GET | `/admin/subject-assignments` | List all assignments (filterable) |
| DELETE | `/admin/subject-assignments/{id}` | Remove assignment (cascades to availability) |
| POST | `/admin/overrides` | Create availability override (persistent or one-time) |
| GET | `/admin/faculty-availability/effective` | Get computed availability (base + overrides) |
| GET | `/admin/override-log` | View audit trail with filters |
| DELETE | `/admin/override-log/{id}` | Remove override (only if not applied) |

### Faculty Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/faculty/subjects` | List assigned subjects for current faculty |
| GET | `/faculty/availability/{subject_id}` | Get availability for specific subject |
| POST | `/faculty/availability` | Update available slots for a subject |

---

## Service Layer Design

### FacultyAssignmentService

**Responsibility:** Manage subject-to-faculty assignments with transaction safety.

**Key Methods:**
- `assign_subject()` - Creates assignment + blank availability atomically
- Validates unique constraint before creation
- Uses MongoDB transactions for data integrity

### FacultyAvailabilityService

**Responsibility:** Manage faculty preferences and compute effective availability.

**Key Methods:**
- `update_availability()` - Updates existing record (not create new)
- `get_effective_availability()` - Computes base + overrides
- `_apply_overrides()` - Merges base slots with override actions
- `_dedupe_and_sort()` - Ensures output is unique and sorted

**Availability Priority:**
1. Base slots (faculty preference)
2. Persistent overrides (admin)
3. One-time overrides (admin, not yet applied)

### AdminOverrideService

**Responsibility:** Manage admin overrides with audit logging.

**Key Methods:**
- `create_override()` - Stores in log only (doesn't modify availability)
- `delete_override()` - Removes if not yet applied (one-time)
- Validates slot format (day enum, slot range)

### TimetableIntegrationService

**Responsibility:** Bridge availability system with timetable generation.

**Key Methods:**
- `get_availability_for_generation()` - Returns effective availability for all faculty
- `mark_one_time_overrides_applied()` - Marks used overrides after generation

---

## React Component Structure

```
src/
├── components/
│   ├── ErrorBoundary.jsx           # Error wrapper component
│   ├── faculty/
│   │   └── SubjectCard.jsx         # Accordion card with slot grid
│   ├── admin/
│   │   └── AssignmentForm.jsx      # Subject assignment form
│   └── shared/
│       └── SlotGrid.jsx            # Reusable memoized grid
├── pages/
│   ├── faculty/
│   │   └── my-subjects.jsx         # Faculty portal main page
│   └── admin/
│       └── assignments.jsx         # Admin assignment page
├── services/
│   ├── facultyAssignment.js        # API client for assignments
│   ├── facultyAvailability.js      # API client for availability
│   └── lib/
│       └── api.js                  # Core API client with auth
└── utils/
    └── debounce.js                 # Debounce utility
```

---

## Key Frontend Features

### SlotGrid Component
- **Memoized** with `React.memo()` for performance
- **Keyboard navigation** (Enter/Space to toggle)
- **ARIA attributes** for accessibility
- **Configurable** days/slots via props

### SubjectCard Component
- **Accordion pattern** for per-subject availability
- **Dirty checking** - Save only when changes made
- **Debounced save** - Prevents API spam
- **Race condition proof** - Uses Map for uniqueness
- **Loading guard** - Prevents unnecessary refetch

### ErrorBoundary Component
- Wraps entire page for crash recovery
- Shows friendly error message
- Provides "Try Again" button

### useAcademicYear Hook
- Persists year to localStorage
- Survives page refresh
- Provides consistent default

---

## Timetable Integration

### Availability Resolution Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Fetch base availability from faculty_availability       │
│     → faculty_id, subject_id, semester, section, year       │
├─────────────────────────────────────────────────────────────┤
│  2. Fetch applicable overrides from admin_override_log      │
│     → Persistent + one_time (applied=false)                 │
│     → Sorted by timestamp (newest last)                     │
├─────────────────────────────────────────────────────────────┤
│  3. Apply overrides to base slots                           │
│     → action="add": Force include                           │
│     → action="remove": Force exclude                        │
├─────────────────────────────────────────────────────────────┤
│  4. Deduplicate and sort result                             │
│     → Unique (day, slot) pairs                              │
│     → Sorted by day, then slot                              │
├─────────────────────────────────────────────────────────────┤
│  5. Return effective_slots to timetable generator           │
└─────────────────────────────────────────────────────────────┘
```

### Scheduling Priority

When generating timetables:
1. **Faculty-defined availability** (highest priority)
2. **Admin persistent overrides**
3. **One-time overrides** (for current generation)
4. **Fallback assignment** (only if necessary, logged as violation)

---

## RBAC Rules

| Role | Can... |
|------|--------|
| **Admin** | Assign subjects, view all availability, create overrides, delete overrides |
| **Faculty** | View own subjects, update own availability, view own availability |
| **Student** | No access to this feature |

**Security Measures:**
- Faculty can only modify `faculty_id` matching their JWT token
- All admin actions logged with `admin_id`
- Override deletion blocked if already applied

---

## Data Validation

### Pydantic Models

```python
class SlotSchema(BaseModel):
    day: DayOfWeek           # Enum: MON-SAT
    slot: int                # 1-10

class FacultyAvailabilityCreate(BaseModel):
    faculty_id: str
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=2)
    academic_year: str
    available_slots: List[SlotSchema]

class AdminOverrideCreate(BaseModel):
    faculty_id: str
    subject_id: str
    semester: int = Field(ge=1, le=8)
    section: str
    academic_year: str
    override_type: OverrideType  # persistent | one_time
    slots: List[SlotSchema]
```

---

## Migration Strategy

1. **Create collections** - `faculty_availability`, `admin_override_log`
2. **Add indexes** - All unique and compound indexes
3. **Update existing** - Add `academic_year` to existing `subject_assignments` if needed
4. **Deploy backend** - New services and controllers
5. **Deploy frontend** - New pages and components
6. **Data migration** - Create blank availability records for existing assignments

---

## Success Criteria

- [ ] Admin can assign subjects to faculty
- [ ] Faculty can set availability per assigned subject
- [ ] Availability persists across sessions
- [ ] Admin can view effective availability (base + overrides)
- [ ] Admin can create persistent and one-time overrides
- [ ] All overrides are logged with admin_id
- [ ] Timetable generation uses effective availability
- [ ] Faculty cannot modify other faculty's availability
- [ ] Unique constraint enforced (one subject per faculty/semester/section)
- [ ] Error boundary prevents page crashes

---

## Appendix: Response Formats

### Effective Availability Response

```json
{
  "base_slots": [
    {"day": "MON", "slot": 1},
    {"day": "MON", "slot": 2}
  ],
  "overrides": [
    {
      "admin_id": "...",
      "type": "persistent",
      "slots": [
        {"day": "TUE", "slot": 3, "action": "add"}
      ],
      "timestamp": "2025-05-04T10:00:00Z"
    }
  ],
  "effective_slots": [
    {"day": "MON", "slot": 1},
    {"day": "MON", "slot": 2},
    {"day": "TUE", "slot": 3}
  ]
}
```

---

*Document Version: 1.0*
*Last Updated: 2025-05-04*
