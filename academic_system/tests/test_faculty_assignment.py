"""Tests for faculty assignment service."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.use_cases.faculty_assignment import (
    FacultyAssignmentService,
    AssignSubjectRequest,
    AssignSubjectResponse
)
from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.entities.user import User, UserRole
from app.domain.entities.subject import Subject, SubjectType
from app.domain.exceptions import ValidationError, ResourceNotFoundError, AuthorizationError


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    class FakeTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def start_transaction(self):
            return FakeTransaction()

    class FakeClient:
        async def start_session(self):
            return FakeSession()

    db = Mock()
    db.client = FakeClient()
    return db


@pytest.fixture
def admin_user():
    """Create admin user for testing."""
    return User(
        id="admin123",
        email="admin@test.edu",
        password_hash="hashed-password",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def faculty_user():
    """Create faculty user for testing."""
    return User(
        id="faculty123",
        email="faculty@test.edu",
        password_hash="hashed-password",
        full_name="Dr. John Doe",
        role=UserRole.FACULTY,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def student_user():
    """Create student user for testing."""
    return User(
        id="student123",
        email="student@test.edu",
        password_hash="hashed-password",
        full_name="Jane Student",
        role=UserRole.STUDENT,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def test_subject():
    """Create test subject."""
    return Subject(
        id="subject123",
        code="CS101",
        name="Introduction to Computer Science",
        semester=1,
        subject_type=SubjectType.THEORY,
        credits=4,
        classes_per_week=4
    )


@pytest.fixture
def test_lab_subject():
    """Create test lab subject."""
    return Subject(
        id="lab123",
        code="CS151",
        name="Programming Lab",
        semester=1,
        subject_type=SubjectType.LAB,
        credits=2,
        classes_per_week=2
    )


@pytest.fixture
def second_theory_subject():
    """Create a second theory subject."""
    return Subject(
        id="subject456",
        code="CS102",
        name="Data Structures",
        semester=1,
        subject_type=SubjectType.THEORY,
        credits=3,
        classes_per_week=3
    )


@pytest.fixture
def second_lab_subject():
    """Create a second lab subject."""
    return Subject(
        id="lab456",
        code="CS152",
        name="Data Structures Lab",
        semester=1,
        subject_type=SubjectType.LAB,
        credits=2,
        classes_per_week=2
    )


@pytest.fixture
def mock_assignment_repo():
    """Mock subject assignment repository."""
    repo = Mock()
    repo.save = AsyncMock()
    repo.find_faculty_assignment = AsyncMock(return_value=None)
    repo.find_by_faculty_and_semester = AsyncMock(return_value=[])
    repo.find_by_id = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_subject_repo():
    """Mock subject repository."""
    repo = Mock()
    repo.find_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_user_repo():
    """Mock user repository."""
    repo = Mock()
    repo.find_by_id = AsyncMock(return_value=None)
    return repo


@pytest.mark.asyncio
async def test_assign_subject_success(
    mock_db, admin_user, faculty_user, test_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test successful subject assignment with transaction safety."""
    # Setup mocks
    mock_subject_repo.find_by_id.return_value = test_subject
    mock_user_repo.find_by_id.return_value = faculty_user

    saved_assignment = SubjectAssignment(
        id="assignment123",
        subject_id="subject123",
        semester=1,
        section="A",
        faculty_id="faculty123",
        is_primary=True,
        created_at=datetime.utcnow()
    )
    mock_assignment_repo.save.return_value = saved_assignment

    # Create service
    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = AssignSubjectRequest(
        subject_id="subject123",
        faculty_id="faculty123",
        semester=1,
        section="A",
        is_primary=True
    )

    # Execute
    result = await service.assign_subject(request, admin_user)

    # Assertions
    assert isinstance(result, AssignSubjectResponse)
    assert result.assignment.id == "assignment123"
    assert result.assignment.faculty_id == "faculty123"
    assert result.assignment.subject_id == "subject123"
    assert "Successfully assigned" in result.message

    # Verify repository calls
    mock_subject_repo.find_by_id.assert_called_once_with("subject123")
    mock_user_repo.find_by_id.assert_called_once_with("faculty123")
    mock_assignment_repo.find_faculty_assignment.assert_called_once()
    mock_assignment_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_assign_subject_duplicate_fails(
    mock_db, admin_user, faculty_user, test_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that duplicate assignment fails with unique constraint."""
    # Setup mocks - return existing assignment
    mock_subject_repo.find_by_id.return_value = test_subject
    mock_user_repo.find_by_id.return_value = faculty_user

    existing_assignment = SubjectAssignment(
        id="existing123",
        subject_id="subject123",
        semester=1,
        section="A",
        faculty_id="faculty123",
        is_primary=True,
        created_at=datetime.utcnow()
    )
    mock_assignment_repo.find_faculty_assignment.return_value = existing_assignment

    # Create service
    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = AssignSubjectRequest(
        subject_id="subject123",
        faculty_id="faculty123",
        semester=1,
        section="A",
        is_primary=True
    )

    # Execute and assert exception
    with pytest.raises(ValidationError) as exc_info:
        await service.assign_subject(request, admin_user)

    assert "already assigned" in str(exc_info.value).lower()
    mock_assignment_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_assign_subject_not_found_fails(
    mock_db, admin_user,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that assignment fails when subject doesn't exist."""
    # Setup mocks - subject not found
    mock_subject_repo.find_by_id.return_value = None

    # Create service
    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = AssignSubjectRequest(
        subject_id="nonexistent123",
        faculty_id="faculty123",
        semester=1,
        section="A",
        is_primary=True
    )

    # Execute and assert exception
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.assign_subject(request, admin_user)

    assert "nonexistent123" in str(exc_info.value)
    mock_assignment_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_assign_subject_faculty_not_found_fails(
    mock_db, admin_user, test_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that assignment fails when faculty user doesn't exist."""
    # Setup mocks
    mock_subject_repo.find_by_id.return_value = test_subject
    mock_user_repo.find_by_id.return_value = None

    # Create service
    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = AssignSubjectRequest(
        subject_id="subject123",
        faculty_id="nonexistent_faculty",
        semester=1,
        section="A",
        is_primary=True
    )

    # Execute and assert exception
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.assign_subject(request, admin_user)

    assert "nonexistent_faculty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_assign_subject_non_admin_fails(
    mock_db, student_user,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that non-admin users cannot assign subjects."""
    # Create service
    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = AssignSubjectRequest(
        subject_id="subject123",
        faculty_id="faculty123",
        semester=1,
        section="A",
        is_primary=True
    )

    # Execute and assert exception
    with pytest.raises(AuthorizationError) as exc_info:
        await service.assign_subject(request, student_user)

    assert "only administrators" in str(exc_info.value).lower()
    mock_assignment_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_assign_subject_non_faculty_role_fails(
    mock_db, admin_user, student_user, test_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that assigning a non-faculty user fails validation."""
    # Setup mocks - user exists but is not faculty
    mock_subject_repo.find_by_id.return_value = test_subject
    mock_user_repo.find_by_id.return_value = student_user  # Student, not faculty

    # Create service
    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = AssignSubjectRequest(
        subject_id="subject123",
        faculty_id="student123",  # Student ID
        semester=1,
        section="A",
        is_primary=True
    )

    # Execute and assert exception
    with pytest.raises(ValidationError) as exc_info:
        await service.assign_subject(request, admin_user)

    assert "not a faculty member" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_assign_subject_allows_one_theory_and_one_lab_per_semester(
    mock_db, admin_user, faculty_user, test_subject, test_lab_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that a faculty member can have one theory and one lab in a semester."""
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_by_faculty_and_semester.return_value = [
        SubjectAssignment(
            id="existing123",
            subject_id=test_subject.id,
            semester=1,
            section="A",
            faculty_id=faculty_user.id,
            is_primary=True,
            created_at=datetime.utcnow()
        )
    ]

    def find_subject(subject_id):
        return {
            test_lab_subject.id: test_lab_subject,
            test_subject.id: test_subject,
        }.get(subject_id)

    mock_subject_repo.find_by_id.side_effect = find_subject
    mock_assignment_repo.save.return_value = SubjectAssignment(
        id="assignment123",
        subject_id=test_lab_subject.id,
        semester=1,
        section="A",
        faculty_id=faculty_user.id,
        is_primary=True,
        created_at=datetime.utcnow()
    )

    request = AssignSubjectRequest(
        subject_id=test_lab_subject.id,
        faculty_id=faculty_user.id,
        semester=1,
        section="A",
        is_primary=True
    )

    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )

    result = await service.assign_subject(request, admin_user)

    assert result.assignment.subject_id == test_lab_subject.id
    mock_assignment_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_assign_subject_rejects_second_theory_in_same_semester(
    mock_db, admin_user, faculty_user, test_subject, second_theory_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that a faculty member cannot have two different theory subjects."""
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_by_faculty_and_semester.return_value = [
        SubjectAssignment(
            id="existing123",
            subject_id=test_subject.id,
            semester=1,
            section="A",
            faculty_id=faculty_user.id,
            is_primary=True,
            created_at=datetime.utcnow()
        )
    ]

    def find_subject(subject_id):
        return {
            second_theory_subject.id: second_theory_subject,
            test_subject.id: test_subject,
        }.get(subject_id)

    mock_subject_repo.find_by_id.side_effect = find_subject

    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )
    request = AssignSubjectRequest(
        subject_id=second_theory_subject.id,
        faculty_id=faculty_user.id,
        semester=1,
        section="A",
        is_primary=True
    )

    with pytest.raises(ValidationError) as exc_info:
        await service.assign_subject(request, admin_user)

    assert "one theory subject" in str(exc_info.value).lower()
    mock_assignment_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_assign_subject_rejects_second_lab_in_same_semester(
    mock_db, admin_user, faculty_user, test_lab_subject, second_lab_subject,
    mock_assignment_repo, mock_subject_repo, mock_user_repo
):
    """Test that a faculty member cannot have two different lab subjects."""
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_by_faculty_and_semester.return_value = [
        SubjectAssignment(
            id="existing123",
            subject_id=test_lab_subject.id,
            semester=1,
            section="A",
            faculty_id=faculty_user.id,
            is_primary=True,
            created_at=datetime.utcnow()
        )
    ]

    def find_subject(subject_id):
        return {
            second_lab_subject.id: second_lab_subject,
            test_lab_subject.id: test_lab_subject,
        }.get(subject_id)

    mock_subject_repo.find_by_id.side_effect = find_subject

    service = FacultyAssignmentService(
        mock_assignment_repo,
        mock_subject_repo,
        mock_user_repo,
        mock_db
    )
    request = AssignSubjectRequest(
        subject_id=second_lab_subject.id,
        faculty_id=faculty_user.id,
        semester=1,
        section="A",
        is_primary=True
    )

    with pytest.raises(ValidationError) as exc_info:
        await service.assign_subject(request, admin_user)

    assert "one lab subject" in str(exc_info.value).lower()
    mock_assignment_repo.save.assert_not_called()
