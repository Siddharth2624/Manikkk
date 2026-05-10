"""Database migrations for schema refactoring."""

from .migration_001_subject_assignments import migration_001_subject_assignments
from .migration_002_timetable_single_document import migration_002_timetable_single_document

MIGRATIONS = [
    ("001_subject_assignments", migration_001_subject_assignments),
    ("002_timetable_single_document", migration_002_timetable_single_document),
]


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
                print(f"Migration {name} completed successfully")
            else:
                print(f"Migration {name} failed: {result.get('error')}")
                raise Exception(f"Migration {name} failed")
        else:
            print(f"Migration {name} already applied, skipping")

    print("All migrations completed")


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
