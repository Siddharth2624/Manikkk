# Database Schema Design

## MongoDB Collections

### 1. users
Stores user accounts with role-based access.

**Indexes:**
- `email` (unique)
- `roll_number` (unique, sparse) - for students
- `employee_id` (unique, sparse) - for faculty
- `role` - for filtering by role
- `("role", "semester")` - compound index for student queries
- `("role", "semester", "section")` - for student section queries

**Schema:**
```javascript
{
  "_id": ObjectId,
  "email": string (unique, required),
  "password_hash": string (required),
  "full_name": string (required),
  "role": enum("admin", "faculty", "student") (required),
  "is_active": boolean (default: true),
  "semester": number (1-8, optional),
  "section": string (optional),
  "roll_number": string (optional, unique for students),
  "employee_id": string (optional, unique for faculty),
  "department": string (optional, for faculty),
  "created_at": datetime,
  "updated_at": datetime
}
```

---

### 2. semesters
Stores semester configuration.

**Indexes:**
- `("semester_number", "academic_year")` (unique)
- `status` - for filtering active semester
- `branch` - for filtering by branch

**Schema:**
```javascript
{
  "_id": ObjectId,
  "semester_number": number (1-8, required),
  "academic_year": string (e.g., "2024-2025"),
  "branch": string (e.g., "CSE"),
  "status": enum("upcoming", "ongoing", "completed"),
  "start_date": datetime,
  "end_date": datetime,
  "sections": [string], // e.g., ["A", "B", "C"]
  "created_at": datetime,
  "updated_at": datetime
}
```

---

### 3. subjects
Stores subject/course catalog information.

**Design Change:** This collection now stores ONLY catalog data. Faculty assignments
and section associations are moved to the `subject_assignments` collection.

**Indexes:**
- `code` (unique)
- `semester` - for catalog organization
- `subject_type` - for filtering by type
- `("semester", "subject_type")` - compound for filtered catalog queries

**Schema:**
```javascript
{
  "_id": ObjectId,
  "code": string (e.g., "CS101", unique, required),
  "name": string (required),
  "semester": number (1-8, required), // For catalog organization only
  "subject_type": enum("theory", "lab", "elective", "core"),
  "credits": number (1-6),
  "classes_per_week": number (1-10),
  "description": string,
  "syllabus": string,
  "created_at": datetime,
  "updated_at": datetime
}
```

**Removed fields (moved to subject_assignments):**
- ~~`sections`~~ - now in subject_assignments
- ~~`faculty_id`~~ - now in subject_assignments

---

### 4. subject_assignments (NEW)
Stores faculty-to-subject assignments for specific semester-section combinations.

**Purpose:** Enables flexible assignment management where:
- A faculty can teach the same subject to multiple sections
- A subject can be taught by different faculty to different sections
- Assignments change yearly without modifying subject catalog

**Indexes:**
- `("faculty_id", "subject_id", "semester", "section")` (unique) - prevents duplicate assignments
- `("semester", "section", "academic_year")` - for finding all assignments for a class
- `("faculty_id", "academic_year")` - for faculty workload queries
- `("subject_id", "academic_year")` - for subject distribution analysis

**Schema:**
```javascript
{
  "_id": ObjectId,
  "subject_id": ObjectId (ref: subjects),
  "faculty_id": ObjectId (ref: users),
  "semester": number (1-8, required),
  "section": string (required),
  "academic_year": string (e.g., "2024-2025"),
  "is_primary": boolean (default: true),
  "created_at": datetime
}
```

**Authorization Usage:**
When marking attendance, the system verifies that the faculty has a valid
assignment in subject_assignments for the given semester, section, and academic year.

---

### 5. timetables (REDESIGNED)
Stores complete timetables with single-document-per-class schema and versioning.

**Design Change:** Changed from per-entry documents to single document per
semester-section-academic_year with embedded schedule array and versioning.

**Indexes:**
- `("semester", "section", "academic_year", "is_active")` - for active timetable lookup
- `("semester", "section", "academic_year", "version")` - for version queries
- `is_active` - for filtering active timetables
- `schedule.slots.faculty_id` - for faculty schedule aggregation
- `schedule.slots.room` - for room conflict detection

**Schema:**
```javascript
{
  "_id": ObjectId,
  "semester": number (1-8, required),
  "section": string (required),
  "academic_year": string (e.g., "2024-2025"),
  "version": number (>=1, required),
  "is_active": boolean (default: true),
  "schedule": [
    {
      "day": enum("MON", "TUE", "WED", "THU", "FRI", "SAT"),
      "slots": [
        {
          "slot": number (1-10),
          "subject_id": ObjectId (ref: subjects, optional),
          "faculty_id": ObjectId (ref: users, optional),
          "room": string (optional)
        }
      ]
    }
  ],
  "created_by": ObjectId (ref: users),
  "created_at": datetime,
  "updated_at": datetime
}
```

**Versioning:**
- Each new version increments the `version` field
- Only one version per semester-section-academic_year has `is_active: true`
- When creating a new version, the old version is deactivated (`is_active: false`)
- Preserves complete history of all timetable changes

**Removed Denormalized Fields:**
- ~~`subject_name`~~ - fetch via aggregation with subjects collection
- ~~`faculty_name`~~ - fetch via aggregation with users collection
- ~~`slot_type`~~ - derived from subject_type or slot context

---

### 6. attendances
Stores attendance records.

**Indexes:**
- `("student_id", "subject_id", "date")` (unique) - one record per student/subject/day
- `("subject_id", "date")` - for daily attendance
- `faculty_id` - for faculty's marked attendance
- `("student_id", "date")` - for student daily attendance

**Schema:**
```javascript
{
  "_id": ObjectId,
  "student_id": ObjectId (ref: users),
  "subject_id": ObjectId (ref: subjects),
  "faculty_id": ObjectId (ref: users),
  "date": date,
  "status": enum("present", "absent", "excused"),
  "remarks": string,
  "marked_at": datetime,
  "updated_at": datetime
}
```

**Authorization Requirement:**
Faculty can only mark attendance if they have a valid subject_assignment
for the subject, semester, section, and academic year.

---

### 7. study_materials
Stores uploaded study materials.

**Indexes:**
- `("subject_id", "semester")` - for materials by subject
- `faculty_id` - for faculty's uploads
- `("semester", "section")` - for student access
- `upload_date` - for sorting by recent
- `title` - for text search

**Schema:**
```javascript
{
  "_id": ObjectId,
  "title": string,
  "description": string,
  "subject_id": ObjectId (ref: subjects),
  "semester": number (1-8),
  "sections": [string], // empty = all sections
  "faculty_id": ObjectId (ref: users),
  "material_type": enum("pdf", "document", "presentation", "video", "archive", "other"),
  "file_url": string,
  "file_name": string,
  "file_size": number (bytes),
  "upload_date": date,
  "download_count": number,
  "tags": [string],
  "is_public": boolean,
  "created_at": datetime,
  "updated_at": datetime
}
```

---

### 8. migrations (NEW)
Tracks applied database migrations.

**Schema:**
```javascript
{
  "_id": ObjectId,
  "name": string (unique, e.g., "001_subject_assignments"),
  "applied_at": datetime,
  "details": object // Migration-specific details
}
```

---

## Relationships

```
users (faculty) ──< (N) subject_assignments ──> subjects
                          │
                          ├── semester: 1-8
                          ├── section: "A", "B", etc.
                          └── academic_year: "2024-2025"

users (student) ──< (N) attendances ──> subjects
     │                                      │
     └── semester, section                  └── catalog data

subjects (catalog) ──< (N) timetables
                            │
                            ├── ONE document per semester-section-year
                            ├── version: 1, 2, 3... (with is_active flag)
                            └── schedule: [{day, slots: [{slot, subject_id, faculty_id, room}]}]

users (faculty) ──< (N) timetables (via schedule.slots.faculty_id)
users (faculty) ──< (N) attendances
users (faculty) ──< (N) study_materials

subjects ──< (N) study_materials
subjects ──< (N) attendances
```

---

## Data Validation Rules

### Users
- Email must be valid and unique
- Password must be hashed (bcrypt)
- Students must have semester (1-8) and section
- Students must have unique roll_number
- Faculty must have department
- Faculty must have unique employee_id

### Subjects
- Semester must be between 1-8 (catalog organization only)
- Credits must be between 1-6
- Classes per week must be between 1-10
- Code must be unique
- No faculty_id or sections (moved to subject_assignments)

### Subject Assignments
- Unique combination of (faculty_id, subject_id, semester, section, academic_year)
- Semester must be between 1-8
- Section must be 1-2 characters
- Faculty must exist and have role="faculty"
- Subject must exist

### Timetables
- Semester must be between 1-8
- Section must be 1-2 characters
- Version must be >= 1
- Only one document per semester-section-academic_year can have is_active=true
- Schedule slots 1-10 for each day
- No duplicate slot numbers within a day

### Attendance
- Unique combination of (student_id, subject_id, date)
- Faculty must have valid subject_assignment for marking attendance
- Status must be present/absent/excused
- Date cannot be in future

### Study Materials
- Semester must be between 1-8
- File size <= 10MB
- File extension must be allowed
- Faculty can only modify their own uploads

---

## Migration Guide

When migrating from the old schema:

1. **Run migrations in order:**
   ```bash
   python migrate.py status   # Check status
   python migrate.py up       # Run pending migrations
   python migrate.py init-indexes  # Create indexes
   ```

2. **Migration 001:** Creates `subject_assignments` collection
   - Extracts data from subjects.sections and subjects.faculty_id
   - Creates assignment records for each faculty-subject-section combination
   - Original subjects data is NOT modified yet

3. **Migration 002:** Converts timetable to single-document schema
   - Groups per-entry documents by semester-section-academic_year
   - Creates backup as `timetables_backup`
   - Builds new schedule structure
   - Drops old per-entry documents
   - Creates new indexes

4. **Post-migration:**
   - Verify data integrity
   - Update application code to use new schema
   - Remove old denormalized fields from subjects (optional)
   - Monitor performance with new indexes
