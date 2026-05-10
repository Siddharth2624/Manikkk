"""MongoDB implementation of semester repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.semester import Semester, SemesterStatus
from app.domain.interfaces.repositories import ISemesterRepository


class SemesterRepository(ISemesterRepository):
    """MongoDB implementation of ISemesterRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.semesters

    def _to_entity(self, document: dict) -> Semester:
        """Convert MongoDB document to Semester entity."""
        return Semester(
            id=str(document["_id"]),
            semester_number=document["semester_number"],
            branch=document["branch"],
            status=SemesterStatus(document["status"]),
            start_date=document.get("start_date"),
            end_date=document.get("end_date"),
            sections=document.get("sections", []),
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    def _to_document(self, semester: Semester) -> dict:
        """Convert Semester entity to MongoDB document."""
        return {
            "semester_number": semester.semester_number,
            "branch": semester.branch,
            "status": semester.status.value,
            "start_date": semester.start_date,
            "end_date": semester.end_date,
            "sections": semester.sections,
            "created_at": semester.created_at,
            "updated_at": semester.updated_at
        }

    async def find_by_id(self, semester_id: str) -> Optional[Semester]:
        """Find semester by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(semester_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_by_number(
        self,
        semester_number: int
    ) -> Optional[Semester]:
        """Find semester by number."""
        document = await self.collection.find_one({
            "semester_number": semester_number
        })
        return self._to_entity(document) if document else None

    async def find_all(
        self,
        status: Optional[SemesterStatus] = None,
        branch: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Semester]:
        """Find all semesters with optional filters."""
        query = {}
        if status:
            query["status"] = status.value
        if branch:
            query["branch"] = branch

        cursor = self.collection.find(query).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_entity(doc) for doc in documents]

    async def get_active_semester(self) -> Optional[Semester]:
        """Get currently active semester."""
        document = await self.collection.find_one({
            "status": SemesterStatus.ONGOING.value
        })
        return self._to_entity(document) if document else None

    async def save(self, semester: Semester) -> Semester:
        """Save or update semester."""
        from datetime import datetime

        semester.updated_at = datetime.utcnow()

        if semester.id:
            await self.collection.update_one(
                {"_id": ObjectId(semester.id)},
                {"$set": self._to_document(semester)}
            )
        else:
            result = await self.collection.insert_one(self._to_document(semester))
            semester.id = str(result.inserted_id)

        return semester

    async def delete(self, semester_id: str) -> bool:
        """Delete semester by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(semester_id)})
            return result.deleted_count > 0
        except Exception:
            return False
