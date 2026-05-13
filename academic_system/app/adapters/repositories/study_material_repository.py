"""MongoDB implementation of study material repository."""

from typing import List, Optional
from datetime import datetime, date
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.study_material import StudyMaterial, MaterialType
from app.domain.interfaces.repositories import IStudyMaterialRepository


class StudyMaterialRepository(IStudyMaterialRepository):
    """MongoDB implementation of IStudyMaterialRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.study_materials

    def _to_entity(self, document: dict) -> StudyMaterial:
        """Convert MongoDB document to StudyMaterial entity."""
        material_date = document.get("material_date") or document.get("upload_date") or date.today()
        if isinstance(material_date, str):
            material_date = date.fromisoformat(material_date[:10])
        elif isinstance(material_date, datetime):
            material_date = material_date.date()

        return StudyMaterial(
            id=str(document["_id"]),
            title=document["title"],
            description=document.get("description"),
            subject_id=document["subject_id"],
            semester=document["semester"],
            sections=document.get("sections", []),
            faculty_id=document["faculty_id"],
            material_url=document.get("material_url") or document.get("file_url", ""),
            material_date=material_date,
            access_count=document.get("access_count", document.get("download_count", 0)),
            tags=document.get("tags", []),
            is_public=document.get("is_public", True),
            created_at=document["created_at"],
            updated_at=document["updated_at"],
            material_type=MaterialType(document.get("material_type", MaterialType.LINK.value))
        )

    def _to_document(self, material: StudyMaterial) -> dict:
        """Convert StudyMaterial entity to MongoDB document."""
        return {
            "title": material.title,
            "description": material.description,
            "subject_id": material.subject_id,
            "semester": material.semester,
            "sections": material.sections,
            "faculty_id": material.faculty_id,
            "material_type": material.material_type.value,
            "material_url": material.material_url,
            "material_date": material.material_date.isoformat(),
            "access_count": material.access_count,
            "tags": material.tags,
            "is_public": material.is_public,
            "created_at": material.created_at,
            "updated_at": material.updated_at
        }

    async def find_by_id(self, material_id: str) -> Optional[StudyMaterial]:
        """Find study material by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(material_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_by_subject(
        self,
        subject_id: str,
        semester: Optional[int] = None,
        section: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> List[StudyMaterial]:
        """Find study materials for a subject."""
        query = {"subject_id": subject_id}
        if semester:
            query["semester"] = semester
        if faculty_id:
            query["faculty_id"] = faculty_id
        if section:
            query["$or"] = [
                {"sections": {"$size": 0}},
                {"sections": section}
            ]

        cursor = self.collection.find(query).sort([("material_date", -1), ("created_at", -1)])
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_faculty(self, faculty_id: str) -> List[StudyMaterial]:
        """Find study materials uploaded by a faculty."""
        cursor = self.collection.find({"faculty_id": faculty_id}).sort([("material_date", -1), ("created_at", -1)])
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_semester(
        self,
        semester: int,
        section: Optional[str] = None
    ) -> List[StudyMaterial]:
        """Find study materials for a semester."""
        query = {
            "semester": semester,
            "is_public": True
        }

        if section:
            query["$or"] = [
                {"sections": {"$size": 0}},
                {"sections": section}
            ]
        else:
            query["sections"] = {"$size": 0}

        cursor = self.collection.find(query).sort([("material_date", -1), ("created_at", -1)])
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def search(
        self,
        query: str,
        semester: Optional[int] = None,
        section: Optional[str] = None,
        faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[StudyMaterial]:
        """Search study materials by title, description, or tags."""
        search_query = {
            "is_public": True,
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$regex": query, "$options": "i"}}
            ]
        }

        if semester:
            search_query["semester"] = semester
        if faculty_id:
            search_query["faculty_id"] = faculty_id
        if subject_id:
            search_query["subject_id"] = subject_id
        if section:
            search_query["$and"] = [
                {
                    "$or": [
                        {"sections": {"$size": 0}},
                        {"sections": section}
                    ]
                }
            ]

        cursor = self.collection.find(search_query).sort([("material_date", -1), ("created_at", -1)]).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_entity(doc) for doc in documents]

    async def save(self, material: StudyMaterial) -> StudyMaterial:
        """Save or update study material."""
        material.updated_at = datetime.utcnow()

        if material.id:
            await self.collection.update_one(
                {"_id": ObjectId(material.id)},
                {"$set": self._to_document(material)}
            )
        else:
            result = await self.collection.insert_one(self._to_document(material))
            material.id = str(result.inserted_id)

        return material

    async def delete(self, material_id: str) -> bool:
        """Delete study material by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(material_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def increment_download_count(self, material_id: str) -> bool:
        """Increment access count for material."""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(material_id)},
                {"$inc": {"access_count": 1, "download_count": 1}}
            )
            return result.modified_count > 0
        except Exception:
            return False
