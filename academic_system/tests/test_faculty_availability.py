"""Tests for faculty availability service."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.use_cases.faculty_availability import (
    FacultyAvailabilityService,
    UpdateAvailabilityRequest,
    EffectiveAvailabilityResponse
)
from app.domain.entities.faculty_availability import (
    FacultyAvailability,
    AvailableSlot,
    DayOfWeek
)
from app.domain.entities.admin_override_log import (
    AdminOverrideLog,
    OverrideSlot,
    OverrideType,
    OverrideAction
)
from app.domain.entities.user import User, UserRole
from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.exceptions import ValidationError, ResourceNotFoundError, AuthorizationError


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    return Mock()


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
def other_faculty_user():
    """Create another faculty user for testing ownership."""
    return User(
        id="faculty456",
        email="other@test.edu",
        password_hash="hashed-password",
        full_name="Dr. Jane Smith",
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
def existing_assignment():
    """Create existing subject assignment."""
    return SubjectAssignment(
        id="assignment123",
        subject_id="subject123",
        semester=1,
        section="A",
        faculty_id="faculty123",
        is_primary=True,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_availability_repo():
    """Mock faculty availability repository."""
    repo = Mock()
    repo.find = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.update = AsyncMock()
    repo.find_by_faculty = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_override_repo():
    """Mock admin override repository."""
    repo = Mock()
    repo.find_applicable = AsyncMock(return_value=[])
    repo.find_audit_log = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_assignment_repo():
    """Mock subject assignment repository."""
    repo = Mock()
    repo.find_faculty_assignment = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_user_repo():
    """Mock user repository."""
    repo = Mock()
    repo.find_by_id = AsyncMock(return_value=None)
    return repo


@pytest.mark.asyncio
async def test_update_availability_success(
    mock_db,
    faculty_user,
    existing_assignment,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test successful availability update with ownership check."""
    # Setup mocks
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_faculty_assignment.return_value = existing_assignment

    updated_availability = FacultyAvailability(
        id="availability123",
        faculty_id="faculty123",
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
            AvailableSlot(day=DayOfWeek.TUE, slot=1)
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_availability_repo.find.return_value = updated_availability
    mock_availability_repo.update.return_value = updated_availability

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Create request with valid slots
    request = UpdateAvailabilityRequest(
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 1}
        ]
    )

    # Execute
    result = await service.update_availability(request, "faculty123", faculty_user)

    # Assertions
    assert result.faculty_id == "faculty123"
    assert len(result.available_slots) == 3
    mock_availability_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_availability_ownership_fails(
    mock_db,
    other_faculty_user,
    faculty_user,
    existing_assignment,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test that faculty cannot update another faculty's availability."""
    # Setup mocks - return the faculty being updated (not the one making request)
    mock_user_repo.find_by_id.return_value = faculty_user

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Create request - other_faculty_user trying to update faculty_user's availability
    request = UpdateAvailabilityRequest(
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 1}
        ]
    )

    # Execute and assert exception
    with pytest.raises(AuthorizationError) as exc_info:
        await service.update_availability(request, "faculty123", other_faculty_user)

    assert "only update their own" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_availability_min_slots_fails(
    mock_db,
    admin_user,
    faculty_user,
    existing_assignment,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test that availability update fails with insufficient slots."""
    # Setup mocks
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_faculty_assignment.return_value = existing_assignment

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Create request with only 2 slots (less than MIN_REQUIRED_SLOTS = 3)
    request = UpdateAvailabilityRequest(
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2}
        ]
    )

    # Execute and assert exception
    with pytest.raises(ValidationError) as exc_info:
        await service.update_availability(request, "faculty123", admin_user)

    assert "at least 3" in str(exc_info.value).lower()
    mock_availability_repo.save.assert_not_called()
    mock_availability_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_availability_no_assignment_fails(
    mock_db,
    admin_user,
    faculty_user,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test that availability update fails when faculty not assigned to subject."""
    # Setup mocks
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_faculty_assignment.return_value = None  # No assignment

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Create request
    request = UpdateAvailabilityRequest(
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 1}
        ]
    )

    # Execute and assert exception
    with pytest.raises(ValidationError) as exc_info:
        await service.update_availability(request, "faculty123", admin_user)

    assert "not assigned" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_availability_invalid_slot_fails(
    mock_db,
    admin_user,
    faculty_user,
    existing_assignment,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test that availability update fails with invalid slot number."""
    # Setup mocks
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_faculty_assignment.return_value = existing_assignment

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Create request with invalid slot (slot 11, max is 10)
    request = UpdateAvailabilityRequest(
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 11}  # Invalid slot
        ]
    )

    # Execute and assert exception
    with pytest.raises(ValidationError) as exc_info:
        await service.update_availability(request, "faculty123", admin_user)

    assert "slot must be between" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_effective_availability_with_overrides(
    mock_db,
    faculty_user,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test effective availability computation with override application."""
    # Setup base availability
    base_availability = FacultyAvailability(
        id="availability123",
        faculty_id="faculty123",
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
            AvailableSlot(day=DayOfWeek.TUE, slot=1)
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Setup overrides - one ADD, one REMOVE
    override = AdminOverrideLog(
        id="override123",
        admin_id="admin123",
        faculty_id="faculty123",
        subject_id="subject123",
        semester=1,
        section="A",
        override_type=OverrideType.PERSISTENT,
        applied=False,
        slots=[
            OverrideSlot(day=DayOfWeek.WED, slot=1, action=OverrideAction.ADD),
            OverrideSlot(day=DayOfWeek.MON, slot=2, action=OverrideAction.REMOVE)
        ],
        timestamp=datetime.utcnow()
    )

    mock_availability_repo.find.return_value = base_availability
    mock_override_repo.find_applicable.return_value = [override]

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Execute
    result = await service.get_effective_availability(
        faculty_id="faculty123",
        subject_id="subject123",
        semester=1,
        section="A",
        requesting_user=faculty_user
    )

    # Assertions
    assert isinstance(result, EffectiveAvailabilityResponse)
    assert len(result.base_slots) == 3  # Original base slots
    assert len(result.effective_slots) == 3  # After applying overrides (ADD WED-1, REMOVE MON-2)
    assert len(result.applied_overrides) == 1

    # Check effective slots contain WED slot 1 (added)
    slot_tuples = [(s.day.value, s.slot) for s in result.effective_slots]
    assert (DayOfWeek.WED.value, 1) in slot_tuples

    # Check MON slot 2 was removed
    assert (DayOfWeek.MON.value, 2) not in slot_tuples


@pytest.mark.asyncio
async def test_get_effective_availability_unauthorized_fails(
    mock_db,
    other_faculty_user,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test that faculty cannot view another faculty's availability."""
    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Execute and assert exception - other_faculty trying to view faculty123's availability
    with pytest.raises(AuthorizationError) as exc_info:
        await service.get_effective_availability(
            faculty_id="faculty123",
            subject_id="subject123",
            semester=1,
            section="A",
            requesting_user=other_faculty_user
        )

    assert "only view their own" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_availability_duplicate_slots_fails(
    mock_db,
    admin_user,
    faculty_user,
    existing_assignment,
    mock_availability_repo,
    mock_override_repo,
    mock_assignment_repo,
    mock_user_repo
):
    """Test that duplicate slots in request are rejected."""
    # Setup mocks
    mock_user_repo.find_by_id.return_value = faculty_user
    mock_assignment_repo.find_faculty_assignment.return_value = existing_assignment

    # Create service
    service = FacultyAvailabilityService(
        mock_availability_repo,
        mock_override_repo,
        mock_assignment_repo,
        mock_user_repo,
        mock_db
    )

    # Create request with duplicate slots
    request = UpdateAvailabilityRequest(
        subject_id="subject123",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 1},  # Duplicate
            {"day": "TUE", "slot": 1}
        ]
    )

    # Execute and assert exception
    with pytest.raises(ValidationError) as exc_info:
        await service.update_availability(request, "faculty123", admin_user)

    assert "duplicate" in str(exc_info.value).lower()
