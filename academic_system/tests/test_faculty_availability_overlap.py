"""Tests for non-exclusive faculty availability collection."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities.faculty_availability import (
    AvailableSlot,
    DayOfWeek,
    FacultyAvailability,
)
from app.domain.entities.user import User, UserRole
from app.use_cases.faculty_availability import (
    FacultyAvailabilityService,
    UpdateAvailabilityRequest,
)


@pytest.fixture
def mock_repos():
    availability_repo = AsyncMock()
    override_repo = AsyncMock()
    assignment_repo = AsyncMock()
    user_repo = AsyncMock()
    db = AsyncMock()
    return availability_repo, override_repo, assignment_repo, user_repo, db


@pytest.fixture
def service(mock_repos):
    availability_repo, override_repo, assignment_repo, user_repo, db = mock_repos
    return FacultyAvailabilityService(
        availability_repo=availability_repo,
        override_repo=override_repo,
        assignment_repo=assignment_repo,
        user_repo=user_repo,
        db=db,
    )


@pytest.fixture
def mock_faculty_user():
    user = MagicMock(spec=User)
    user.id = "faculty1"
    user.role = UserRole.FACULTY
    user.full_name = "Dr. Smith"
    return user


@pytest.mark.asyncio
async def test_update_availability_allows_overlap_with_other_faculty(
    service,
    mock_repos,
    mock_faculty_user,
):
    """Faculty availability is not a reservation, so overlaps are valid input."""
    availability_repo, _, assignment_repo, user_repo, _ = mock_repos
    user_repo.find_by_id.return_value = mock_faculty_user
    assignment_repo.find_faculty_assignment.return_value = MagicMock()
    availability_repo.find.return_value = None

    saved_availability = FacultyAvailability(
        id="avail1",
        faculty_id="faculty1",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.MON, slot=2),
            AvailableSlot(day=DayOfWeek.TUE, slot=3),
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    availability_repo.save.return_value = saved_availability

    request = UpdateAvailabilityRequest(
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            {"day": "MON", "slot": 1},
            {"day": "MON", "slot": 2},
            {"day": "TUE", "slot": 3},
        ],
    )

    result = await service.update_availability(request, "faculty1", mock_faculty_user)

    assert result == saved_availability
    availability_repo.save.assert_awaited_once()
    availability_repo.find_by_semester_and_section.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_occupied_slots_is_informational_only(
    service,
    mock_repos,
):
    """The overlap summary can still be used for diagnostics without blocking saves."""
    availability_repo, _, _, user_repo, _ = mock_repos
    other_faculty_avail = FacultyAvailability(
        id="avail2",
        faculty_id="faculty2",
        subject_id="sub1",
        semester=1,
        section="A",
        available_slots=[
            AvailableSlot(day=DayOfWeek.MON, slot=1),
            AvailableSlot(day=DayOfWeek.TUE, slot=3),
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    availability_repo.find_by_semester_and_section.return_value = [other_faculty_avail]

    other_faculty = MagicMock(spec=User)
    other_faculty.full_name = "Dr. Jones"
    user_repo.find_by_id.return_value = other_faculty

    overlaps = await service.get_occupied_slots(
        semester=1,
        section="A",
        exclude_faculty_id="faculty1",
    )

    assert overlaps == {
        ("MON", 1): "Dr. Jones",
        ("TUE", 3): "Dr. Jones",
    }
