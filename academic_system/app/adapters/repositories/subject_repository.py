"""MongoDB implementation of subject repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.subject import Subject, SubjectType
from app.domain.interfaces.repositories import ISubjectRepository


class SubjectRepository(ISubjectRepository):
    """MongoDB implementation of ISubjectRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.subjects

    def _to_entity(self, document: dict) -> Subject:
        """Convert MongoDB document to Subject entity."""
        return Subject(
            id=str(document["_id"]),
            code=document["code"],
            name=document["name"],
            semester=document["semester"],
            subject_type=SubjectType(document["subject_type"]),
            credits=document["credits"],
            classes_per_week=document["classes_per_week"],
            description=document.get("description"),
            syllabus=document.get("syllabus"),
            created_at=document["created_at"],
            updated_at=document["updated_at"]
        )

    def _to_document(self, subject: Subject) -> dict:
        """Convert Subject entity to MongoDB document."""
        return {
            "code": subject.code.upper(),
            "name": subject.name,
            "semester": subject.semester,
            "subject_type": subject.subject_type.value,
            "credits": subject.credits,
            "classes_per_week": subject.classes_per_week,
            "description": subject.description,
            "syllabus": subject.syllabus,
            "created_at": subject.created_at,
            "updated_at": subject.updated_at
        }

    async def find_by_id(self, subject_id: str) -> Optional[Subject]:
        """Find subject by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(subject_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_by_code(self, code: str) -> Optional[Subject]:
        """Find subject by code."""
        document = await self.collection.find_one({"code": code.upper()})
        return self._to_entity(document) if document else None

    async def find_all(
        self,
        semester: Optional[int] = None,
        subject_type: Optional[SubjectType] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Subject]:
        """Find subjects with optional filters."""
        query = {}
        if semester:
            query["semester"] = semester
        if subject_type:
            query["subject_type"] = subject_type.value

        cursor = self.collection.find(query).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_entity(doc) for doc in documents]

    async def save(self, subject: Subject) -> Subject:
        """Save or update subject."""
        from datetime import datetime

        subject.updated_at = datetime.utcnow()

        if subject.id:
            await self.collection.update_one(
                {"_id": ObjectId(subject.id)},
                {"$set": self._to_document(subject)}
            )
        else:
            result = await self.collection.insert_one(self._to_document(subject))
            subject.id = str(result.inserted_id)

        return subject

    async def delete(self, subject_id: str) -> bool:
        """Delete subject by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(subject_id)})
            return result.deleted_count > 0
        except Exception:
            return False