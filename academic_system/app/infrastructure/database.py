"""MongoDB database connection and client management."""

from typing import AsyncGenerator, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from contextlib import asynccontextmanager
import logging

from .config import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager."""

    client: Optional[AsyncIOMotorClient] = None

    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        if self.client is None:
            # Add TLS options for Windows compatibility
            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                tls=True,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
            )
            # Verify connection
            try:
                await self.client.admin.command('ping')
                logger.info(f"Connected to MongoDB at {settings.mongodb_url}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client is not None:
            self.client.close()
            self.client = None
            logger.info("Disconnected from MongoDB")

    def get_database(self):
        """Get the database instance."""
        if self.client is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.client[settings.mongodb_database]

    async def ping(self) -> bool:
        """Check if database connection is alive."""
        if self.client is None:
            return False
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False


# Global database instance
db = Database()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator:
    """Context manager for database session."""
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()


async def get_database():
    """Dependency to get database instance."""
    if db.client is None:
        await db.connect()
    return db.get_database()


async def create_faculty_availability_indexes(db):
    """Create indexes for faculty_availability collection."""
    collection = db.faculty_availability

    # Unique constraint
    await collection.create_index(
        [("faculty_id", 1), ("subject_id", 1), ("semester", 1), ("section", 1)],
        unique=True
    )

    # Query indexes
    await collection.create_index([
        ("faculty_id", 1), ("semester", 1), ("section", 1)
    ])
    await collection.create_index([
        ("subject_id", 1), ("semester", 1), ("section", 1)
    ])


async def create_admin_override_log_indexes(db):
    """Create indexes for admin_override_log collection."""
    collection = db.admin_override_log

    # Query index
    await collection.create_index([
        ("faculty_id", 1), ("subject_id", 1), ("semester", 1), ("section", 1)
    ])

    # Audit query index
    await collection.create_index([("faculty_id", 1), ("subject_id", 1)])

    # Timestamp index for sorting
    await collection.create_index([("timestamp", -1)])


async def init_indexes():
    """Initialize database indexes for optimal query performance.

    Updated for redesigned schema:
    - subjects: simplified (no sections, no faculty_id)
    - subject_assignments: NEW collection for subject-section-faculty relationships
    - timetables: single document per semester-section
    """
    database = db.get_database()

    # Helper function to create index with error handling
    async def safe_create_index(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except Exception as e:
            # Ignore errors for existing indexes or other issues
            pass  # Silently ignore - indexes will be created on first run or already exist

    # Users indexes
    await safe_create_index(database.users, "email", unique=True)
    await safe_create_index(database.users, "roll_number", unique=True, sparse=True)
    await safe_create_index(database.users, "employee_id", unique=True, sparse=True)
    await safe_create_index(database.users, "role")
    await safe_create_index(database.users, [("role", 1), ("semester", 1)])
    await safe_create_index(database.users, [("role", 1), ("semester", 1), ("section", 1)])

    # Subjects indexes - simplified schema (no sections, no faculty_id)
    await safe_create_index(database.subjects, "code", unique=True, sparse=True)
    await safe_create_index(database.subjects, "semester")
    await safe_create_index(database.subjects, "subject_type")
    await safe_create_index(database.subjects, [("semester", 1), ("subject_type", 1)])

    # Subject assignments indexes
    await safe_create_index(database.subject_assignments,
        [("faculty_id", 1), ("subject_id", 1), ("semester", 1), ("section", 1)],
        unique=True
    )
    await safe_create_index(database.subject_assignments,
        [("semester", 1), ("section", 1)]
    )
    await safe_create_index(database.subject_assignments, [("faculty_id", 1)])
    await safe_create_index(database.subject_assignments, [("subject_id", 1)])

    # Timetables indexes
    await safe_create_index(database.timetables,
        [("semester", 1), ("section", 1), ("is_active", -1)]
    )
    await safe_create_index(database.timetables,
        [("semester", 1), ("section", 1), ("version", -1)]
    )
    await safe_create_index(database.timetables, "is_active")

    # Semesters indexes
    await safe_create_index(database.semesters, "semester_number")
    await safe_create_index(database.semesters, "branch")
    await safe_create_index(database.semesters, "status")

    # Attendance indexes
    await safe_create_index(database.attendances,
        [("student_id", 1), ("subject_id", 1), ("date", 1)], unique=True
    )
    await safe_create_index(database.attendances, [("subject_id", 1), ("date", 1)])
    await safe_create_index(database.attendances, "faculty_id")
    await safe_create_index(database.attendances, [("student_id", 1), ("date", 1)])

    # Study materials indexes
    await safe_create_index(database.study_materials, [("subject_id", 1), ("semester", 1)])
    await safe_create_index(database.study_materials, [("semester", 1), ("sections", 1), ("subject_id", 1)])
    await safe_create_index(database.study_materials, "faculty_id")
    await safe_create_index(database.study_materials, "material_date", -1)
    await safe_create_index(database.study_materials, "title")

    # Faculty availability indexes
    await create_faculty_availability_indexes(database)

    # Admin override log indexes
    await create_admin_override_log_indexes(database)

    logger.info("Database indexes initialized successfully")
