#!/usr/bin/env python
"""CLI command to run database migrations.

Usage:
    python migrate.py status     - Show migration status
    python migrate.py up         - Run pending migrations
    python migrate.py init-indexes - Initialize database indexes
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set fallback environment variables
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DATABASE", "academic_system")


async def get_database():
    """Get database connection without loading full app."""
    from motor.motor_asyncio import AsyncIOMotorClient

    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_database = os.getenv("MONGODB_DATABASE", "academic_system")

    client = AsyncIOMotorClient(
        mongodb_url,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000,
    )

    # Verify connection
    try:
        await client.admin.command('ping')
        print(f"Connected to MongoDB at {mongodb_url}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

    return client[mongodb_database]


async def safe_create_index(collection, keys, **kwargs):
    """Safely create an index, ignoring if it already exists."""
    try:
        # Convert -1 to pymongo's DESCENDING for uploaded_at
        if keys == "uploaded_at" and kwargs.get("direction") == -1:
            keys = [("uploaded_at", -1)]
        elif isinstance(keys, str) and keys == "uploaded_at":
            # For simple string keys
            pass
        await collection.create_index(keys, **kwargs)
    except Exception as e:
        error_str = str(e)
        if "IndexKeySpecsConflict" in error_str or "already exists" in error_str:
            pass  # Index already exists, skip
        else:
            raise


async def init_indexes():
    """Initialize database indexes."""
    db = await get_database()

    print("Initializing database indexes...\n")

    # Users indexes
    await safe_create_index(db.users, "email", unique=True)
    await safe_create_index(db.users, "roll_number", unique=True, sparse=True)
    await safe_create_index(db.users, "employee_id", unique=True, sparse=True)
    await safe_create_index(db.users, "role")
    await safe_create_index(db.users, [("role", 1), ("semester", 1)])
    await safe_create_index(db.users, [("role", 1), ("semester", 1), ("section", 1)])

    # Subjects indexes - simplified schema
    await safe_create_index(db.subjects, "code", unique=True)
    await safe_create_index(db.subjects, "semester")
    await safe_create_index(db.subjects, "subject_type")
    await safe_create_index(db.subjects, [("semester", 1), ("subject_type", 1)])

    # Subject assignments indexes - NEW collection
    await safe_create_index(db.subject_assignments, [
        ("faculty_id", 1),
        ("subject_id", 1),
        ("semester", 1),
        ("section", 1),
        ("academic_year", 1)
    ], unique=True)
    await safe_create_index(db.subject_assignments, [
        ("semester", 1),
        ("section", 1),
        ("academic_year", 1)
    ])
    await safe_create_index(db.subject_assignments, [
        ("faculty_id", 1),
        ("academic_year", 1)
    ])
    await safe_create_index(db.subject_assignments, [
        ("subject_id", 1),
        ("academic_year", 1)
    ])

    # Timetables indexes - NEW single-document schema
    await safe_create_index(db.timetables, [
        ("semester", 1),
        ("section", 1),
        ("academic_year", 1),
        ("is_active", -1)
    ])
    await safe_create_index(db.timetables, [
        ("semester", 1),
        ("section", 1),
        ("academic_year", 1),
        ("version", -1)
    ])
    await safe_create_index(db.timetables, "is_active")

    # Semesters indexes
    await safe_create_index(db.semesters, "semester_number")
    await safe_create_index(db.semesters, "academic_year")
    await safe_create_index(db.semesters, [
        ("semester_number", 1),
        ("academic_year", 1)
    ], unique=True)
    await safe_create_index(db.semesters, "status")
    await safe_create_index(db.semesters, "branch")

    # Attendance indexes
    await safe_create_index(db.attendances, [
        ("student_id", 1), ("subject_id", 1), ("date", 1)
    ], unique=True)
    await safe_create_index(db.attendances, [("subject_id", 1), ("date", 1)])
    await safe_create_index(db.attendances, "faculty_id")
    await safe_create_index(db.attendances, [("student_id", 1), ("date", 1)])

    # Study materials indexes
    await safe_create_index(db.study_materials, [("subject_id", 1), ("semester", 1)])
    await safe_create_index(db.study_materials, "faculty_id")
    await safe_create_index(db.study_materials, [("uploaded_at", -1)])
    await safe_create_index(db.study_materials, "title")

    print("[OK] Database indexes initialized successfully")


async def migration_001_subject_assignments(db):
    """Create subject_assignments collection."""
    from datetime import datetime
    from bson import ObjectId

    details = {
        "subjects_processed": 0,
        "assignments_created": 0
    }

    try:
        # Check if collection already exists with data
        if "subject_assignments" in await db.list_collection_names():
            count = await db.subject_assignments.count_documents({})
            if count > 0:
                return {
                    "success": True,
                    "applied_at": datetime.utcnow(),
                    "details": {**details, "message": "Collection already exists"}
                }

        # Create collection with indexes
        await db.create_collection("subject_assignments")

        default_academic_year = "2024-2025"

        # Migrate data from subjects collection if it has the old structure
        async for subject_doc in db.subjects.find({
            "faculty_id": {"$exists": True},
            "sections": {"$exists": True, "$ne": []}
        }):
            subject_id = subject_doc["_id"]
            faculty_id = subject_doc.get("faculty_id")
            sections = subject_doc.get("sections", [])
            semester = subject_doc.get("semester")

            if not faculty_id or not sections:
                continue

            for section in sections:
                assignment = {
                    "_id": ObjectId(),
                    "subject_id": subject_id,
                    "faculty_id": ObjectId(faculty_id) if isinstance(faculty_id, str) else faculty_id,
                    "semester": semester,
                    "section": section,
                    "academic_year": default_academic_year,
                    "is_primary": True,
                    "created_at": datetime.utcnow()
                }

                try:
                    await db.subject_assignments.insert_one(assignment)
                    details["assignments_created"] [OK]= 1
                except Exception:
                    pass  # Skip duplicates

            details["subjects_processed"] [OK]= 1

        return {
            "success": True,
            "applied_at": datetime.utcnow(),
            "details": details
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": details
        }


async def migration_002_timetable_single_document(db):
    """Convert timetable to single-document schema."""
    from datetime import datetime
    from bson import ObjectId

    details = {
        "entries_processed": 0,
        "timetables_created": 0
    }

    try:
        # Check if migration already applied
        existing = await db.timetables.find_one({"schedule": {"$exists": True}})
        if existing:
            return {
                "success": True,
                "applied_at": datetime.utcnow(),
                "details": {**details, "message": "New schema already exists"}
            }

        # Group entries by semester-section-academic_year
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "semester": "$semester",
                        "section": "$section",
                        "academic_year": {"$ifNull": ["$academic_year", "2024-2025"]}
                    },
                    "entries": {"$push": "$$ROOT"},
                    "generated_at": {"$first": "$generated_at"},
                    "count": {"$sum": 1}
                }
            }
        ]

        groups = await db.timetables.aggregate(pipeline).to_list(length=None)

        new_timetables = []
        default_academic_year = "2024-2025"

        for group in groups:
            key = group["_id"]
            entries = group.get("entries", [])
            semester = key["semester"]
            section = key["section"]
            academic_year = key.get("academic_year", default_academic_year)

            # Build schedule
            schedule_by_day = {}
            for day_str in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]:
                schedule_by_day[day_str] = []

            for entry in entries:
                day_str = entry.get("day")
                slot = entry.get("slot")
                if day_str in schedule_by_day:
                    schedule_by_day[day_str].append({
                        "slot": slot,
                        "subject_id": entry.get("subject_id"),
                        "faculty_id": entry.get("faculty_id"),
                        "room": entry.get("room_number")
                    })
                    details["entries_processed"] [OK]= 1

            schedule = []
            for day_str, slots in schedule_by_day.items():
                schedule.append({
                    "day": day_str,
                    "slots": slots
                })

            new_timetable = {
                "_id": ObjectId(),
                "semester": semester,
                "section": section,
                "academic_year": academic_year,
                "version": 1,
                "is_active": True,
                "schedule": schedule,
                "created_by": "migration",
                "created_at": group.get("generated_at", datetime.utcnow()),
                "updated_at": datetime.utcnow()
            }

            new_timetables.append(new_timetable)
            details["timetables_created"] [OK]= 1

        if new_timetables:
            await db.timetables.insert_many(new_timetables)

        return {
            "success": True,
            "applied_at": datetime.utcnow(),
            "details": details
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": details
        }


MIGRATIONS = [
    ("001_subject_assignments", migration_001_subject_assignments),
    ("002_timetable_single_document", migration_002_timetable_single_document),
]


async def get_migration_status(db):
    """Get status of all migrations."""
    if "migrations" not in await db.list_collection_names():
        return {
            "applied": [],
            "pending": [name for name, _ in MIGRATIONS]
        }

    applied = []
    async for doc in db.migrations.find().sort("applied_at", 1):
        applied.append({
            "name": doc["name"],
            "applied_at": doc["applied_at"]
        })

    applied_names = set(doc["name"] for doc in applied)
    pending = [name for name, _ in MIGRATIONS if name not in applied_names]

    return {"applied": applied, "pending": pending}


async def run_all_migrations(db):
    """Run all pending migrations."""
    # Create migrations tracking collection
    if "migrations" not in await db.list_collection_names():
        await db.create_collection("migrations")
        await db.migrations.create_index([("name", 1)], unique=True)

    # Get applied migrations
    applied = set()
    async for doc in db.migrations.find():
        applied.add(doc["name"])

    # Run pending migrations
    for name, migration_func in MIGRATIONS:
        if name not in applied:
            print(f"Running migration: {name}")
            result = await migration_func(db)
            if result.get("success"):
                await db.migrations.insert_one({
                    "name": name,
                    "applied_at": result.get("applied_at"),
                    "details": result.get("details", {})
                })
                print(f"[OK] Migration {name} completed")
            else:
                print(f"[FAIL] Migration {name} failed: {result.get('error')}")
                raise Exception(f"Migration {name} failed")
        else:
            print(f"[SKIP] Migration {name} already applied, skipping")


async def status_command():
    """Show migration status."""
    db = await get_database()
    try:
        status = await get_migration_status(db)

        print("\n=== Migration Status ===\n")

        if status["applied"]:
            print("Applied migrations:")
            for m in status["applied"]:
                print(f"  [[OK]] {m['name']} - {m['applied_at']}")
        else:
            print("No migrations applied yet")

        if status["pending"]:
            print(f"\nPending migrations ({len(status['pending'])}):")
            for name in status["pending"]:
                print(f"  [ ] {name}")
        else:
            print("\nAll migrations up to date!")

        print()
    finally:
        from motor.motor_asyncio import AsyncIOMotorClient
        if hasattr(db, 'client'):
            db.client.close()


async def up_command():
    """Run pending migrations."""
    db = await get_database()
    try:
        # Show status before
        status_before = await get_migration_status(db)
        if status_before["pending"]:
            print(f"Running {len(status_before['pending'])} pending migration(s)...\n")
        else:
            print("No pending migrations. Database is up to date.\n")
            return

        # Run migrations
        await run_all_migrations(db)

        # Show status after
        print("\nVerifying migration status...\n")
        status_after = await get_migration_status(db)

        print(f"\n[OK] Migrations complete!")
        print(f"  Applied: {len(status_after['applied'])}")
        print(f"  Pending: {len(status_after['pending'])}")

    except Exception as e:
        print(f"\n[FAIL] Migration failed: {e}")
        sys.exit(1)
    finally:
        from motor.motor_asyncio import AsyncIOMotorClient
        if hasattr(db, 'client'):
            db.client.close()


async def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command>")
        print("\nCommands:")
        print("  status       - Show migration status")
        print("  up           - Run pending migrations")
        print("  init-indexes - Initialize database indexes")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        await status_command()
    elif command == "up":
        await up_command()
    elif command == "init-indexes":
        await init_indexes()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
