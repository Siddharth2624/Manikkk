# tests/adapters/repositories/test_generation_telemetry_repository.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.feasibility import GenerationTelemetry
from app.adapters.repositories.generation_telemetry_repository import (
    GenerationTelemetryRepository,
    TelemetryConfig
)
from bson import ObjectId


def _create_mock_cursor(to_list_return_value):
    """Helper to create a properly mocked cursor chain: find().sort().limit()"""
    # The final cursor with to_list
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=to_list_return_value)

    # Create an object that has limit() method returning the cursor
    class MockWithLimit:
        def limit(self, n):
            return mock_cursor

    mock_sort_result = MockWithLimit()

    # find() returns an object with sort() returning the sort result
    class MockWithSort:
        def __call__(self, query, projection):
            return self

        def sort(self, field, direction):
            return mock_sort_result

    return MockWithSort(), mock_cursor


@pytest.mark.asyncio
async def test_save_telemetry_when_enabled():
    """Should save when config enables persistence."""
    # Mock collection methods first
    mock_collection = MagicMock()
    mock_collection.estimated_document_count = AsyncMock(return_value=100)
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(acknowledged=True))

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(enabled=True, persistence_enabled=True)
    repo = GenerationTelemetryRepository(db, config)

    telemetry = GenerationTelemetry(
        generation_timestamp=datetime.utcnow(),
        semester=1,
        section="A",
        feasibility_confidence=75,
        generation_seed="abc123",
        actual_attempts_used=5000,
        success=True,
        duration_ms=1500,
        bottleneck_subjects=[],
        total_backtracks=0,
        backtrack_by_reason={},
        conflict_hotspots=[]
    )

    result = await repo.save(telemetry)
    assert result is True


@pytest.mark.asyncio
async def test_save_telemetry_when_disabled():
    """Should return True without saving when disabled."""
    # Mock collection methods first
    mock_collection = MagicMock()

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(enabled=False)
    repo = GenerationTelemetryRepository(db, config)

    telemetry = GenerationTelemetry(
        generation_timestamp=datetime.utcnow(),
        semester=1,
        section="A",
        feasibility_confidence=75,
        generation_seed="abc123",
        actual_attempts_used=5000,
        success=True,
        duration_ms=1500,
        bottleneck_subjects=[],
        total_backtracks=0,
        backtrack_by_reason={},
        conflict_hotspots=[]
    )

    result = await repo.save(telemetry)
    assert result is True  # Should not fail, just skip
    # Verify insert_one was NOT called when disabled
    mock_collection.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_expired():
    """Should remove records older than retention_days."""
    # Mock collection methods first
    mock_collection = MagicMock()
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(retention_days=30)
    repo = GenerationTelemetryRepository(db, config)

    deleted_count = await repo.cleanup_expired()

    # Verify delete_many was called with date cutoff
    args, _ = mock_collection.delete_many.call_args
    query = args[0]
    assert "generation_timestamp" in query
    assert "$lt" in query["generation_timestamp"]
    assert deleted_count == 5


@pytest.mark.asyncio
async def test_cleanup_oldest_when_limit_reached():
    """Should fetch oldest IDs and delete them explicitly."""
    # Mock collection methods first
    mock_collection = MagicMock()
    mock_collection.estimated_document_count = AsyncMock(return_value=100)

    # Mock the cursor chain: find().sort().limit()
    mock_find, mock_cursor = _create_mock_cursor([
        {"_id": ObjectId("507f1f77bcf86cd799439011")},
        {"_id": ObjectId("507f1f77bcf86cd799439012")},
    ])
    mock_collection.find = mock_find

    # Mock delete_many
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=2))

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(max_records=100)
    repo = GenerationTelemetryRepository(db, config)

    await repo._cleanup_oldest()

    # Verify delete_many was called with IDs
    args, _ = mock_collection.delete_many.call_args
    query = args[0]
    assert "_id" in query
    assert "$in" in query["_id"]


@pytest.mark.asyncio
async def test_cleanup_oldest_empty_collection():
    """Should handle empty collection gracefully."""
    # Mock collection methods first
    mock_collection = MagicMock()
    mock_collection.estimated_document_count = AsyncMock(return_value=100)

    # Mock the cursor chain: find().sort().limit()
    mock_find, mock_cursor = _create_mock_cursor([])
    mock_collection.find = mock_find

    # Mock delete_many
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(max_records=100)
    repo = GenerationTelemetryRepository(db, config)

    await repo._cleanup_oldest()

    # Verify delete_many was NOT called since no records
    mock_collection.delete_many.assert_not_called()


@pytest.mark.asyncio
async def test_save_triggers_cleanup_when_at_limit():
    """Should trigger cleanup of oldest records when max reached."""
    # Mock collection methods first
    mock_collection = MagicMock()
    mock_collection.estimated_document_count = AsyncMock(return_value=100)

    # Mock the cursor chain: find().sort().limit()
    mock_find, mock_cursor = _create_mock_cursor([
        {"_id": ObjectId("507f1f77bcf86cd799439011")},
    ])
    mock_collection.find = mock_find

    # Mock delete_many and insert_one
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=1))
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(acknowledged=True))

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(max_records=100)
    repo = GenerationTelemetryRepository(db, config)

    telemetry = GenerationTelemetry(
        generation_timestamp=datetime.utcnow(),
        semester=1,
        section="A",
        feasibility_confidence=75,
        generation_seed="abc123",
        actual_attempts_used=5000,
        success=True,
        duration_ms=1500,
        bottleneck_subjects=[],
        total_backtracks=0,
        backtrack_by_reason={},
        conflict_hotspots=[]
    )

    result = await repo.save(telemetry)

    assert result is True
    # Verify both cleanup and insert happened
    mock_collection.delete_many.assert_called_once()
    mock_collection.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_expired_when_disabled():
    """Should return 0 when telemetry is disabled."""
    # Mock collection methods first
    mock_collection = MagicMock()
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))

    # Create db mock with collection
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    db.generation_telemetry = mock_collection

    config = TelemetryConfig(enabled=False, retention_days=30)
    repo = GenerationTelemetryRepository(db, config)

    deleted_count = await repo.cleanup_expired()

    # Verify delete_many was NOT called when disabled
    mock_collection.delete_many.assert_not_called()
    assert deleted_count == 0
