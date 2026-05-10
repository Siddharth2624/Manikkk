# Missing Frontend Routes Implementation Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create frontend pages and services for missing backend routes - Profile page and Faculty Reports page.

**Architecture:** Extend existing React frontend with role-based pages following established patterns.

**Tech Stack:** React 19, Vite, Tailwind CSS, Lucide icons

---

## Overview

This spec implements two missing frontend features:

1. **Profile Page (`/profile`)** - User profile viewing and password change for all users
2. **Faculty Reports Page (`/faculty/reports`)** - Attendance reports for faculty's assigned subjects only

---

## Features

### 1. Profile Page

**Route:** `/profile`
**Access:** All authenticated users (student, faculty, admin)
**Service:** Extend `authService` with `changePassword()` method

#### UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Profile                                                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Profile Information (Read-Only)                   │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  Full Name:    John Doe                           │  │
│  │  Email:        john@example.com                   │  │
│  │  Role:         Student                            │  │
│  │  Department:   Computer Science                   │  │
│  │  Roll Number:  2024001        [Student only]      │  │
│  │  Semester:     3               [Student only]      │  │
│  │  Section:      A               [Student only]      │  │
│  │  Employee ID:  EMP001          [Faculty only]      │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Security Settings (Change Password)               │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  Current Password:  [________________]            │  │
│  │  New Password:      [________________]            │  │
│  │  Confirm Password:  [________________]            │  │
│  │                                                   │  │
│  │  [Change Password]                                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

#### Role-Based Display Fields

| Field | Student | Faculty | Admin |
|-------|---------|---------|-------|
| Full Name | ✅ | ✅ | ✅ |
| Email | ✅ | ✅ | ✅ |
| Role | ✅ | ✅ | ✅ |
| Department | ✅ | ✅ | ✅ |
| Roll Number | ✅ | ❌ | ❌ |
| Semester | ✅ | ❌ | ❌ |
| Section | ✅ | ❌ | ❌ |
| Employee ID | ❌ | ✅ | ❌ |

#### Password Validation Rules

- Minimum length: 8 characters
- Confirm password must match new password
- Show inline error messages for validation failures
- Disable submit button while request is in progress
- Show success message on successful change
- Show error message on failure (wrong current password, etc.)

#### Security

- After successful password change, redirect to login page for re-authentication

#### API Calls

```javascript
// Get current user info
GET /auth/me
Response: { id, email, full_name, role, semester, section, roll_number, department, employee_id }

// Change password
POST /auth/change-password
Body: { old_password, new_password }
Response: { message: "Password changed successfully" }
```

---

### 2. Faculty Reports Page

**Route:** `/faculty/reports`
**Access:** Faculty only (strict RBAC)
**Service:** Use existing `attendanceService.getReport()`

#### UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Attendance Reports                                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Select Subject: [DBMS (Sem 3 - A) ▼]                   │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │ [Summary] [Detailed]                               │  │
│  ├───────────────────────────────────────────────────┤  │
│  │                                                   │  │
│  │  Summary Tab:                                     │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Overall Attendance: 78%                     │  │  │
│  │  │ Total Students: 45                          │  │  │
│  │  │ Present: 35 | Absent: 8 | Excused: 2        │  │  │
│  │  │                                             │  │  │
│  │  │ Below Threshold (<75%):                     │  │  │
│  │  │ • John Smith (62%)                           │  │  │
│  │  │ • Jane Doe (71%)                             │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  Detailed Tab:                                    │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Search: [__________]                         │  │  │
│  │  │                                             │  │  │
│  │  │ Student           | Present | Absent | %    │  │  │
│  │  │ John Doe          |    12   |    3   | 80%  │  │  │
│  │  │ Jane Smith        |    10   |    5   | 67%  │  │  │
│  │  │ Bob Johnson       |    14   |    1   | 93%  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

#### Subject Dropdown Format

Each option displays: `Subject Name (Sem X - Y)`

Example: "DBMS (Sem 3 - A)"

When selected, extract: `subject_id`, `semester`, `section`

#### Tabs/Views

1. **Summary Tab** - Class-level overview
   - Overall attendance percentage
   - Total students count
   - Present/Absent/Excused counts
   - List of students below 75% threshold

2. **Detailed Tab** - Per-student breakdown
   - Search by name/roll number
   - Table with columns: Student Name, Present, Absent, Percentage
   - **Sorted by percentage (descending) by default**

#### UI States

1. **Loading State:** Show spinner when fetching reports
2. **Empty State (No Data):** Show message when no attendance records exist for selected subject
3. **Empty State (No Subjects):** Show message when faculty has no assigned subjects

#### Access Control

- Route guarded: Only `role === 'faculty'` can access
- Navbar menu item: Only shown if `user.role === 'faculty'`
- Data filtering: API only returns data for faculty's assigned subjects
- Redirect unauthorized users to `/dashboard`

#### API Calls

```javascript
// Get faculty's assigned subjects (already exists)
GET /faculty/assignments/my-subjects?academic_year=2024-2025
Response: { assignments: [{ id, subject_id, subject: {name, code}, semester, section, ... }] }

// Get attendance report for a subject
GET /attendance/report?subject_id={subjectId}&semester={sem}&section={sec}&academic_year=2024-2025
Response: { subject_id, subject_name, students: [{ student_id, student_name, total_classes, present, absent, excused, percentage }] }
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/pages/profile.jsx` | Profile page component |
| `frontend/src/pages/faculty/reports.jsx` | Faculty reports page component |

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/services/auth.js` | Add `changePassword()` method |
| `frontend/src/App.jsx` | Add routes for `/profile` and `/faculty/reports` |
| `frontend/src/components/layout/navbar.jsx` | Add "Profile" and "Reports" menu items |

---

## Route Definitions

```jsx
// App.jsx
<Route
  path="/profile"
  element={
    <ProtectedRoute>
      <ProfilePage />
    </ProtectedRoute>
  }
/>
<Route
  path="/faculty/reports"
  element={
    <ProtectedRoute allowedRoles={['faculty']}>
      <FacultyReportsPage />
    </ProtectedRoute>
  }
/>
```

## Navbar Menu Items

```javascript
// Add to imports: FileText from 'lucide-react'

const navItems = [
  // ... existing items
  { label: 'Reports', href: '/faculty/reports', icon: FileText, show: currentRole === 'faculty' },
  { label: 'Profile', href: '/profile', icon: User, show: true }, // All users
];
```

---

## Component Specifications

### Profile Page Component

**File:** `frontend/src/pages/profile.jsx`

**State:**
- `user`: Object - Current user info from `/auth/me`
- `loading`: Boolean - Initial data fetch state
- `formData`: Object - { currentPassword, newPassword, confirmPassword }
- `errors`: Object - Validation errors
- `success`: Boolean - Password change success
- `changing`: Boolean - Password change in progress

**Effects:**
- On mount: Fetch user info via `GET /auth/me`
- On success: Set timeout then redirect to `/login`

**Handlers:**
- `handleSubmit`: Validate and call `authService.changePassword()`
- `validate`: Check password length and match

**Conditional Rendering:**
- Show role-specific fields based on `user.role`

---

### Faculty Reports Page Component

**File:** `frontend/src/pages/faculty/reports.jsx`

**State:**
- `assignments`: Array - Faculty's subject assignments
- `selectedAssignment`: Object - Currently selected {subject_id, semester, section, subject_name}
- `reportData`: Object - Attendance report for selected subject
- `activeTab`: String - 'summary' or 'detailed'
- `searchQuery`: String - For student search
- `loading`: Boolean - Data fetch state

**Effects:**
- On mount: Fetch faculty's assignments via `facultyAssignmentService.getMySubjects()`
- On assignment change: Fetch report via `attendanceService.getReport()`

**Computed:**
- `filteredStudents`: Filter reportData.students by searchQuery
- `belowThresholdStudents`: Filter students with percentage < 75

**Handlers:**
- `handleAssignmentChange`: Update selectedAssignment and fetch report
- `handleTabChange`: Switch between summary/detailed views

---

## Service Updates

### Auth Service

**File:** `frontend/src/services/auth.js`

Add method:

```javascript
changePassword: async (data) => {
  return await api('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
```

---

## Success Criteria

1. ✅ Profile page accessible to all users
2. ✅ Role-specific fields display correctly
3. ✅ Password validation works (length, match)
4. ✅ Password change triggers re-authentication
5. ✅ Faculty reports page accessible only to faculty
6. ✅ Faculty sees only their assigned subjects
7. ✅ Subject dropdown includes semester and section info
8. ✅ Summary and detailed tabs display correctly
9. ✅ Unauthorized users redirected from reports page
10. ✅ Navbar menu items display based on role

---

## Implementation Order

1. Update `authService` with `changePassword()` method
2. Create `profile.jsx` page
3. Add `/profile` route to `App.jsx`
4. Add "Profile" menu item to navbar
5. Create `faculty/reports.jsx` page
6. Add `/faculty/reports` route to `App.jsx`
7. Add "Reports" menu item to navbar (faculty only)
8. Test role-based access control
