"""Migration 002: Redesign timetable to single-document schema.

This migration converts timetable entries from multiple documents per timetable
to a single document per semester-section with versioning support.

Before: One document per entry (semester, section, day, slot)
After: One document per semester-section-academic_year with versioning
"""

from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId


async def migration_002_timetable_single_document(db) -> Dict[str, Any]:
    """
    Convert timetable entries to single-document schema.

    Steps:
    1. Create backup of existing timetables collection
    2. Group entries by semester-section-academic_year
    3. Create new single-document timetables
    4. Update indexes
    """
    details = {
        "entries_processed": 0,
        "timetables_created": 0,
        "backup_created": False
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

        # Create backup
        backup_collection_name = "timetables_backup"
        if backup_collection_name not in await db.list_collection_names():
            # Aggregate all entries and save to backup
            pipeline = [{"$match": {}}]
            entries = await db.timetables.aggregate(pipeline).to_list(length=None)

            if entries:
                await db.create_collection(backup_collection_name)
                if entries:
                    await db[backup_collection_name].insert_many(entries)
                details["backup_created"] = True

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

        # Create new timetable documents
        default_academic_year = "2024-2025"
        new_timetables = []

        for group in groups:
            key = group["_id"]
            entries = group["entries"]
            semester = key["semester"]
            section = key["section"]
            academic_year = key.get("academic_year", default_academic_year)

            # Build schedule structure
            from app.domain.entities.timetable import DayOfWeek

            schedule_by_day = {}
            for day in DayOfWeek:
                schedule_by_day[day] = []

            # Process entries
            for entry in entries:
                day_str = entry.get("day")
                slot = entry.get("slot")

                try:
                    day_enum = DayOfWeek(day_str)
                except ValueError:
                    continue

                from app.domain.entities.timetable import TimetableSlot
                slot_obj = TimetableSlot(
                    slot=slot,
                    subject_id=entry.get("subject_id"),
                    faculty_id=entry.get("faculty_id"),
                    room=entry.get("room_number")
                )
                schedule_by_day[day_enum].append(slot_obj)
                details["entries_processed"] += 1

            # Create schedule list
            from app.domain.entities.timetable import DaySchedule
            schedule = []
            for day, slots in schedule_by_day.items():
                schedule.append(DaySchedule(day=day, slots=slots))

            # Create new timetable document
            new_timetable = {
                "_id": ObjectId(),
                "semester": semester,
                "section": section,
                "academic_year": academic_year,
                "version": 1,
                "is_active": True,
                "schedule": [
                    {
                        "day": ds.day.value,
                        "slots": [
                            {
                                "slot": s.slot,
                                "subject_id": s.subject_id,
                                "faculty_id": s.faculty_id,
                                "room": s.room
                            }
                            for s in ds.slots
                        ]
                    }
                    for ds in schedule
                ],
                "created_by": "migration",
                "created_at": group.get("generated_at", datetime.utcnow()),
                "updated_at": datetime.utcnow()
            }

            new_timetables.append(new_timetable)
            details["timetables_created"] += 1

        # Insert new timetables
        if new_timetables:
            await db.timetables.insert_many(new_timetables)

        # Drop old entries (keep only new schema documents)
        await db.timetables.delete_many({
            "schedule": {"$exists": False}
        })

        # Create new indexes
        await db.timetables.create_index([
            ("semester", 1),
            ("section", 1),
            ("academic_year", 1),
            ("is_active", -1)
        ])

        await db.timetables.create_index([
            ("semester", 1),
            ("section", 1),
            ("academic_year", 1),
            ("version", -1)
        ])

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


async def rollback_002_timetable_single_document(db):
    """Rollback migration 002 - restore from backup if exists."""
    if "timetables_backup" in await db.list_collection_names():
        # Drop current collection
        await db.timetables.drop()
        # Rename backup
        await db.timetables_backup.rename("timetables")
        return {"success": True, "rolled_back_at": datetime.utcnow()}
    return {"success": False, "error": "No backup found"}
