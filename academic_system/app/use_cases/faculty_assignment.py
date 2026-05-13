"""Faculty assignment service for managing subject-faculty assignments."""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClientSession

from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.entities.subject import Subject, SubjectType
from app.domain.entities.user import User, UserRole
from app.domain.exceptions import ValidationError, ResourceNotFoundError, AuthorizationError
from app.domain.interfaces.repositories import ISubjectAssignmentRepository, ISubjectRepository, IUserRepository


@dataclass
class AssignSubjectRequest:
    """Request to assign a subject to a faculty member."""
    subject_id: str
    faculty_id: str
    semester: int
    section: str
    is_primary: bool = True


@dataclass
class AssignSubjectResponse:
    """Response after assigning a subject."""
    assignment: SubjectAssignment
    message: str = "Subject assigned successfully"


class FacultyAssignmentService:
    """Service for managing faculty-subject assignments."""

    def __init__(
        self,
        assignment_repo: ISubjectAssignmentRepository,
        subject_repo: ISubjectRepository,
        user_repo: IUserRepository,
        db: AsyncIOMotorDatabase
    ):
        self.assignment_repo = assignment_repo
        self.subject_repo = subject_repo
        self.user_repo = user_repo
        self.db = db

    def _subject_assignment_kind(self, subject: Subject) -> str:
        """Group subject types by assignment limit category."""
        return "lab" if subject.subject_type == SubjectType.LAB else "theory"

    async def assign_subject(
        self,
        request: AssignSubjectRequest,
        current_user: User
    ) -> AssignSubjectResponse:
        """
        Assign a subject to a faculty member with transaction-safe validation.

        Args:
            request: Assignment details
            current_user: User making the request (must be admin)

        Returns:
            AssignSubjectResponse with created assignment

        Raises:
            AuthorizationError: If current_user is not admin
            ValidationError: If validation fails
            ResourceNotFoundError: If subject or faculty not found
        """
        # Authorization check
        if current_user.role != UserRole.ADMIN:
            raise AuthorizationError(
                "Only administrators can assign subjects to faculty"
            )

        # Validate subject exists
        subject = await self.subject_repo.find_by_id(request.subject_id)
        if not subject:
            raise ResourceNotFoundError("Subject", request.subject_id)

        # Validate faculty exists and is actually a faculty member
        faculty = await self.user_repo.find_by_id(request.faculty_id)
        if not faculty:
            raise ResourceNotFoundError("User", request.faculty_id)

        if faculty.role != UserRole.FACULTY:
            raise ValidationError(
                f"User {faculty.email} is not a faculty member"
            )

        # Check for duplicate assignment (same faculty, subject, semester, section)
        existing = await self.assignment_repo.find_faculty_assignment(
            faculty_id=request.faculty_id,
            subject_id=request.subject_id,
            semester=request.semester,
            section=request.section
        )

        if existing:
            raise ValidationError(
                f"Faculty is already assigned to this subject for "
                f"semester {request.semester} section {request.section}"
            )

        # CONSTRAINT: One faculty can teach one theory-type subject and one lab
        # subject per semester. The same subject can still be assigned to both
        # sections A and B.
        semester_assignments = await self.assignment_repo.find_by_faculty_and_semester(
            faculty_id=request.faculty_id,
            semester=request.semester
        )

        requested_kind = self._subject_assignment_kind(subject)

        for assignment in semester_assignments:
            if assignment.subject_id == request.subject_id:
                continue

            other_subject = await self.subject_repo.find_by_id(assignment.subject_id)
            if not other_subject:
                continue

            existing_kind = self._subject_assignment_kind(other_subject)
            if existing_kind == requested_kind:
                kind_label = "lab" if requested_kind == "lab" else "theory"
                raise ValidationError(
                    f"Faculty can teach only one {kind_label} subject per semester. "
                    f"{faculty.full_name} is already assigned to "
                    f"'{other_subject.name}' ({other_subject.code}) in semester "
                    f"{request.semester}. They can also be assigned one "
                    f"{'theory' if requested_kind == 'lab' else 'lab'} subject, "
                    f"but not another {kind_label} subject in the same semester."
                )

        # Use transaction for atomicity
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                # Create the assignment
                assignment = SubjectAssignment(
                    id=None,  # Will be generated by repository
                    subject_id=request.subject_id,
                    semester=request.semester,
                    section=request.section,
                    faculty_id=request.faculty_id,
                    is_primary=request.is_primary,
                    created_at=datetime.utcnow()
                )

                saved = await self.assignment_repo.save(assignment)

                return AssignSubjectResponse(
                    assignment=saved,
                    message=f"Successfully assigned {subject.name} to {faculty.full_name}"
                )

    async def get_faculty_assignments(
        self,
        faculty_id: str,
        requesting_user: Optional[User] = None
    ) -> List[SubjectAssignment]:
        """
        Get all assignments for a specific faculty member.

        Args:
            faculty_id: ID of the faculty
            requesting_user: User making the request (for authorization check)

        Returns:
            List of SubjectAssignment entities

        Raises:
            AuthorizationError: If requesting_user is not the faculty or admin
            ResourceNotFoundError: If faculty not found
        """
        # Authorization: faculty can see own assignments, admins can see all
        if requesting_user:
            if requesting_user.role == UserRole.FACULTY:
                if requesting_user.id != faculty_id:
                    raise AuthorizationError(
                        "Faculty members can only view their own assignments"
                    )
            elif requesting_user.role != UserRole.ADMIN:
                raise AuthorizationError(
                    "Unauthorized to view faculty assignments"
                )

        # Verify faculty exists
        faculty = await self.user_repo.find_by_id(faculty_id)
        if not faculty:
            raise ResourceNotFoundError("Faculty", faculty_id)

        if faculty.role != UserRole.FACULTY:
            raise ValidationError(f"User {faculty_id} is not a faculty member")

        return await self.assignment_repo.find_by_faculty(faculty_id)

    async def get_all_assignments(
        self,
        semester: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """
        Get all subject assignments with optional filters.

        Args:
            semester: Filter by semester (optional)
            section: Filter by section (optional)

        Returns:
            List of SubjectAssignment entities
        """
        return await self.assignment_repo.find_all(
            semester=semester,
            section=section
        )

    async def find_assignments(
        self,
        faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        semester: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """
        Find assignments with multiple filters.

        Args:
            faculty_id: Filter by faculty ID (optional)
            subject_id: Filter by subject ID (optional)
            semester: Filter by semester (optional)
            section: Filter by section (optional)

        Returns:
            List of SubjectAssignment entities matching filters
        """
        if faculty_id:
            return await self.assignment_repo.find_by_faculty(faculty_id)
        elif subject_id:
            return await self.assignment_repo.find_by_subject(subject_id)
        else:
            return await self.assignment_repo.find_all(
                semester=semester,
                section=section
            )

    async def remove_assignment(
        self,
        assignment_id: str,
        current_user: User
    ) -> bool:
        """
        Remove a subject assignment.

        Args:
            assignment_id: ID of the assignment to remove
            current_user: User making the request (must be admin)

        Returns:
            True if removed, False otherwise

        Raises:
            AuthorizationError: If current_user is not admin
            ResourceNotFoundError: If assignment not found
        """
        # Authorization check
        if current_user.role != UserRole.ADMIN:
            raise AuthorizationError(
                "Only administrators can remove subject assignments"
            )

        # Verify assignment exists
        assignment = await self.assignment_repo.find_by_id(assignment_id)
        if not assignment:
            raise ResourceNotFoundError("Assignment", assignment_id)

        return await self.assignment_repo.delete(assignment_id)

    @property
    def client(self) -> AsyncIOMotorClientSession:
        """Get MongoDB client for transactions."""
        return self.db.client
