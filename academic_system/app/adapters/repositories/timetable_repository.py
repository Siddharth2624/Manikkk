"""MongoDB implementation of timetable repository - redesigned for single-document schema."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.timetable import (
    Timetable, TimetableSlot, DaySchedule, DayOfWeek
)


class TimetableRepository:
    """MongoDB implementation of Timetable repository.

    New schema: ONE document per semester-section.
    Supports versioning with is_active flag.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.timetables

    def _to_entity(self, document: dict) -> Timetable:
        """Convert MongoDB document to Timetable entity."""
        schedule = []
        for day_doc in document.get("schedule", []):
            slots = [
                TimetableSlot(
                    slot=slot_doc["slot"],
                    subject_id=slot_doc.get("subject_id"),
                    faculty_id=slot_doc.get("faculty_id"),
                    room=slot_doc.get("room")
                )
                for slot_doc in day_doc.get("slots", [])
            ]
            schedule.append(DaySchedule(
                day=DayOfWeek(day_doc["day"]),
                slots=slots
            ))

        return Timetable(
            id=str(document["_id"]),
            semester=document["semester"],
            section=document["section"],
            version=document["version"],
            is_active=document.get("is_active", True),
            schedule=schedule,
            created_by=document.get("created_by", ""),
            created_at=document.get("created_at", datetime.utcnow()),
            updated_at=document.get("updated_at", datetime.utcnow())
        )

    def _to_document(self, timetable: Timetable) -> dict:
        """Convert Timetable entity to MongoDB document."""
        schedule = []
        for day_schedule in timetable.schedule:
            slots = [
                {
                    "slot": slot.slot,
                    "subject_id": slot.subject_id,
                    "faculty_id": slot.faculty_id,
                    "room": slot.room
                }
                for slot in day_schedule.slots
            ]
            schedule.append({
                "day": day_schedule.day.value,
                "slots": slots
            })

        return {
            "semester": timetable.semester,
            "section": timetable.section,
            "version": timetable.version,
            "is_active": timetable.is_active,
            "schedule": schedule,
            "created_by": timetable.created_by,
            "created_at": timetable.created_at,
            "updated_at": timetable.updated_at
        }

    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str
    ) -> Optional[Timetable]:
        """Find active timetable by semester and section."""
        document = await self.collection.find_one({
            "semester": semester,
            "section": section,
            "is_active": True
        })
        return self._to_entity(document) if document else None

    async def find_active_by_semester(
        self,
        semester: int,
        exclude_section: Optional[str] = None
    ) -> List[Timetable]:
        """Find active timetables for a semester, optionally excluding one section."""
        query = {
            "semester": semester,
            "is_active": True
        }
        if exclude_section is not None:
            query["section"] = {"$ne": exclude_section}

        cursor = self.collection.find(query).sort("section", 1)
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_id(self, timetable_id: str) -> Optional[Timetable]:
        """Find timetable by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(timetable_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_all_versions(
        self,
        semester: int,
        section: str
    ) -> List[Timetable]:
        """Find all versions of a timetable (including inactive)."""
        cursor = self.collection.find({
            "semester": semester,
            "section": section
        }).sort("version", -1)

        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def get_latest_version(
        self,
        semester: int,
        section: str
    ) -> Optional[Timetable]:
        """Get the latest version (highest version number) regardless of is_active."""
        document = await self.collection.find_one({
            "semester": semester,
            "section": section
        }, sort=[("version", -1)])
        return self._to_entity(document) if document else None

    async def find_by_faculty(
        self,
        faculty_id: str
    ) -> List[Dict[str, Any]]:
        """Find all timetable entries for a faculty member.

        Returns aggregated data with subject and timetable info.
        """
        pipeline = [
            {"$match": {"is_active": True}},
            {"$unwind": "$schedule"},
            {"$unwind": "$schedule.slots"},
            {"$match": {"schedule.slots.faculty_id": faculty_id}},
            {
                "$project": {
                    "semester": 1,
                    "section": 1,
                    "day": "$schedule.day",
                    "slot": "$schedule.slots.slot",
                    "subject_id": "$schedule.slots.subject_id",
                    "faculty_id": "$schedule.slots.faculty_id",
                    "room": "$schedule.slots.room"
                }
            }
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        return results

    async def save(self, timetable: Timetable) -> Timetable:
        """Save or update timetable.

        If timetable has an ID, updates the existing document.
        Otherwise, creates a new document (new version).
        """
        timetable.updated_at = datetime.utcnow()

        if timetable.id:
            await self.collection.update_one(
                {"_id": ObjectId(timetable.id)},
                {"$set": self._to_document(timetable)}
            )
        else:
            # Check if this is a new version - deactivate existing
            await self.deactivate_active(
                timetable.semester,
                timetable.section
            )

            # Get next version number
            latest = await self.get_latest_version(
                timetable.semester,
                timetable.section
            )
            timetable.version = (latest.version + 1) if latest else 1

            result = await self.collection.insert_one(self._to_document(timetable))
            timetable.id = str(result.inserted_id)

        return timetable

    async def deactivate_active(
        self,
        semester: int,
        section: str
    ) -> int:
        """Deactivate all timetables for a semester-section.

        Returns the number of documents updated.
        """
        result = await self.collection.update_many(
            {
                "semester": semester,
                "section": section,
                "is_active": True
            },
            {"$set": {"is_active": False}}
        )
        return result.modified_count

    async def activate_version(
        self,
        timetable_id: str,
        semester: int,
        section: str
    ) -> bool:
        """Activate a specific timetable version and deactivate others."""
        # First deactivate all
        await self.deactivate_active(semester, section)

        # Then activate the specified one
        result = await self.collection.update_one(
            {"_id": ObjectId(timetable_id)},
            {"$set": {"is_active": True}}
        )
        return result.modified_count > 0

    async def delete_by_semester_and_section(
        self,
        semester: int,
        section: str
    ) -> int:
        """Delete all timetables for a semester and section.

        Returns the number of documents deleted.
        """
        result = await self.collection.delete_many({
            "semester": semester,
            "section": section
        })
        return result.deleted_count

    async def delete(self, timetable_id: str) -> bool:
        """Delete a specific timetable by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(timetable_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def find_conflicts(
        self,
        semester: int,
        section: str,
        day: DayOfWeek,
        slot: int
    ) -> List[Dict[str, Any]]:
        """Find entries at the same day and slot.

        Returns list of conflicting entries with subject_id, faculty_id, room.
        """
        document = await self.collection.find_one({
            "semester": semester,
            "section": section,
            "is_active": True
        })

        if not document:
            return []

        conflicts = []
        for day_schedule in document.get("schedule", []):
            if day_schedule["day"] == day.value:
                for slot_data in day_schedule.get("slots", []):
                    if slot_data["slot"] == slot and slot_data.get("subject_id"):
                        conflicts.append({
                            "day": day.value,
                            "slot": slot,
                            "subject_id": slot_data.get("subject_id"),
                            "faculty_id": slot_data.get("faculty_id"),
                            "room": slot_data.get("room")
                        })

        return conflicts

    async def find_slot_conflicts_for_faculty(
        self,
        faculty_id: str,
        day: DayOfWeek,
        slot: int,
        exclude_timetable_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find if faculty is already booked at this day/slot.

        Optional exclude_timetable_id to skip when checking current timetable.
        """
        query = {
            "is_active": True,
            "schedule": {
                "$elemMatch": {
                    "day": day.value,
                    "slots": {
                        "$elemMatch": {
                            "slot": slot,
                            "faculty_id": faculty_id
                        }
                    }
                }
            }
        }

        if exclude_timetable_id:
            query["_id"] = {"$ne": ObjectId(exclude_timetable_id)}

        cursor = self.collection.find(query)
        documents = await cursor.to_list(length=None)

        results = []
        for doc in documents:
            results.append({
                "timetable_id": str(doc["_id"]),
                "semester": doc["semester"],
                "section": doc["section"]
            })

        return results

    async def find_slot_conflicts_for_room(
        self,
        room: str,
        day: DayOfWeek,
        slot: int,
        exclude_timetable_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find if room is already booked at this day/slot."""
        query = {
            "is_active": True,
            "schedule": {
                "$elemMatch": {
                    "day": day.value,
                    "slots": {
                        "$elemMatch": {
                            "slot": slot,
                            "room": room
                        }
                    }
                }
            }
        }

        if exclude_timetable_id:
            query["_id"] = {"$ne": ObjectId(exclude_timetable_id)}

        cursor = self.collection.find(query)
        documents = await cursor.to_list(length=None)

        results = []
        for doc in documents:
            results.append({
                "timetable_id": str(doc["_id"]),
                "semester": doc["semester"],
                "section": doc["section"]
            })

        return results

    async def get_all_semesters_sections(self) -> List[Dict[str, Any]]:
        """Get all semester-section combinations with active timetables."""
        pipeline = [
            {"$match": {"is_active": True}},
            {
                "$group": {
                    "_id": {
                        "semester": "$semester",
                        "section": "$section"
                    },
                    "version": {"$first": "$version"},
                    "created_at": {"$first": "$created_at"},
                    "updated_at": {"$first": "$updated_at"}
                }
            },
            {"$sort": {"_id.semester": 1, "_id.section": 1}}
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)

        return [
            {
                "semester": r["_id"]["semester"],
                "section": r["_id"]["section"],
                "version": r["version"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            }
            for r in results
        ]

    async def get_with_subject_details(
        self,
        semester: int,
        section: str
    ) -> Optional[Dict[str, Any]]:
        """Get timetable with subject and faculty details joined."""
        pipeline = [
            {
                "$match": {
                    "semester": semester,
                    "section": section,
                    "is_active": True
                }
            }
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=1)

        if not results:
            return None

        doc = results[0]

        # Extract all unique subject_ids and faculty_ids from the schedule
        subject_ids = []
        faculty_ids = []
        for day in doc.get("schedule", []):
            for slot in day.get("slots", []):
                if slot.get("subject_id"):
                    subject_ids.append(slot["subject_id"])
                if slot.get("faculty_id"):
                    faculty_ids.append(slot["faculty_id"])

        # Fetch subjects
        subjects_map = {}
        if subject_ids:
            subject_docs = await self.db.subjects.find({
                "_id": {"$in": [ObjectId(sid) for sid in subject_ids]}
            }).to_list(length=None)
            subjects_map = {
                str(s["_id"]): {"code": s["code"], "name": s["name"]}
                for s in subject_docs
            }

        # Fetch faculty
        faculty_map = {}
        if faculty_ids:
            faculty_docs = await self.db.users.find({
                "_id": {"$in": [ObjectId(fid) for fid in faculty_ids]}
            }).to_list(length=None)
            faculty_map = {
                str(f["_id"]): {"name": f.get("name") or f.get("full_name", ""), "email": f.get("email", "")}
                for f in faculty_docs
            }

        # Enrich schedule
        enriched_schedule = []
        for day_doc in doc.get("schedule", []):
            enriched_slots = []
            for slot in day_doc.get("slots", []):
                enriched_slot = {
                    "slot": slot["slot"],
                    "subject_id": slot.get("subject_id"),
                    "faculty_id": slot.get("faculty_id"),
                    "room": slot.get("room")
                }

                if slot.get("subject_id") and str(slot["subject_id"]) in subjects_map:
                    enriched_slot["subject"] = subjects_map[str(slot["subject_id"])]

                if slot.get("faculty_id") and str(slot["faculty_id"]) in faculty_map:
                    enriched_slot["faculty"] = faculty_map[str(slot["faculty_id"])]

                enriched_slots.append(enriched_slot)

            enriched_schedule.append({
                "day": day_doc["day"],
                "slots": enriched_slots
            })

        return {
            "id": str(doc["_id"]),
            "semester": doc["semester"],
            "section": doc["section"],
            "version": doc["version"],
            "is_active": doc.get("is_active", False),
            "schedule": enriched_schedule,
            "created_at": doc["created_at"],
            "updated_at": doc["updated_at"]
        }

    async def exists(self, semester: int, section: str) -> bool:
        """Check if any timetable exists for semester-section."""
        count = await self.collection.count_documents({
            "semester": semester,
            "section": section
        })
        return count > 0

    async def has_active(self, semester: int, section: str) -> bool:
        """Check if active timetable exists for semester-section."""
        count = await self.collection.count_documents({
            "semester": semester,
            "section": section,
            "is_active": True
        })
        return count > 0
