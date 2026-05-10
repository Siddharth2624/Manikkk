"""MongoDB implementation of admin override repository."""

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.admin_override_log import (
    AdminOverrideLog, OverrideSlot, OverrideType,
    DayOfWeek, OverrideAction
)
from app.domain.interfaces.repositories import IAdminOverrideRepository


class AdminOverrideRepository(IAdminOverrideRepository):
    """MongoDB implementation of admin override repository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.admin_override_log

    def _to_entity(self, document: dict) -> AdminOverrideLog:
        """Convert MongoDB document to AdminOverrideLog entity."""
        slots = [
            OverrideSlot(
                day=DayOfWeek(s["day"]),
                slot=s["slot"],
                action=OverrideAction(s["action"])
            )
            for s in document.get("slots", [])
        ]

        return AdminOverrideLog(
            id=str(document["_id"]),
            admin_id=str(document["admin_id"]),
            faculty_id=str(document["faculty_id"]),
            subject_id=str(document["subject_id"]),
            semester=document["semester"],
            section=document["section"],
            override_type=OverrideType(document["override_type"]),
            applied=document.get("applied", False),
            slots=slots,
            timestamp=document["timestamp"]
        )

    def _to_document(self, override: AdminOverrideLog) -> dict:
        """Convert AdminOverrideLog entity to MongoDB document."""
        return {
            "admin_id": ObjectId(override.admin_id),
            "faculty_id": ObjectId(override.faculty_id),
            "subject_id": ObjectId(override.subject_id),
            "semester": override.semester,
            "section": override.section,
            "override_type": override.override_type.value,
            "applied": override.applied,
            "slots": [
                {"day": s.day.value, "slot": s.slot, "action": s.action.value}
                for s in override.slots
            ],
            "timestamp": override.timestamp
        }

    async def save(self, override: AdminOverrideLog) -> AdminOverrideLog:
        """Save override log entry."""
        doc = self._to_document(override)

        if override.id:
            await self.collection.update_one(
                {"_id": ObjectId(override.id)},
                {"$set": doc}
            )
        else:
            result = await self.collection.insert_one(doc)
            override.id = str(result.inserted_id)

        return override

    async def find_by_id(self, override_id: str) -> Optional[AdminOverrideLog]:
        """Find override by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(override_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_applicable(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str
    ) -> List[AdminOverrideLog]:
        """Find all applicable overrides (persistent + all one-time for this section).

        Note: One-time overrides are now included regardless of applied status.
        They remain applicable until explicitly deleted by the admin.
        """
        import logging
        logger = logging.getLogger(__name__)

        # FIXED: Include all one_time overrides, not just applied=False
        # This allows admins to create overrides and regenerate timetables
        # without the overrides being "used up"
        query = {
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section,
            "$or": [
                {"override_type": "persistent"},
                {"override_type": "one_time"}  # ALL one-time overrides, not just applied=False
            ]
        }
        logger.info(f"[DEBUG OVERRIDES] Query: {query}")

        cursor = self.collection.find(query).sort("timestamp", 1)
        documents = await cursor.to_list(length=None)

        logger.info(f"[DEBUG OVERRIDES] Found {len(documents)} applicable overrides")

        return [self._to_entity(doc) for doc in documents]

    async def find_audit_log(
        self, faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None
    ) -> List[AdminOverrideLog]:
        """Find overrides for audit log view."""
        query = {}
        if faculty_id:
            query["faculty_id"] = ObjectId(faculty_id)
        if subject_id:
            query["subject_id"] = ObjectId(subject_id)
        if from_date:
            query["timestamp"] = {"$gte": from_date}

        cursor = self.collection.find(query).sort("timestamp", -1)
        documents = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in documents]

    async def mark_one_time_applied(
        self, semester: int, section: str
    ) -> int:
        """Mark one-time overrides as applied after generation."""
        result = await self.collection.update_many(
            {
                "semester": semester,
                "section": section,
                "override_type": "one_time",
                "applied": False
            },
            {"$set": {"applied": True}}
        )

        return result.modified_count

    async def delete(self, override_id: str) -> bool:
        """Delete override by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(override_id)})
            return result.deleted_count > 0
        except Exception:
            return False
