# Academic Management System

A scalable, multi-semester academic management system built with FastAPI, MongoDB, and Clean Architecture principles.

## Features

- **Multi-Semester Support**: Manage all 8 semesters of CSE branch
- **Multiple Sections**: Support for multiple sections per semester
- **Role-Based Access Control**: Admin, Faculty, and Student roles
- **JWT Authentication**: Secure token-based authentication
- **Timetable Generation**: Automated timetable generation with constraints
- **Attendance Management**: Track and report student attendance
- **Study Materials**: Faculty can upload, students can download

## Tech Stack

- **Framework**: FastAPI 0.109.0
- **Database**: MongoDB with Motor (async driver)
- **Authentication**: JWT with bcrypt password hashing
- **Architecture**: Clean Architecture with Hexagonal Ports & Adapters
- **Validation**: Pydantic v2

## Project Structure

```
academic_system/
├── app/
│   ├── domain/              # Core business entities and interfaces
│   │   ├── entities/        # Domain entities
│   │   ├── value_objects/   # Value objects
│   │   └── interfaces/      # Repository and service interfaces
│   ├── use_cases/           # Application business logic
│   ├── adapters/            # External implementations
│   │   ├── repositories/    # MongoDB repositories
│   │   ├── controllers/     # FastAPI routers
│   │   └── gateways/        # External services (email, storage)
│   └── infrastructure/      # Framework & configuration
│       ├── config.py        # Settings
│       ├── database.py      # MongoDB client
│       ├── security.py      # JWT, password hashing
│       └── dependencies.py  # Dependency injection
├── tests/                   # Test suite
├── uploads/                 # File uploads directory
└── main.py                  # Application entry point
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using poetry
poetry install
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
- MongoDB connection URL
- JWT secret key
- CORS origins
- File upload settings

## Running the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Schema

### Collections

1. **users** - User accounts with roles (admin, faculty, student)
2. **semesters** - Semester configuration and status
3. **subjects** - Subject catalog (simplified - no faculty/sections)
4. **subject_assignments** - Faculty-subject-section assignments
5. **timetables** - Single document per semester-section with embedded schedule
6. **attendances** - Attendance records
7. **study_materials** - Uploaded materials
8. **faculty_availability** - Faculty availability for subject assignments
9. **admin_override_log** - Audit log for admin availability overrides

### Schema Design Notes

**Timetable Schema**: Each timetable is a single document containing:
- `semester`, `section`, `academic_year` - Composite key
- `version` - For tracking changes
- `is_active` - Flags the currently active version
- `schedule` - Array of day schedules with embedded slots

**Subject Assignment Schema**: Separates faculty-subject relationships from subjects:
- Allows multiple faculty to teach same subject in different sections
- Tracks academic year for historical accuracy
- Supports section-level assignment granularity

**Faculty Availability Schema**: One record per faculty-subject-semester-section:
- `faculty_id`, `subject_id`, `semester`, `section`, `academic_year` - Composite unique key
- `available_slots` - Array of available time slots (day, slot number)
- Faculty must provide at least 3 available slots
- Used by timetable generator for optimal scheduling

**Admin Override Log Schema**: Audit trail for admin interventions:
- `override_type` - "persistent" (always applies) or "one_time" (applied once)
- `slots` - Array of slot overrides with action (add/remove)
- `applied` - Boolean flag for one-time overrides
- Complete audit trail with admin_id and timestamp

## Faculty Assignment and Availability System

### Overview

The faculty assignment and availability system enables administrators to assign faculty to subjects and allows faculty to specify their availability for timetable generation. Administrators can also create overrides to handle special cases.

### Key Features

1. **Subject Assignment**
   - Admins assign faculty to specific subjects for a semester/section
   - One faculty per subject per section per academic year (unique constraint)
   - Supports primary and secondary faculty assignments
   - Transaction-safe assignment with validation

2. **Faculty Availability**
   - Faculty members specify available time slots for each assigned subject
   - Minimum 3 slots required per subject
   - Slots are defined by day (MON-SAT) and slot number (1-10)
   - Availability is used by the timetable generator for optimal scheduling

3. **Admin Overrides**
   - Persistent overrides: Always apply to availability
   - One-time overrides: Applied once, then marked as used
   - Complete audit log of all override actions
   - Used by timetable generator for special cases

### API Endpoints

#### Faculty Assignment Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/faculty-assignments/assign` | Assign subject to faculty | Admin |
| GET | `/api/faculty-assignments/faculty/{faculty_id}` | Get faculty assignments | Admin/Faculty (own) |
| GET | `/api/faculty-assignments/` | Get all assignments (filtered) | Admin |
| DELETE | `/api/faculty-assignments/{assignment_id}` | Remove assignment | Admin |

#### Faculty Availability Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| PUT | `/api/faculty-availability/{faculty_id}` | Update availability | Admin/Faculty (own) |
| GET | `/api/faculty-availability/{faculty_id}/effective` | Get effective availability (with overrides) | Admin/Faculty (own) |
| GET | `/api/faculty-availability/{faculty_id}` | Get availability by subject | Admin/Faculty (own) |

#### Admin Override Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/admin/overrides` | Create availability override | Admin |
| GET | `/api/admin/overrides/audit` | Get override audit log | Admin |
| DELETE | `/api/admin/overrides/{override_id}` | Delete override | Admin |
| POST | `/api/admin/overrides/mark-applied` | Mark one-time overrides as applied | Admin |

### Constraints

1. **Unique Assignment Constraint**
   - One faculty member cannot be assigned the same subject for the same semester/section/academic_year
   - Enforced via unique index on `(faculty_id, subject_id, semester, section, academic_year)`

2. **Minimum Availability Requirement**
   - Faculty must provide at least 3 available slots per subject
   - Prevents generation of suboptimal timetables

3. **Ownership Validation**
   - Faculty can only view/update their own availability
   - Admins can manage any faculty's availability

4. **Override Validation**
   - Slot numbers must be between 1-10
   - Day must be valid (MON, TUE, WED, THU, FRI, SAT)
   - Action must be "add" or "remove"

### Database Collections

| Collection | Description |
|------------|-------------|
| `subject_assignments` | Faculty-subject assignments |
| `faculty_availability` | Faculty availability records |
| `admin_override_log` | Admin override audit trail |

## Development

```bash
# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy app/
```

## License

MIT License - Manik Bhagat
