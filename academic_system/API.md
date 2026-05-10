# API Documentation

## Academic Management System REST API

Base URL: `http://localhost:8000/api/v1`

---

## Authentication

All endpoints (except login/register) require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Authentication

#### `POST /auth/login`
Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "student",
    "semester": 1,
    "section": "A"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### `POST /auth/register`
Register a new user (admin only for creating students/faculty).

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "SecurePass123!",
  "full_name": "Jane Student",
  "role": "student",
  "semester": 1,
  "section": "A",
  "roll_number": "2024001"
}
```

**Response (200):**
```json
{
  "user": {
    "id": "507f1f77bcf86cd799439012",
    "email": "student@example.com",
    "full_name": "Jane Student",
    "role": "student"
  },
  "message": "User registered successfully"
}
```

#### `GET /auth/me`
Get current user information.

**Response (200):**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "student",
  "semester": 1,
  "section": "A",
  "roll_number": "2024001",
  "department": null
}
```

#### `POST /auth/change-password`
Change current user's password.

**Request Body:**
```json
{
  "current_password": "oldpass123",
  "new_password": "newpass456"
}
```

---

### Admin Operations

#### `GET /admin/users`
List users with filters (admin only).

**Query Parameters:**
- `role`: Filter by role (admin, faculty, student)
- `semester`: Filter by semester (1-8)
- `section`: Filter by section (A, B, etc.)
- `skip`: Pagination offset (default: 0)
- `limit`: Results per page (default: 20, max: 100)

**Response (200):**
```json
{
  "users": [
    {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "student",
      "semester": 1,
      "section": "A",
      "roll_number": "2024001",
      "department": null,
      "is_active": true
    }
  ],
  "count": 1
}
```

#### `POST /admin/users`
Create a new user (admin only).

**Request Body:**
```json
{
  "email": "faculty@example.com",
  "password": "SecurePass123!",
  "full_name": "Dr. Smith",
  "role": "faculty",
  "department": "Computer Science",
  "employee_id": "FAC001"
}
```

#### `PUT /admin/users/{user_id}`
Update user information (admin only).

#### `DELETE /admin/users/{user_id}`
Delete a user (admin only).

#### `GET /admin/stats`
Get system statistics (admin only).

**Response (200):**
```json
{
  "total_users": 150,
  "admins": 2,
  "faculty": 20,
  "students": 128
}
```

---

### Timetable

#### `POST /timetable/generate`
Generate timetable for a semester and sections (admin only).

**Request Body:**
```json
{
  "semester": 1,
  "sections": ["A", "B"],
  "academic_year": "2024-2025",
  "subject_ids": ["507f1f77bcf86cd799439020", "507f1f77bcf86cd799439021"],
  "faculty_availability": {
    "FAC001": {
      "MON": [1, 2, 3, 4, 7, 8, 9],
      "TUE": [1, 2, 3, 7, 8, 9],
      "WED": [1, 2, 3, 4, 7, 8, 9],
      "THU": [1, 2, 3, 7, 8, 9],
      "FRI": [1, 2, 3, 4, 7, 8, 9]
    }
  }
}
```

**Response (200):**
```json
{
  "message": "Timetable generated successfully",
  "timetable": {
    "id": "1_A_B_2024-2025",
    "semester": 1,
    "sections": "A,B",
    "academic_year": "2024-2025",
    "entries_count": 100
  },
  "warnings": []
}
```

#### `GET /timetable?semester=1&section=A&academic_year=2024-2025`
View timetable for a semester and section.

**Response (200):**
```json
{
  "semester": 1,
  "section": "A",
  "matrix": [
    {
      "time": "9:00-9:50",
      "slots": [
        {"type": "theory", "subject": "CS101", "faculty": "Dr. Smith", "room": "101"},
        {"type": "theory", "subject": "CS101", "faculty": "Dr. Smith", "room": "101"}
      ]
    }
  ]
}
```

#### `GET /timetable/faculty/{faculty_id}?academic_year=2024-2025`
Get schedule for a faculty member.

#### `GET /timetable/list`
List all generated timetables.

#### `DELETE /timetable/{semester}/{section}?academic_year=2024-2025`
Delete timetable (admin only).

#### `GET /timetable/slots`
Get available time slots.

**Response (200):**
```json
{
  "time_slots": [
    {"slot_number": 1, "start_time": "9:00", "end_time": "9:50", "display": "9:00 - 9:50"},
    {"slot_number": 2, "start_time": "9:50", "end_time": "10:40", "display": "9:50 - 10:40"}
  ]
}
```

---

### Attendance

#### `POST /attendance/mark`
Mark attendance for students (faculty/admin only).

**Request Body:**
```json
{
  "subject_id": "507f1f77bcf86cd799439020",
  "section": "A",
  "attendance_date": "2024-01-15",
  "attendance": [
    {"student_id": "507f1f77bcf86cd799439030", "status": "present", "remarks": null},
    {"student_id": "507f1f77bcf86cd799439031", "status": "absent", "remarks": "Sick"}
  ]
}
```

#### `GET /attendance/my-summary?subject_id={subject_id}`
Get attendance summary for current student.

**Response (200):**
```json
{
  "student": {
    "id": "507f1f77bcf86cd799439030",
    "name": "Jane Student",
    "roll_number": "2024001",
    "semester": 1,
    "section": "A"
  },
  "summaries": [
    {
      "subject_id": "507f1f77bcf86cd799439020",
      "total_classes": 20,
      "present": 18,
      "absent": 2,
      "excused": 0,
      "percentage": 90.0,
      "is_below_threshold": false
    }
  ]
}
```

#### `GET /attendance/report/{subject_id}?section=A&start_date=2024-01-01&end_date=2024-01-31`
Get attendance report for a subject (faculty/admin only).

#### `GET /attendance/daily/{subject_id}?attendance_date=2024-01-15`
Get attendance records for a subject on a specific date.

---

### Study Materials

#### `POST /materials/upload`
Upload study material (faculty/admin only).

**Request:** Multipart form data with:
- `metadata`: JSON string with material info
- `file`: File to upload

**metadata format:**
```json
{
  "title": "Lecture 1: Introduction",
  "description": "Introduction to the course",
  "subject_id": "507f1f77bcf86cd799439020",
  "semester": 1,
  "sections": ["A", "B"],
  "tags": ["lecture", "intro"],
  "is_public": true
}
```

#### `GET /materials?semester=1&section=A&subject_id={subject_id}&query=intro`
List study materials (filtered by user role).

#### `GET /materials/{material_id}`
Get study material details.

#### `GET /materials/{material_id}/download`
Download study material file.

#### `DELETE /materials/{material_id}`
Delete study material (owner faculty or admin only).

---

## Error Responses

All endpoints may return error responses:

**400 Bad Request:**
```json
{
  "detail": "Validation error message"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden:**
```json
{
  "detail": "You don't have permission to perform this action"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

---

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error
