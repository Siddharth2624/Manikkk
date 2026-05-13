"""MongoDB implementation of faculty availability repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClientSession
from datetime import datetime

from app.domain.entities.faculty_availability import FacultyAvailability, AvailableSlot, DayOfWeek
from app.domain.interfaces.repositories import IFacultyAvailabilityRepository


class FacultyAvailabilityRepository(IFacultyAvailabilityRepository):
    """MongoDB implementation of faculty availability repository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.faculty_availability

    def _to_entity(self, document: dict) -> FacultyAvailability:
        """Convert MongoDB document to FacultyAvailability entity."""
        slots = [
            AvailableSlot(
                day=DayOfWeek(s["day"]),
                slot=s["slot"]
            )
            for s in document.get("available_slots", [])
        ]

        return FacultyAvailability(
            id=str(document["_id"]),
            faculty_id=str(document["faculty_id"]),
            subject_id=str(document["subject_id"]),
            semester=document["semester"],
            section=document["section"],
            available_slots=slots,
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    def _to_document(self, availability: FacultyAvailability) -> dict:
        """Convert FacultyAvailability entity to MongoDB document."""
        return {
            "faculty_id": ObjectId(availability.faculty_id),
            "subject_id": ObjectId(availability.subject_id),
            "semester": availability.semester,
            "section": availability.section,
            "available_slots": [
                {"day": s.day.value, "slot": s.slot} for s in availability.available_slots
            ],
            "created_at": availability.created_at,
            "updated_at": availability.updated_at
        }

    async def save(
        self, availability: FacultyAvailability,
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> FacultyAvailability:
        """Save or update availability record."""
        doc = self._to_document(availability)

        if availability.id:
            # Update existing
            await self.collection.update_one(
                {"_id": ObjectId(availability.id)},
                {"$set": doc},
                session=session
            )
        else:
            # Insert new
            result = await self.collection.insert_one(doc, session=session)
            availability.id = str(result.inserted_id)

        return availability

    async def find(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str
    ) -> Optional[FacultyAvailability]:
        """Find availability by unique key."""
        document = await self.collection.find_one({
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section
        })

        return self._to_entity(document) if document else None

    async def find_by_faculty(
        self, faculty_id: str
    ) -> List[FacultyAvailability]:
        """Find all availability for a faculty member."""
        query = {"faculty_id": ObjectId(faculty_id)}

        cursor = self.collection.find(query).sort("semester", 1)
        documents = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in documents]

    async def find_by_faculty_and_subject(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str
    ) -> Optional[FacultyAvailability]:
        """Find availability for a specific faculty subject assignment."""
        return await self.find(
            faculty_id=faculty_id,
            subject_id=subject_id,
            semester=semester,
            section=section
        )

    async def update(self, availability: FacultyAvailability) -> FacultyAvailability:
        """Update existing availability record."""
        availability.updated_at = datetime.utcnow()
        doc = self._to_document(availability)

        await self.collection.update_one(
            {"_id": ObjectId(availability.id)},
            {"$set": doc}
        )

        return availability

    async def delete(
        self, faculty_id: str, subject_id: str,
        semester: int, section: str
    ) -> bool:
        """Delete availability record."""
        result = await self.collection.delete_one({
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section
        })

        return result.deleted_count > 0

    async def find_by_semester_and_section(
        self, semester: int, section: str
    ) -> List[FacultyAvailability]:
        """Find all availability records for a semester and section (across all faculty)."""
        query = {"semester": semester, "section": section}
        cursor = self.collection.find(query)
        documents = await cursor.to_list(length=None)

        return [self._to_entity(doc) for doc in documents]
