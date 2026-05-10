# Academic Management System - Complete Codebase Flow Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [User Roles & Permissions](#user-roles--permissions)
3. [Core Domain Entities](#core-domain-entities)
4. [Repository Layer](#repository-layer)
5. [Use Case Layer](#use-case-layer)
6. [Controller Layer](#controller-layer)
7. [Complete Endpoint Flows](#complete-endpoint-flows)
8. [Timetable Generation Flow](#timetable-generation-flow)
9. [Faculty Availability & Override Flow](#faculty-availability--override-flow)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Admin     │  │   Faculty   │  │   Student   │  │    Auth     │        │
│  │   Pages     │  │   Pages     │  │   Pages     │  │   Context   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTP/REST API
┌──────────────────────────────┴──────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        CONTROLLER LAYER                                │   │
│  │  - Receives HTTP requests                                            │   │
│  │  - Validates DTOs                                                    │   │
│  │  - Calls use cases                                                   │   │
│  │  - Returns HTTP responses                                            │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                             │                                               │
│  ┌──────────────────────────┴───────────────────────────────────────────┐   │
│  │                        USE CASE LAYER                                  │   │
│  │  - Business logic                                                     │   │
│  │  - Orchestration of repositories                                      │   │
│  │  - Validation rules                                                   │   │
│  │  - Domain entity operations                                          │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                             │                                               │
│  ┌──────────────────────────┴───────────────────────────────────────────┐   │
│  │                       REPOSITORY LAYER                                │   │
│  │  - Database operations (MongoDB)                                      │   │
│  │  - Entity ↔ Document conversion                                      │   │
│  │  - Queries                                                            │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
└─────────────────────────────┼──────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴──────────────────────────────────────────────┐
│                         MONGODB DATABASE                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐     │
│  │  users   │ │subjects  │ │timetables│ │ overrides│ │  availability│     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## User Roles & Permissions

### 1. ADMIN
**Full access to all administrative functions**

| Feature | Access Level |
|---------|--------------|
| Create/view/delete subject assignments | ✅ Full |
| Create/view/delete faculty availability overrides | ✅ Full |
| Update any faculty's availability | ✅ Full |
| Generate timetables | ✅ Full |
| View/edit/delete timetables | ✅ Full |
| View all users | ✅ Full |
| Manage subjects | ✅ Full |

### 2. FACULTY
**Self-service access to own data**

| Feature | Access Level |
|---------|--------------|
| View own assigned subjects | ✅ Own only |
| Update own availability | ✅ Own only |
| View own effective availability | ✅ Own only |
| View own schedule | ✅ Own only |
| Create overrides | ❌ No |
| Update others' availability | ❌ No |

### 3. STUDENT
**Read-only access to own data**

| Feature | Access Level |
|---------|--------------|
| View own timetable | ✅ Own only |
| View own schedule | ✅ Own only |
| Edit anything | ❌ No |

---

## Core Domain Entities

### User
```python
{
    "id": str,              # MongoDB ObjectId as string
    "full_name": str,
    "email": str,
    "password_hash": str,   # Bcrypt hashed
    "role": UserRole,        # ADMIN, FACULTY, STUDENT
    "semester": int | None, # For students
    "section": str | None,  # For students
    "is_active": bool
}
```

### Subject
```python
{
    "id": str,
    "name": str,            # e.g., "Data Structures"
    "code": str,            # e.g., "CS201"
    "credits": int,         # Typically 3-4
    "subject_type": SubjectType,  # THEORY, LAB, ELECTIVE, CORE
    "semester": int,        # Which semester this belongs to
}
```

### SubjectAssignment
```python
{
    "id": str,
    "faculty_id": str,      # Who teaches this
    "subject_id": str,      # What subject
    "semester": int,        # For which semester
    "section": str,         # Which section (A, B, etc.)
    "is_primary": bool,     # Primary instructor?
}
```

### FacultyAvailability
```python
{
    "id": str,
    "faculty_id": str,
    "subject_id": str,
    "semester": int,
    "section": str,
    "available_slots": List[AvailableSlot],  # Slots faculty is FREE
    "created_at": datetime,
    "updated_at": datetime
}

# AvailableSlot
{
    "day": DayOfWeek,       # MON, TUE, WED, THU, FRI
    "slot": int             # 1-10 (each slot = 30 mins)
}
```

### AdminOverrideLog
```python
{
    "id": str,
    "admin_id": str,        # Who created override
    "faculty_id": str,      # Whose availability
    "subject_id": str,
    "semester": int,
    "section": str,
    "override_type": OverrideType,  # PERSISTENT, ONE_TIME
    "applied": bool,        # Used in generation?
    "slots": List[OverrideSlot],
    "timestamp": datetime
}

# OverrideSlot
{
    "day": DayOfWeek,
    "slot": int,
    "action": OverrideAction  # ADD (make available), REMOVE (make unavailable)
}
```

### Timetable
```python
{
    "id": str,
    "semester": int,
    "section": str,
    "version": int,         # Incremented on changes
    "is_active": bool,      # Only one active per semester/section
    "schedule": List[DaySchedule],
    "created_by": str,
    "created_at": datetime,
    "updated_at": datetime
}

# DaySchedule
{
    "day": DayOfWeek,
    "slots": List[TimetableSlot]  # 10 slots per day
}

# TimetableSlot
{
    "slot": int,            # 1-10
    "subject_id": str | None,
    "faculty_id": str | None,
    "room": str | None
}
```

---

## Repository Layer

### Purpose
Repositories handle ALL database operations. Controllers and Use Cases NEVER access MongoDB directly.

### Key Repositories

| Repository | Collections Accessed | Main Operations |
|------------|---------------------|-----------------|
| UserRepository | users | find_by_id, find_by_email, create, update |
| SubjectRepository | subjects | find_by_id, find_all, create |
| SubjectAssignmentRepository | subject_assignments | find_all, find_faculty_assignment, save, delete |
| FacultyAvailabilityRepository | faculty_availability | find, save, update, delete, find_by_faculty |
| AdminOverrideRepository | admin_overrides | find_applicable, find_audit_log, save, delete, mark_one_time_applied |
| TimetableRepository | timetables | find_by_semester_and_section, save, delete_by_semester_and_section, get_with_subject_details |

---

## Use Case Layer

### Purpose
Use cases contain business logic. They orchestrate repositories and enforce validation rules.

### Key Use Cases

| Use Case | Purpose |
|----------|---------|
| FacultyAssignmentService | Assign subjects to faculty, get assignments |
| FacultyAvailabilityService | Update availability, compute effective availability (base + overrides) |
| AdminOverrideService | Create/delete overrides, get audit log |
| TimetableUseCase | Generate timetables, view timetables, update slots |
| TimetableGenerator | Algorithm to auto-schedule classes |

---

## Controller Layer

### Purpose
Controllers handle HTTP requests/responses. They:
1. Receive HTTP request with DTOs
2. Call use cases
3. Return HTTP responses with DTOs
4. Handle HTTP status codes and exceptions

### Controllers

| Controller | Prefix | Purpose |
|------------|--------|---------|
| auth_controller | /auth | Login, register, me endpoint |
| faculty_assignment_controller | /admin, /faculty | Assignments, availability, overrides |
| timetable_controller | /timetable | Generate, view, edit timetables |
| subject_controller | /subjects | CRUD for subjects |

---

## Complete Endpoint Flows

### Authentication Flow

```
POST /api/v1/auth/login
│
├─ Request: { "email": "...", "password": "..." }
│
├─ Controller: auth_controller.py → login()
│   │
│   ├─ 1. Validate request body
│   │
│   ├─ 2. Call UserRepository.find_by_email()
│   │   └─ Query: db.users.find_one({ "email": email })
│   │
│   ├─ 3. Verify password (bcrypt)
│   │
│   ├─ 4. Check user.is_active
│   │
│   ├─ 5. Create access token (JWT)
│   │   └─ Contains: user_id, role, exp
│   │
│   └─ 6. Return: { "access_token": "...", "user": {...} }
│
└─ Response: 200 OK with JWT token
```

---

### Subject Assignment Flow (Admin)

```
POST /api/v1/admin/subject-assignments
│
├─ Request: { "faculty_id": "...", "subject_id": "...", "semester": 1, "section": "A" }
│
├─ Controller: faculty_assignment_controller.py → assign_subject()
│   │
│   ├─ 1. get_current_admin() - Verify JWT token has ADMIN role
│   │
│   ├─ 2. Convert DTO to ServiceRequest
│   │
│   ├─ 3. Call FacultyAssignmentService.assign_subject()
│   │   │
│   │   ├─ 3a. Validate user exists and is FACULTY
│   │   │   └─ UserRepository.find_by_id(faculty_id)
│   │   │
│   │   ├─ 3b. Validate subject exists
│   │   │   └─ SubjectRepository.find_by_id(subject_id)
│   │   │
│   │   ├─ 3c. Check assignment doesn't already exist
│   │   │   └─ SubjectAssignmentRepository.find_faculty_assignment()
│   │   │
│   │   ├─ 3d. Create SubjectAssignment entity
│   │   │
│   │   └─ 3e. Save via SubjectAssignmentRepository.save()
│   │       └─ db.subject_assignments.insert_one(document)
│   │
│   └─ 4. Return AssignmentResponse
│
└─ Response: 201 Created
```

---

### Faculty Availability Update Flow (Faculty)

```
POST /api/v1/faculty/availability
│
├─ Request: {
│     "subject_id": "...",
│     "semester": 1,
│     "section": "A",
│     "available_slots": [
│       { "day": "MON", "slot": 1 },
│       { "day": "MON", "slot": 2 },
│       ...
│     ]
│   }
│
├─ Controller: faculty_assignment_controller.py → update_my_availability()
│   │
│   ├─ 1. get_current_faculty() - Verify JWT token has FACULTY role
│   │
│   ├─ 2. Convert DTO to ServiceRequest
│   │
│   ├─ 3. Call FacultyAvailabilityService.update_availability()
│   │   │
│   │   ├─ 3a. Authorization: faculty can only update OWN availability
│   │   │
│   │   ├─ 3b. Validate MINIMUM 3 slots required
│   │   │
│   │   ├─ 3c. Verify faculty is assigned to this subject
│   │   │   └─ SubjectAssignmentRepository.find_faculty_assignment()
│   │   │
│   │   ├─ 3d. Convert slot dicts to AvailableSlot entities
│   │   │
│   │   ├─ 3e. Check for duplicate slots
│   │   │
│   │   ├─ 3f. Check if availability already exists
│   │   │   └─ FacultyAvailabilityRepository.find()
│   │   │
│   │   └─ 3g. Save (create new or update existing)
│   │       └─ FacultyAvailabilityRepository.save() / update()
│   │
│   └─ 4. Return AvailabilityResponse with slots
│
└─ Response: 200 OK
```

---

### Effective Availability Calculation Flow

```
GET /api/v1/admin/faculty-availability/effective?faculty_id={id}&subject_id={id}&semester={n}&section={s}
│
├─ Controller: faculty_assignment_controller.py → get_effective_availability()
│   │
│   ├─ 1. get_current_user() - Any authenticated user
│   │
│   ├─ 2. Call FacultyAvailabilityService.get_effective_availability()
│   │   │
│   │   ├─ 2a. Get BASE availability from faculty
│   │   │   └─ availability_repo.find(faculty_id, subject_id, semester, section)
│   │   │       └─ Returns: FacultyAvailability with available_slots
│   │   │       └─ base_slots = availability.available_slots or []
│   │   │
│   │   ├─ 2b. Get APPLICABLE overrides
│   │   │   └─ override_repo.find_applicable(faculty_id, subject_id, semester, section)
│   │   │       └─ Query: {
│   │   │             "faculty_id": ObjectId(faculty_id),
│   │   │             "subject_id": ObjectId(subject_id),
│   │   │             "semester": semester,
│   │   │             "section": section,
│   │   │             "$or": [
│   │   │               { "override_type": "persistent" },
│   │   │               { "override_type": "one_time", "applied": false }
│   │   │             ]
│   │   │           }
│   │   │
│   │   ├─ 2c. APPLY overrides to base slots
│   │   │   └─ _apply_overrides(base_slots, overrides)
│   │   │       │
│   │   │       ├─ Start with base_slots as Set of (day, slot) tuples
│   │   │       │
│   │   │       └─ For each override:
│   │   │           │
│   │   │           └─ For each override_slot:
│   │   │               │
│   │   │               ├─ If action == ADD:
│   │   │               │   └─ effective.add((day, slot))
│   │   │               │
│   │   │               └─ If action == REMOVE:
│   │   │                   └─ effective.discard((day, slot))
│   │   │
│   │   ├─ 2d. Dedupe and sort effective_slots
│   │   │   └─ _dedupe_and_sort(effective_slots)
│   │   │
│   │   └─ 2e. Return EffectiveAvailabilityResponse
│   │       └─ {
│   │             base_slots: [...],
│   │             effective_slots: [...],
│   │             applied_overrides: [...]
│   │           }
│   │
│   └─ 3. Split overrides by type (persistent vs one_time) for debugging
│
└─ Response: 200 OK
    {
      "base_slots": [...],           // What faculty defined
      "effective_slots": [...],       // Final result after overrides
      "persistent_overrides": [...],  // Persistent overrides
      "one_time_overrides": [...]     // One-time overrides
    }
```

---

### Admin Override Creation Flow

```
POST /api/v1/admin/overrides
│
├─ Request: {
│     "faculty_id": "...",
│     "subject_id": "...",
│     "semester": 1,
│     "section": "A",
│     "override_type": "persistent",  // or "one_time"
│     "slots": [
│       { "day": "MON", "slot": 3, "action": "add" },
│       { "day": "WED", "slot": 5, "action": "remove" }
│     ]
│   }
│
├─ Controller: faculty_assignment_controller.py → create_override()
│   │
│   ├─ 1. get_current_admin() - Verify ADMIN role
│   │
│   ├─ 2. Convert DTO to ServiceRequest
│   │
│   ├─ 3. Call AdminOverrideService.create_override()
│   │   │
│   │   ├─ 3a. Authorization check (ADMIN only)
│   │   │
│   │   ├─ 3b. Validate override_type ("persistent" or "one_time")
│   │   │
│   │   ├─ 3c. Verify faculty exists and is FACULTY
│   │   │   └─ UserRepository.find_by_id(faculty_id)
│   │   │
│   │   ├─ 3d. Verify faculty is assigned to this subject
│   │   │   └─ SubjectAssignmentRepository.find_faculty_assignment()
│   │   │
│   │   ├─ 3e. Validate each slot
│   │   │   ├─ Day must be valid (MON-FRI)
│   │   │   ├─ Slot must be 1-10
│   │   │   ├─ Action must be "add" or "remove"
│   │   │   └─ Check for duplicates
│   │   │
│   │   ├─ 3f. Create AdminOverrideLog entity
│   │   │   └─ {
│   │   │         admin_id: admin_id,
│   │   │         faculty_id: faculty_id,
│   │   │         subject_id: subject_id,
│   │   │         semester: semester,
│   │   │         section: section,
│   │   │         override_type: PERSISTENT/ONE_TIME,
│   │   │         applied: false,
│   │   │         slots: [...],
│   │   │         timestamp: now
│   │   │       }
│   │   │
│   │   └─ 3g. Save via AdminOverrideRepository.save()
│   │       └─ db.admin_overrides.insert_one(document)
│   │
│   └─ 4. Return OverrideResponse
│
└─ Response: 201 Created
```

---

## Timetable Generation Flow

### Simple Generation (Auto-detect everything)

```
POST /api/v1/timetable/generate/simple
│
├─ Request: { "semester": 1, "section": "A" }
│
├─ Controller: timetable_controller.py → generate_timetable_simple()
│   │
│   ├─ 1. get_current_admin() - Verify ADMIN role
│   │
│   ├─ 2. Call TimetableUseCase.generate_timetable_simple()
│   │   │
│   │   ├─ STEP 1: Detect assignments and availability
│   │   │   └─ detect_assignments_for_timetable(semester, section)
│   │   │       │
│   │   │       ├─ 1a. Get all subject assignments
│   │   │       │   └─ assignment_repo.find_all(semester, section)
│   │   │       │       └─ Returns: List[SubjectAssignment]
│   │   │       │
│   │   │       ├─ 1b. Extract unique subject_ids
│   │   │       │   └─ For each assignment:
│   │   │       │       ├─ Add subject_id to list
│   │   │       │       └─ Build subject_faculty_map: {subject_id: faculty_id}
│   │   │       │
│   │   │       └─ 1c. Build faculty_availability using EFFECTIVE availability
│   │   │           └─ For each assignment:
│   │   │               ├─ Call availability_service.get_effective_availability()
│   │   │               │   ├─ Gets base availability
│   │   │               │   ├─ Gets applicable overrides
│   │   │               │   ├─ Applies overrides
│   │   │               │   └─ Returns effective_slots
│   │   │               │
│   │   │               └─ Format for generator:
│   │   │                   └─ faculty_availability[faculty_id][day] = [slots]
│   │   │
│   │   ├─ STEP 2: Create GenerateTimetableRequest
│   │   │   └─ {
│   │   │         semester: semester,
│   │   │         section: section,
│   │   │         subject_ids: [...],
│   │   │         faculty_availability: {...},
│   │   │         subject_faculty_map: {...},
│   │   │         created_by: admin_id
│   │   │       }
│   │   │
│   │   └─ STEP 3: Call generate_timetable(request)
│   │       │
│   │       ├─ 3a. Fetch subjects by ID
│   │       │   └─ For each subject_id:
│   │       │       └─ subject_repo.find_by_id(subject_id)
│   │       │
│   │       ├─ 3b. Update timetable_generator with subjects
│   │       │   └─ timetable_generator.subjects = subjects
│   │       │
│   │       ├─ 3c. Validate constraints
│   │       │   └─ timetable_generator.validate_constraints()
│   │       │       ├─ Check if subjects can fit in available slots
│   │       │       └─ Return: { valid: bool, warnings: [], errors: [] }
│   │       │
│   │       ├─ 3d. Generate timetable
│   │       │   └─ timetable_generator.generate()
│   │       │       │
│   │       │       ├─ Separate LAB and THEORY subjects
│   │       │       │   ├─ lab_subjects = subjects where is_lab() = true
│   │       │       │   └─ theory_subjects = subjects where is_theory() or is_elective()
│   │       │       │
│   │       │       ├─ Schedule LAB subjects first (require consecutive slots)
│   │       │       │   └─ For each lab_subject:
│   │       │       │       ├─ Find available consecutive slots
│   │       │       │       ├─ Assign to timetable
│   │       │       │       └─ Mark slots as used
│   │       │       │
│   │       │       └─ Schedule THEORY subjects
│   │       │           └─ For each theory_subject:
│   │       │               ├─ Calculate required slots (credits * 2)
│   │       │               ├─ Distribute across week
│   │       │               ├─ Assign to available slots
│   │       │               └─ Mark slots as used
│   │       │
│   │       ├─ 3e. Create Timetable entity
│   │       │   └─ Timetable(
│   │       │         semester: semester,
│   │       │         section: section,
│   │       │         version: 1,
│   │       │         is_active: true,
│   │       │         schedule: generated_schedule,
│   │       │         created_by: admin_id
│   │       │       )
│   │       │
│   │       └─ 3f. Save timetable
│   │           └─ timetable_repo.save()
│   │               ├─ Deactivate existing timetables for this semester/section
│   │               │   └─ db.timetables.update_many(
│   │               │         { semester, section, is_active: true },
│   │               │         { $set: { is_active: false } }
│   │               │       )
│   │               ├─ Get next version number
│   │               │   └─ max_version + 1
│   │               └─ Insert new timetable
│   │
│   └─ 3. Return response
│
└─ Response: 200 OK
    {
      "message": "Timetable generated successfully",
      "timetable": { "id": "...", "semester": 1, "section": "A", "version": 1 },
      "warnings": []
    }
```

---

### View Timetable Flow

```
GET /api/v1/timetable?semester=1&section=A
│
├─ Controller: timetable_controller.py → view_timetable()
│   │
│   ├─ 1. get_current_user() - Any authenticated user
│   │
│   ├─ 2. Call TimetableUseCase.view_timetable()
│   │   │
│   │   └─ timetable_repo.get_with_subject_details(semester, section)
│   │       │
│   │       ├─ 2a. Find active timetable
│   │       │   └─ db.timetables.find_one({
│   │       │         semester: semester,
│   │       │         section: section,
│   │       │         is_active: true
│   │       │       })
│   │       │
│   │       ├─ 2b. If not found, return null
│   │       │
│   │       ├─ 2c. Extract all unique subject_ids and faculty_ids from schedule
│   │       │   └─ For each day in schedule:
│   │       │       └─ For each slot in day.slots:
│   │       │           ├─ Add slot.subject_id to subject_ids list
│   │       │           └─ Add slot.faculty_id to faculty_ids list
│   │       │
│   │       ├─ 2d. Fetch subjects in batch
│   │       │   └─ db.subjects.find({
│   │       │         "_id": { $in: [ObjectId(subject_id) for subject_id in subject_ids] }
│   │       │       })
│   │       │   └─ Create subjects_map: { subject_id: { code, name } }
│   │       │
│   │       ├─ 2e. Fetch faculty in batch
│   │       │   └─ db.users.find({
│   │       │         "_id": { $in: [ObjectId(faculty_id) for faculty_id in faculty_ids] }
│   │       │       })
│   │       │   └─ Create faculty_map: { faculty_id: { full_name } }
│   │       │
│   │       └─ 2f. Enrich schedule with details
│   │           └─ For each day in schedule:
│   │               └─ For each slot in day.slots:
│   │                   ├─ slot.subject = subjects_map.get(slot.subject_id)
│   │                   └─ slot.faculty = faculty_map.get(slot.faculty_id)
│   │
│   └─ 3. Return enriched timetable
│
└─ Response: 200 OK
    {
      "id": "...",
      "semester": 1,
      "section": "A",
      "version": 1,
      "schedule": [
        {
          "day": "MON",
          "slots": [
            {
              "slot": 1,
              "subject_id": "...",
              "subject": { "code": "CS201", "name": "Data Structures" },
              "faculty_id": "...",
              "faculty": { "full_name": "Dr. Smith" },
              "room": "101"
            },
            ...
          ]
        },
        ...
      ]
    }
```

---

## Faculty Availability & Override Flow - Complete Example

### Scenario: Faculty marks availability, Admin creates override, Timetable uses effective availability

``┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Faculty sets base availability                                     │
└─────────────────────────────────────────────────────────────────────────────┘

POST /api/v1/faculty/availability
Request:
{
  "subject_id": "sub123",
  "semester": 1,
  "section": "A",
  "available_slots": [
    { "day": "MON", "slot": 1 },
    { "day": "MON", "slot": 2 },
    { "day": "MON", "slot": 3 },
    { "day": "TUE", "slot": 1 },
    { "day": "TUE", "slot": 2 },
    { "day": "WED", "slot": 1 },
    { "day": "WED", "slot": 2 },
    { "day": "THU", "slot": 1 },
    { "day": "THU", "slot": 2 },
    { "day": "FRI", "slot": 1 }
  ]
}

Database (faculty_availability collection):
{
  "_id": ObjectId("..."),
  "faculty_id": ObjectId("fac123"),
  "subject_id": ObjectId("sub123"),
  "semester": 1,
  "section": "A",
  "available_slots": [
    { "day": "MON", "slot": 1 },
    { "day": "MON", "slot": 2 },
    { "day": "MON", "slot": 3 },
    { "day": "TUE", "slot": 1 },
    { "day": "TUE", "slot": 2 },
    { "day": "WED", "slot": 1 },
    { "day": "WED", "slot": 2 },
    { "day": "THU", "slot": 1 },
    { "day": "THU", "slot": 2 },
    { "day": "FRI", "slot": 1 }
  ],
  "created_at": ISODate("2025-01-15T10:00:00Z"),
  "updated_at": ISODate("2025-01-15T10:00:00Z")
}

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Admin creates override (remove MON slot 3, add FRI slot 2)          │
└─────────────────────────────────────────────────────────────────────────────┘

POST /api/v1/admin/overrides
Request:
{
  "faculty_id": "fac123",
  "subject_id": "sub123",
  "semester": 1,
  "section": "A",
  "override_type": "persistent",
  "slots": [
    { "day": "MON", "slot": 3, "action": "remove" },  // Remove from availability
    { "day": "FRI", "slot": 2, "action": "add" }      // Add to availability
  ]
}

Database (admin_overrides collection):
{
  "_id": ObjectId("ovr123"),
  "admin_id": ObjectId("admin456"),
  "faculty_id": ObjectId("fac123"),
  "subject_id": ObjectId("sub123"),
  "semester": 1,
  "section": "A",
  "override_type": "persistent",
  "applied": false,
  "slots": [
    { "day": "MON", "slot": 3, "action": "remove" },
    { "day": "FRI", "slot": 2, "action": "add" }
  ],
  "timestamp": ISODate("2025-01-15T11:00:00Z")
}

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Get effective availability (base + overrides applied)              │
└─────────────────────────────────────────────────────────────────────────────┘

GET /api/v1/admin/faculty-availability/effective?faculty_id=fac123&subject_id=sub123&semester=1&section=A

Processing:
│
├─ Get base availability:
│   └─ [MON:1, MON:2, MON:3, TUE:1, TUE:2, WED:1, WED:2, THU:1, THU:2, FRI:1]
│
├─ Get applicable overrides:
│   └─ [{ day: MON, slot: 3, action: remove }, { day: FRI, slot: 2, action: add }]
│
├─ Apply overrides:
│   ├─ Start: [MON:1, MON:2, MON:3, TUE:1, TUE:2, WED:1, WED:2, THU:1, THU:2, FRI:1]
│   │
│   ├─ Apply MON:3 remove:
│   │   └─ [MON:1, MON:2, TUE:1, TUE:2, WED:1, WED:2, THU:1, THU:2, FRI:1]
│   │
│   └─ Apply FRI:2 add:
│       └─ [MON:1, MON:2, TUE:1, TUE:2, WED:1, WED:2, THU:1, THU:2, FRI:1, FRI:2]
│
└─ Response:
    {
      "base_slots": [
        { "day": "MON", "slot": 1 },
        { "day": "MON", "slot": 2 },
        { "day": "MON", "slot": 3 },
        { "day": "TUE", "slot": 1 },
        { "day": "TUE", "slot": 2 },
        { "day": "WED", "slot": 1 },
        { "day": "WED", "slot": 2 },
        { "day": "THU", "slot": 1 },
        { "day": "THU", "slot": 2 },
        { "day": "FRI", "slot": 1 }
      ],
      "effective_slots": [
        { "day": "MON", "slot": 1 },
        { "day": "MON", "slot": 2 },
        // MON:3 removed by override
        { "day": "TUE", "slot": 1 },
        { "day": "TUE", "slot": 2 },
        { "day": "WED", "slot": 1 },
        { "day": "WED", "slot": 2 },
        { "day": "THU", "slot": 1 },
        { "day": "THU", "slot": 2 },
        { "day": "FRI", "slot": 1 },
        { "day": "FRI", "slot": 2 }  // Added by override
      ],
      "persistent_overrides": [
        {
          "id": "ovr123",
          "override_type": "persistent",
          "slots": [
            { "day": "MON", "slot": 3, "action": "remove" },
            { "day": "FRI", "slot": 2, "action": "add" }
          ],
          "admin_id": "admin456",
          "timestamp": "2025-01-15T11:00:00Z",
          "applied": false
        }
      ],
      "one_time_overrides": []
    }

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Timetable generation uses effective availability                    │
└─────────────────────────────────────────────────────────────────────────────┘

POST /api/v1/timetable/generate/simple
Request: { "semester": 1, "section": "A" }

Processing (detect_assignments_for_timetable):
│
├─ For each assignment:
│   ├─ faculty_id = fac123, subject_id = sub123
│   │
│   ├─ Get effective availability:
│   │   └─ availability_service.get_effective_availability()
│   │       └─ Returns effective_slots: [MON:1, MON:2, TUE:1, TUE:2, WED:1, WED:2, THU:1, THU:2, FRI:1, FRI:2]
│   │
│   └─ Format for generator:
│       └─ faculty_availability[fac123] = {
│             "MON": [1, 2],      // NOT 3 (removed by override)
│             "TUE": [1, 2],
│             "WED": [1, 2],
│             "THU": [1, 2],
│             "FRI": [1, 2]       // Including 2 (added by override)
│           }
│
└─ Generator schedules classes using EFFECTIVE availability only

Result: Timetable reflects overrides (MON slot 3 is free, FRI slot 2 can be used)
```

---

## Key Design Principles

### 1. Hexagonal Architecture
- Domain entities don't depend on infrastructure
- Repositories abstract database access
- Use cases contain business logic
- Controllers handle HTTP only

### 2. Single Responsibility
- Repository: Database operations only
- Use Case: Business logic only
- Controller: HTTP handling only
- Entity: Data structure + validation only

### 3. Dependency Injection
- All dependencies injected via FastAPI Depends()
- Enables testing and flexibility

### 4. Effective Availability Pattern
- Base availability = What faculty defines
- Overrides = Admin modifications
- Effective = Base + Overrides applied
- Used by: Timetable generator, schedule views

---

## Database Collections Summary

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| users | Authentication, role management | email, password_hash, role, semester, section |
| subjects | Course catalog | code, name, credits, subject_type, semester |
| subject_assignments | Faculty → Subject mapping | faculty_id, subject_id, semester, section |
| faculty_availability | Faculty available time slots | faculty_id, subject_id, available_slots |
| admin_overrides | Admin modifications to availability | admin_id, faculty_id, override_type, slots, applied |
| timetables | Generated class schedules | semester, section, version, is_active, schedule |

---

## Common Workflows by Role

### ADMIN Workflow
```
1. Login → Get JWT token
2. Assign subjects to faculty
   POST /admin/subject-assignments
3. (Optional) Override faculty availability
   POST /admin/overrides
4. Generate timetable
   POST /timetable/generate/simple
5. View timetable
   GET /timetable?semester=1&section=A
6. (Optional) Edit specific slots
   PUT /timetable/slots/{timetable_id}
```

### FACULTY Workflow
```
1. Login → Get JWT token
2. View assigned subjects
   GET /faculty/assignments/my-subjects
3. Set availability for each subject
   POST /faculty/availability
4. View effective availability (with admin overrides)
   GET /faculty/availability/effective
5. View own schedule
   GET /timetable/faculty/{faculty_id}
```

### STUDENT Workflow
```
1. Login → Get JWT token
2. View own timetable
   GET /timetable/my
   - Uses semester and section from user profile
```

---

## Error Handling Flow

All endpoints follow this pattern:

```python
try:
    # 1. Validate request
    # 2. Call use case
    # 3. Return response
except AuthorizationError as e:
    raise HTTPException(status_code=403, detail=str(e))
except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except ResourceNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    # Log error
    raise HTTPException(status_code=500, detail=str(e))
```

---

## Time Slots System

### Slot Definition
- Day: MON, TUE, WED, THU, FRI (No SAT/SUN)
- Slots: 1-10 per day
- Each slot = 30 minutes
- Working hours: 9:00 AM - 2:00 PM

### Slot Times
| Slot | Time |
|------|------|
| 1 | 9:00 - 9:30 |
| 2 | 9:30 - 10:00 |
| 3 | 10:00 - 10:30 |
| 4 | 10:30 - 11:00 |
| 5 | 11:00 - 11:30 |
| 6 | 11:30 - 12:00 |
| 7 | 12:00 - 12:30 |
| 8 | 12:30 - 1:00 |
| 9 | 1:00 - 1:30 |
| 10 | 1:30 - 2:00 |

### Credit System
- Theory subject: credits × 2 slots per week
- Lab subject: credits × 2 consecutive slots per session
- Example: 3-credit theory = 6 slots/week, 3-credit lab = 6 consecutive slots

---

## File Structure Reference

```
academic_system/
├── app/
│   ├── domain/
│   │   ├── entities/           # Domain entities (User, Subject, Timetable, etc.)
│   │   ├── exceptions/         # Custom exceptions
│   │   └── interfaces/         # Repository interfaces
│   ├── adapters/
│   │   ├── repositories/       # MongoDB implementations
│   │   ├── services/           # TimetableGenerator
│   │   └── controllers/        # FastAPI route handlers
│   │       └── dto/            # Request/Response models
│   ├── use_cases/              # Business logic
│   ├── infrastructure/         # Dependencies, auth, database
│   └── main.py                 # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── pages/              # React page components
│       ├── components/         # Reusable components
│       └── context/            # Auth context
└── docs/                       # Documentation
```

---

## Summary

This document provides a complete reference for:
1. How the system is architected
2. What each role can do
3. How each endpoint processes requests
4. How data flows through the system
5. How effective availability is calculated and used
6. How timetables are generated

For debugging, use the effective availability endpoint to verify overrides are being applied correctly before generating timetables.
