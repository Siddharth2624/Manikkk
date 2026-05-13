from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.adapters.repositories.faculty_availability_repository import (
    FacultyAvailabilityRepository,
)
from app.domain.entities.faculty_availability import DayOfWeek


@pytest.mark.asyncio
async def test_find_by_faculty_and_subject_uses_assignment_key():
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "faculty_id": ObjectId(),
            "subject_id": ObjectId(),
            "semester": 3,
            "section": "A",
            "available_slots": [{"day": DayOfWeek.MON.value, "slot": 1}],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )

    db = MagicMock()
    db.faculty_availability = collection

    repo = FacultyAvailabilityRepository(db)
    faculty_id = str(ObjectId())
    subject_id = str(ObjectId())

    result = await repo.find_by_faculty_and_subject(
        faculty_id=faculty_id,
        subject_id=subject_id,
        semester=3,
        section="A",
    )

    assert result is not None
    assert result.semester == 3
    assert result.section == "A"
    assert result.available_slots[0].day == DayOfWeek.MON
    collection.find_one.assert_awaited_once_with(
        {
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": 3,
            "section": "A",
        }
    )
