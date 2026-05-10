"""Migration 001: Create subject_assignments collection.

This migration creates the new subject_assignments collection by extracting
data from the denormalized subjects collection.

Before: subjects had sections array and faculty_id
After: subjects only have catalog data; assignments are in subject_assignments
"""

from datetime import datetime
from typing import Dict, Any
from bson import ObjectId


async def migration_001_subject_assignments(db) -> Dict[str, Any]:
    """
    Create subject_assignments collection from subjects collection.

    Steps:
    1. Check if subjects collection has sections/faculty_id fields
    2. For each subject with sections, create assignment records
    3. DO NOT remove fields from subjects yet (done in later migration)
    """
    details = {
        "subjects_processed": 0,
        "assignments_created": 0,
        "subjects_without_assignments": 0
    }

    try:
        # Check if subject_assignments already exists and has data
        if "subject_assignments" in await db.list_collection_names():
            count = await db.subject_assignments.count_documents({})
            if count > 0:
                return {
                    "success": True,
                    "applied_at": datetime.utcnow(),
                    "details": {**details, "message": "Collection already exists with data"}
                }

        # Create collection with indexes
        await db.create_collection("subject_assignments")

        # Create unique index on faculty-subject-semester-section-academic_year
        await db.subject_assignments.create_index([
            ("faculty_id", 1),
            ("subject_id", 1),
            ("semester", 1),
            ("section", 1),
            ("academic_year", 1)
        ], unique=True)

        # Migrate data from subjects collection
        default_academic_year = "2024-2025"

        async for subject_doc in db.subjects.find({
            "faculty_id": {"$exists": True},
            "sections": {"$exists": True, "$ne": []}
        }):
            subject_id = subject_doc["_id"]
            faculty_id = subject_doc.get("faculty_id")
            sections = subject_doc.get("sections", [])
            semester = subject_doc.get("semester")

            if not faculty_id or not sections:
                details["subjects_without_assignments"] += 1
                continue

            # Create assignment for each section
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
                    details["assignments_created"] += 1
                except Exception as e:
                    # Duplicate or error, log but continue
                    details[f"error_{subject_id}_{section}"] = str(e)

            details["subjects_processed"] += 1

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


async def rollback_001_subject_assignments(db):
    """Rollback migration 001 - drop subject_assignments collection."""
    await db.subject_assignments.drop()
    return {"success": True, "rolled_back_at": datetime.utcnow()}
