"""Migration 003: Create faculty availability collection for existing assignments.

This migration creates faculty_availability records for all existing
subject_assignments to support the faculty availability feature.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Dict, Any


async def upgrade(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """
    Create faculty availability records for existing subject assignments.

    For each existing subject_assignment, create a corresponding
    faculty_availability record with empty available_slots.
    Faculty will then populate their availability through the UI.

    Returns:
        Dict with migration status and details
    """
    details = {
        "assignments_processed": 0,
        "availability_created": 0,
        "availability_skipped": 0,
        "errors": []
    }

    try:
        # Check if faculty_availability collection already exists
        collections = await db.list_collection_names()
        if "faculty_availability" not in collections:
            # Create collection with unique index
            await db.create_collection("faculty_availability")

            # Create unique index on faculty-subject-semester-section-academic_year
            await db.faculty_availability.create_index([
                ("faculty_id", 1),
                ("subject_id", 1),
                ("semester", 1),
                ("section", 1),
                ("academic_year", 1)
            ], unique=True)

            # Create index for faculty lookup
            await db.faculty_availability.create_index([
                ("faculty_id", 1),
                ("academic_year", 1)
            ])

        # Process all existing subject assignments
        async for assignment in db.subject_assignments.find({}):
            details["assignments_processed"] += 1

            faculty_id = assignment.get("faculty_id")
            subject_id = assignment.get("subject_id")
            semester = assignment.get("semester")
            section = assignment.get("section")
            academic_year = assignment.get("academic_year", "2024-2025")

            # Check if availability record already exists
            existing = await db.faculty_availability.find_one({
                "faculty_id": faculty_id,
                "subject_id": subject_id,
                "semester": semester,
                "section": section,
                "academic_year": academic_year
            })

            if existing:
                details["availability_skipped"] += 1
                continue

            # Create new availability record with empty slots
            now = datetime.utcnow()
            availability_record = {
                "faculty_id": faculty_id,
                "subject_id": subject_id,
                "semester": semester,
                "section": section,
                "academic_year": academic_year,
                "available_slots": [],  # Empty - faculty to populate
                "created_at": now,
                "updated_at": now
            }

            try:
                await db.faculty_availability.insert_one(availability_record)
                details["availability_created"] += 1
            except Exception as e:
                details["errors"].append({
                    "assignment_id": str(assignment.get("_id")),
                    "error": str(e)
                })

        return {
            "success": True,
            "applied_at": datetime.utcnow().isoformat(),
            "details": details,
            "message": (
                f"Migration 003 complete: "
                f"Created {details['availability_created']} records, "
                f"skipped {details['availability_skipped']}, "
                f"processed {details['assignments_processed']} assignments"
            )
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": details,
            "applied_at": datetime.utcnow().isoformat()
        }


async def downgrade(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """
    Rollback migration 003 - drop faculty_availability collection.

    WARNING: This will permanently delete all faculty availability data.
    """
    try:
        # Check if collection exists
        collections = await db.list_collection_names()
        if "faculty_availability" in collections:
            await db.faculty_availability.drop()
            return {
                "success": True,
                "rolled_back_at": datetime.utcnow().isoformat(),
                "message": "Migration 003 rollback complete: faculty_availability collection dropped"
            }
        else:
            return {
                "success": True,
                "rolled_back_at": datetime.utcnow().isoformat(),
                "message": "Migration 003 rollback: faculty_availability collection did not exist"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rolled_back_at": datetime.utcnow().isoformat()
        }
