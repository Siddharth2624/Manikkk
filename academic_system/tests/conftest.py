"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import AsyncGenerator

from app.infrastructure.config import settings


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Create test database connection."""
    client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    db = client[f"{settings.mongodb_database}_test"]

    # Clean up before tests
    await client.drop_database(f"{settings.mongodb_database}_test")

    yield db

    # Clean up after tests
    await client.drop_database(f"{settings.mongodb_database}_test")
    client.close()


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "role": "student",
        "semester": 1,
        "section": "A"
    }


@pytest.fixture
def test_subject_data():
    """Sample subject data for testing."""
    return {
        "code": "CS101",
        "name": "Introduction to Computer Science",
        "semester": 1,
        "subject_type": "theory",
        "credits": 4,
        "classes_per_week": 4
    }
