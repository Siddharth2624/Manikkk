"""User domain entity with role-based access control."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List
from bson import ObjectId


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"


@dataclass
class User:
    """
    Core user entity - represents all users in the system.

    Attributes:
        id: Unique user identifier (MongoDB ObjectId as string)
        email: User's email address (unique)
        password_hash: Bcrypt hashed password
        full_name: User's full name
        role: User's role (admin, faculty, student)
        is_active: Whether the account is active
        semester: Student's semester (1-8), None for admin/faculty
        section: Student's section (e.g., "A", "B"), None for admin/faculty
        roll_number: Student's roll number (unique), None for admin/faculty
        employee_id: Faculty's employee ID (unique), None for admin/student
        department: Faculty's department, None for admin/student
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    email: str
    password_hash: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    semester: Optional[int] = None
    section: Optional[str] = None
    roll_number: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None

    def __post_init__(self):
        """Validate user data after initialization."""
        # Validate semester range
        if self.semester is not None and not 1 <= self.semester <= 8:
            raise ValueError("Semester must be between 1 and 8")

        # Validate section format
        if self.section is not None and len(self.section) > 2:
            raise ValueError("Section must be 1-2 characters")

    # Role check methods
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN

    def is_faculty(self) -> bool:
        """Check if user is a faculty member."""
        return self.role == UserRole.FACULTY

    def is_student(self) -> bool:
        """Check if user is a student."""
        return self.role == UserRole.STUDENT

    # Access control methods
    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role == UserRole.ADMIN

    def can_manage_timetable(self) -> bool:
        """Check if user can manage timetables."""
        return self.role == UserRole.ADMIN

    def can_mark_attendance(self) -> bool:
        """Check if user can mark attendance."""
        return self.role in (UserRole.ADMIN, UserRole.FACULTY)

    def can_upload_material(self) -> bool:
        """Check if user can upload study materials."""
        return self.role in (UserRole.ADMIN, UserRole.FACULTY)

    def can_view_attendance(self) -> bool:
        """Check if user can view attendance."""
        return self.role in (UserRole.ADMIN, UserRole.FACULTY, UserRole.STUDENT)

    def can_view_timetable(self, target_semester: Optional[int] = None) -> bool:
        """
        Check if user can view timetable.

        Args:
            target_semester: The semester being viewed (for students)
        """
        if self.role in (UserRole.ADMIN, UserRole.FACULTY):
            return True
        if self.role == UserRole.STUDENT:
            return target_semester == self.semester
        return False

    # Business logic methods
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def update_profile(self, **kwargs) -> None:
        """
        Update user profile fields.

        Args:
            **kwargs: Fields to update (full_name, department, etc.)
        """
        allowed_fields = {
            "full_name", "department", "semester", "section",
            "roll_number", "employee_id"
        }
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

    def get_display_name(self) -> str:
        """Get user's display name."""
        return self.full_name or self.email.split("@")[0]

    def get_identifier(self) -> str:
        """Get unique identifier for the user based on role."""
        if self.role == UserRole.STUDENT and self.roll_number:
            return f"{self.roll_number} (Sem-{self.semester} {self.section})"
        elif self.role == UserRole.FACULTY and self.employee_id:
            return f"{self.employee_id} ({self.department})"
        return self.email


@dataclass
class StudentProfile:
    """Student-specific profile information."""
    user_id: str
    semester: int
    section: str
    roll_number: str
    batch: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[datetime] = None


@dataclass
class FacultyProfile:
    """Faculty-specific profile information."""
    user_id: str
    employee_id: str
    department: str
    designation: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    date_of_joining: Optional[datetime] = None
