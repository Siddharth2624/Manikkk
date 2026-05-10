"""RequestContext - Immutable user context for service layer authorization."""

from dataclasses import dataclass
from typing import Optional

from app.domain.entities.user import UserRole, User


@dataclass(frozen=True)
class RequestContext:
    """
    Immutable context passed to service layer.
    Contains user identity and role for authorization decisions.
    """
    user_id: str
    role: UserRole
    email: str
    semester: Optional[int] = None
    section: Optional[str] = None
    employee_id: Optional[str] = None

    @classmethod
    def from_user(cls, user: User) -> "RequestContext":
        return cls(
            user_id=user.id,
            role=user.role,
            email=user.email,
            semester=user.semester,
            section=user.section,
            employee_id=user.employee_id
        )

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_faculty(self) -> bool:
        return self.role == UserRole.FACULTY

    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    def can_access_student_data(self, student_id: str) -> bool:
        if self.role in (UserRole.ADMIN, UserRole.FACULTY):
            return True
        return self.user_id == student_id
