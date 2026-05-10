# Architecture Documentation

## System Architecture

This Academic Management System follows **Clean Architecture** principles with clear separation of concerns.

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Adapters (Routers)                       │
│                   FastAPI Controllers                        │
├─────────────────────────────────────────────────────────────┤
│                      Use Cases                               │
│                 Application Business Logic                    │
├─────────────────────────────────────────────────────────────┤
│              Domain (Entities + Interfaces)                   │
│                    Core Business Rules                       │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure                              │
│            Framework & External Services                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
academic_system/
├── app/
│   ├── domain/                    # Core layer
│   │   ├── entities/              # Business entities
│   │   │   ├── user.py
│   │   │   ├── semester.py
│   │   │   ├── subject.py              # Simplified: catalog only
│   │   │   ├── subject_assignment.py   # NEW: Faculty-subject relationships
│   │   │   ├── timetable.py            # REDESIGNED: Single-document schema
│   │   │   ├── attendance.py
│   │   │   └── study_material.py
│   │   ├── interfaces/            # Repository/Service interfaces (ports)
│   │   │   ├── repositories.py
│   │   │   ├── timetable_generator.py
│   │   │   └── file_storage.py
│   │   └── value_objects/         # Immutable value objects
│   ├── use_cases/                 # Application logic
│   │   ├── auth.py
│   │   ├── timetable.py           # Updated: Versioning support
│   │   ├── attendance.py          # Updated: Faculty authorization
│   │   └── study_material.py
│   ├── adapters/                  # External implementations
│   │   ├── repositories/          # MongoDB repositories
│   │   │   ├── user_repository.py
│   │   │   ├── subject_repository.py          # Simplified
│   │   │   ├── subject_assignment_repository.py  # NEW
│   │   │   ├── timetable_repository.py        # REDESIGNED
│   │   │   ├── attendance_repository.py
│   │   │   ├── study_material_repository.py
│   │   │   └── semester_repository.py
│   │   ├── services/              # External services
│   │   │   ├── timetable_generator.py
│   │   │   └── file_storage_service.py
│   │   └── controllers/           # FastAPI routers
│   │       ├── auth_controller.py
│   │       ├── admin_controller.py
│   │       ├── timetable_controller.py        # Updated: Versioning endpoints
│   │       ├── attendance_controller.py       # Updated: New params
│   │       └── study_material_controller.py
│   ├── migrations/                # NEW: Database migrations
│   │   ├── __init__.py
│   │   ├── migration_001_subject_assignments.py
│   │   └── migration_002_timetable_single_document.py
│   └── infrastructure/            # Framework config
│       ├── config.py
│       ├── database.py            # Updated: New indexes
│       ├── security.py
│       └── dependencies.py        # Updated: New repo factories
├── tests/                         # Test suite
├── uploads/                       # File storage
├── main.py                        # Application entry point
├── migrate.py                     # NEW: Migration CLI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Key Design Decisions

### 1. Clean Architecture
- **Dependency Rule**: Dependencies point inward
- Inner layers (domain, use_cases) don't know about outer layers (adapters, infrastructure)
- Business logic is independent of FastAPI, MongoDB, etc.

### 2. Repository Pattern
- **Port**: Interface in `domain/interfaces/repositories.py`
- **Adapter**: MongoDB implementation in `adapters/repositories/`
- Easy to swap database implementations
- Factory functions in `infrastructure/dependencies.py` for DI

### 3. Separation of Concerns (NEW)
- **Subject Catalog**: Static subject information (code, name, credits, syllabus)
- **Subject Assignments**: Dynamic faculty-subject-section relationships (yearly)
- **Timetable**: Schedule data with versioning and single-document schema

### 4. Timetable Versioning (NEW)
- One document per semester-section-academic_year
- Version field with incremental numbering
- `is_active` flag for current version
- Preserves complete history of all changes
- Supports rollback to previous versions

### 5. Faculty Authorization (NEW)
- Attendance marking requires valid subject_assignment
- Checked at use case layer before allowing operations
- Prevents unauthorized faculty from marking attendance

### 6. Use Cases
- Orchestrate business logic
- Stay framework-agnostic
- Return domain entities, not database models
- Include authorization checks for sensitive operations

---

## Data Flow

### Authentication Flow

```
1. POST /auth/login
   ↓
2. auth_controller.login()
   ↓
3. AuthenticationUseCase.login()
   ├─ UserRepository.find_by_email()
   ├─ verify_password()
   └─ create_access_token()
   ↓
4. Return JWT to client
```

### Timetable Generation Flow (UPDATED)

```
1. POST /timetable/generate
   ↓
2. timetable_controller.generate_timetable()
   ↓
3. TimetableUseCase.generate_timetable()
   ├─ SubjectRepository.find_all()
   ├─ TimetableGenerator.validate_constraints()
   ├─ TimetableGenerator.generate()
   │   ├─ _assign_labs()
   │   ├─ _assign_theory()
   │   └─ _assign_lunch_breaks()
   └─ TimetableRepository.save()
       ├─ deactivate_active()  # Deactivate old versions
       ├─ increment version    # Get next version number
       └─ insert new document  # Create new version
   ↓
4. Return generated timetable with version
```

### Attendance Marking Flow (UPDATED)

```
1. POST /attendance/mark
   ↓
2. attendance_controller.mark_attendance()
   ↓
3. AttendanceUseCase.mark_attendance()
   ├─ SubjectRepository.find_by_id()  # Verify subject exists
   ├─ SubjectAssignmentRepository.find_faculty_assignment()
   │   └── Verify faculty is assigned to this subject/semester/section/year
   ├─ [Authorization check - raise ValueError if not authorized]
   ├─ Create AttendanceRecord entities
   └─ AttendanceRepository.save_batch()
   ↓
4. Return attendance confirmation
```

---

## Database Strategy

### Schema Redesign Principles

1. **Separation of Catalog vs Assignment Data**
   - Subjects: Static catalog information
   - Subject Assignments: Dynamic yearly assignments
   - Enables flexibility in faculty-subject mapping

2. **Single-Document Timetable Schema**
   - Before: One document per (semester, section, day, slot)
   - After: One document per (semester, section, academic_year)
   - Embedded schedule array with all days and slots
   - Reduces query complexity and improves read performance

3. **Versioning Support**
   - Multiple versions per timetable can coexist
   - `is_active` flag identifies current version
   - Supports audit trail and rollback capabilities

4. **Denormalization Removal**
   - Removed denormalized `subject_name`, `faculty_name` from timetables
   - Use $lookup aggregation when needed for display
   - Single source of truth for all data

### Index Strategy

```python
# User queries
("role", "semester")
("role", "semester", "section")
"employee_id" (unique, sparse)

# Subject catalog
"code" (unique)
"semester"
("semester", "subject_type")

# Subject assignments (NEW)
("faculty_id", "subject_id", "semester", "section", "academic_year") unique
("semester", "section", "academic_year")
("faculty_id", "academic_year")
("subject_id", "academic_year")

# Timetables (REDESIGNED)
("semester", "section", "academic_year", "is_active")
("semester", "section", "academic_year", "version")
"is_active"
"schedule.slots.faculty_id"
"schedule.slots.room"

# Attendance
("student_id", "subject_id", "date") unique
("subject_id", "date")
("student_id", "date")
```

---

## Migration System (NEW)

### Running Migrations

```bash
# Check migration status
python migrate.py status

# Run pending migrations
python migrate.py up

# Initialize database indexes
python migrate.py init-indexes
```

### Migration Files

Located in `app/migrations/`:
- `migration_001_subject_assignments.py` - Creates subject_assignments collection
- `migration_002_timetable_single_document.py` - Converts timetable schema

---

## Security

### Authentication
- JWT tokens with 30-minute expiration
- Refresh tokens for extended sessions
- Bcrypt password hashing

### Authorization
- Role-based access control (RBAC)
- Route-level protection via `Depends()`
- **NEW**: Faculty-subject authorization for attendance marking
- **NEW**: Assignment-based access control

### Faculty Authorization Rules

Faculty can only mark attendance if they have a valid subject_assignment for:
- The specific subject
- The specific semester
- The specific section
- The current academic year

This check is performed at the use case layer before any database operations.

---

## Testing Strategy

### Unit Tests
- Test use cases with mocked repositories
- Test domain entities business logic
- Test timetable generation algorithm
- **NEW**: Test faculty authorization logic

### Integration Tests
- Test full request/response cycle
- Test database operations with test database
- Test authentication flow
- **NEW**: Test migration scripts

---

## Extension Points

### Adding New Features
1. Define domain entity in `domain/entities/`
2. Create repository interface in `domain/interfaces/`
3. Implement repository in `adapters/repositories/`
4. Create use case in `use_cases/`
5. Create controller in `adapters/controllers/`
6. Add dependency factory in `infrastructure/dependencies.py`

### Adding New Migrations
1. Create `migration_XXX_name.py` in `app/migrations/`
2. Implement `migration_XXX_name(db)` function
3. Add to MIGRATIONS list in `app/migrations/__init__.py`
4. Test with `python migrate.py up`

### Adding New Roles
1. Add enum value to `UserRole`
2. Update permission checks in `User` entity
3. Add role-specific dependencies in `infrastructure/dependencies.py`

---

## API Changes (Schema Refactor)

### Attendance Endpoints

**Before:**
```http
POST /attendance/mark
{
  "subject_id": "...",
  "section": "A",
  "attendance_date": "2024-01-15",
  "attendance": [...]
}
```

**After:**
```http
POST /attendance/mark
{
  "subject_id": "...",
  "semester": 3,
  "section": "A",
  "academic_year": "2024-2025",
  "attendance_date": "2024-01-15",
  "attendance": [...]
}
```

### Timetable Endpoints (NEW)

```http
# List all versions
GET /timetable/versions/{semester}/{section}?academic_year=2024-2025

# Activate specific version
POST /timetable/versions/activate/{timetable_id}

# Create new version
POST /timetable/versions/create

# Update single slot
PUT /timetable/slots/{timetable_id}

# Check conflicts
GET /timetable/conflicts?semester=3&section=A&day=MON&slot=1
GET /timetable/conflicts/faculty/{faculty_id}?day=MON&slot=1
GET /timetable/conflicts/room/{room}?day=MON&slot=1
```
