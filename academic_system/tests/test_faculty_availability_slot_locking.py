"""Tests for faculty availability slot locking across faculty."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.use_cases.faculty_availability import FacultyAvailabilityService, UpdateAvailabilityRequest
from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.entities.user import User, UserRole
from app.domain.exceptions import ValidationError


@pytest.fixture
def mock_repos():
    """Create mock repositories."""
    availability_repo = AsyncMock()
    override_repo = AsyncMock()
    assignment_repo = AsyncMock()
    user_repo = AsyncMock()
    db = AsyncMock()
    return availability_repo, override_repo, assignment_repo, user_repo, db


@pytest.fixture
def service(mock_repos):
    """Create FacultyAvailabilityService with mock repos."""
    availability_repo, override_repo, assignment_repo, user_repo, db = mock_repos
    return FacultyAvailabilityService(
        availability_repo=availability_repo,
        override_repo=override_repo,
        assignment_repo=assignment_repo,
        user_repo=user_repo,
        db=db
    )


@pytest.fixture
def mock_faculty_user():
    """Create a mock faculty user."""
    user = MagicMock(spec=User)
    user.id = "faculty1"
    user.role = UserRole.FACULTY
    user.full_name = "Dr. Smith"
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = "admin1"
    user.role = UserRole.ADMIN
    user.full_name = "Admin User"
    return user


@pytest.mark.asyncio
async def test_get_occupied_slots_returns_conflicting_slots(service, mock_repos, mock_faculty_user):
    """Should return slots occupied by other faculty for the same semester/section."""
    availability_repo, _, _, user_repo, _ = mock_repos

    # Setup: Faculty2 has availability for semester 1, section A
    other_faculty_avail = FacultyAvailability(
        id="avail2",
        faculty_id="faculty2",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
            AvailableSlot(day=DayOfWeek.TUE, slot=3),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    availability_repo.find_by_semester_and_section.return_value = [other_faculty_avail]

    # Mock other faculty user
    other_faculty = MagicMock(spec=User)
    other_faculty.full_name = "Dr. Jones"
    user_repo.find_by_id.return_value = other_faculty

    # Get occupied slots excluding faculty1
    occupied = await service.get_occupied_slots(
        semester=1,
        section="A",
        exclude_faculty_id="faculty1"
    )

    # Should have 3 occupied slots
    assert len(occupied) == 3
    assert ("MON", 1) in occupied
    assert ("MON", 2) in occupied
    assert ("TUE", 3) in occupied
    assert occupied[("MON", 1)] == "Dr. Jones"

    # Verify the repo was called correctly
    availability_repo.find_by_semester_and_section.assert_called_once_with(semester=1, section="A")


@pytest.mark.asyncio
async def test_get_occupied_slots_excludes_current_faculty(service, mock_repos, mock_faculty_user):
    """Should not include current faculty's own slots."""
    availability_repo, _, _, user_repo, _ = mock_repos

    # Setup: Current faculty has their own availability
    own_avail = FacultyAvailability(
        id="avail1",
        faculty_id="faculty1",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=5),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    availability_repo.find_by_semester_and_section.return_value = [own_avail]

    # Get occupied slots excluding faculty1 (should exclude their own)
    occupied = await service.get_occupied_slots(
        semester=1,
        section="A",
        exclude_faculty_id="faculty1"
    )

    # Should be empty since we excluded faculty1
    assert len(occupied) == 0


@pytest.mark.asyncio
async def test_update_availability_rejects_occupied_slots(service, mock_repos, mock_faculty_user):
    """Should reject update if slots are already occupied by other faculty."""
    availability_repo, _, assignment_repo, user_repo, _ = mock_repos

    # Setup: Another faculty already has MON-1 and MON-2
    other_faculty_avail = FacultyAvailability(
        id="avail2",
        faculty_id="faculty2",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    availability_repo.find_by_semester_and_section.return_value = [other_faculty_avail]
    availability_repo.find.return_value = None  # No existing availability for this faculty

    # Mock other faculty user
    other_faculty = MagicMock(spec=User)
    other_faculty.full_name = "Dr. Jones"
    user_repo.find_by_id.side_effect = lambda uid: {
        "faculty1": mock_faculty_user,
        "faculty2": other_faculty
    }.get(uid)

    # Mock assignment exists
    assignment_repo.find_faculty_assignment.return_value = MagicMock()

    # Try to update with slots including occupied ones
    request = UpdateAvailabilityRequest(
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},  # Occupied by Dr. Jones
            {"day": "MON", "slot": 2},  # Occupied by Dr. Jones
            {"day": "TUE", "slot": 3},  # Available
        ]
    )

    with pytest.raises(ValidationError) as exc_info:
        await service.update_availability(request, "faculty1", mock_faculty_user)

    error_msg = str(exc_info.value)
    assert "already selected by other faculty" in error_msg
    assert "Dr. Jones" in error_msg


@pytest.mark.asyncio
async def test_update_availability_allows_non_conflicting_slots(service, mock_repos, mock_faculty_user):
    """Should allow update if slots are not occupied by other faculty."""
    availability_repo, _, assignment_repo, user_repo, _ = mock_repos

    # Setup: Another faculty has different slots
    other_faculty_avail = FacultyAvailability(
        id="avail2",
        faculty_id="faculty2",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    availability_repo.find_by_semester_and_section.return_value = [other_faculty_avail]
    availability_repo.find.return_value = None

    # Mock users
    user_repo.find_by_id.return_value = mock_faculty_user

    # Mock assignment exists
    assignment_repo.find_faculty_assignment.return_value = MagicMock()

    # Mock save
    availability_repo.save.return_value = FacultyAvailability(
        id="avail1",
        faculty_id="faculty1",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.TUE, slot=3),
            AvailableSlot(day=DayOfWeek.TUE, slot=4),
            AvailableSlot(day=DayOfWeek.WED, slot=5),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Update with non-conflicting slots
    request = UpdateAvailabilityRequest(
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            {"day": "TUE", "slot": 3},
            {"day": "TUE", "slot": 4},
            {"day": "WED", "slot": 5},
        ]
    )

    # Should succeed without raising
    result = await service.update_availability(request, "faculty1", mock_faculty_user)
    assert result is not None
    assert len(result.available_slots) == 3


@pytest.mark.asyncio
async def test_update_availability_allows_own_slots(service, mock_repos, mock_faculty_user):
    """Should allow faculty to update their own existing slots."""
    availability_repo, _, assignment_repo, user_repo, _ = mock_repos

    # Setup: Faculty1 already has some availability
    existing_avail = FacultyAvailability(
        id="avail1",
        faculty_id="faculty1",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    availability_repo.find_by_semester_and_section.return_value = [existing_avail]
    availability_repo.find.return_value = existing_avail

    # Mock users
    user_repo.find_by_id.return_value = mock_faculty_user

    # Mock assignment exists
    assignment_repo.find_faculty_assignment.return_value = MagicMock()

    # Mock update
    availability_repo.update.return_value = existing_avail

    # Update with same slots (no conflict since it's their own)
    request = UpdateAvailabilityRequest(
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 3},
        ]
    )

    # Should succeed - faculty can update their own slots
    result = await service.update_availability(request, "faculty1", mock_faculty_user)
    assert result is not None


