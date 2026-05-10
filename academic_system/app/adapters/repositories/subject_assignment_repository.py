"""MongoDB implementation of subject assignment repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.subject_assignment import SubjectAssignment
from app.domain.interfaces.repositories import ISubjectAssignmentRepository


class SubjectAssignmentRepository(ISubjectAssignmentRepository):
    """MongoDB implementation of ISubjectAssignmentRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.subject_assignments

    def _to_entity(self, document: dict) -> SubjectAssignment:
        """Convert MongoDB document to SubjectAssignment entity."""
        return SubjectAssignment(
            id=str(document["_id"]),
            subject_id=str(document["subject_id"]),
            semester=document["semester"],
            section=document["section"],
            faculty_id=str(document["faculty_id"]),
            is_primary=document.get("is_primary", True),
            created_at=document["created_at"]
        )

    def _to_document(self, assignment: SubjectAssignment) -> dict:
        """Convert SubjectAssignment entity to MongoDB document."""
        return {
            "subject_id": ObjectId(assignment.subject_id),
            "semester": assignment.semester,
            "section": assignment.section,
            "faculty_id": ObjectId(assignment.faculty_id),
            "is_primary": assignment.is_primary,
            "created_at": assignment.created_at
        }

    async def save(self, assignment: SubjectAssignment) -> SubjectAssignment:
        """Save or update subject assignment."""
        if assignment.id:
            await self.collection.update_one(
                {"_id": ObjectId(assignment.id)},
                {"$set": self._to_document(assignment)}
            )
        else:
            result = await self.collection.insert_one(self._to_document(assignment))
            assignment.id = str(result.inserted_id)

        return assignment

    async def find_by_id(self, assignment_id: str) -> Optional[SubjectAssignment]:
        """Find assignment by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(assignment_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_faculty_assignment(
        self,
        faculty_id: str,
        subject_id: str,
        semester: int,
        section: str
    ) -> Optional[SubjectAssignment]:
        """Find if faculty is assigned to specific subject/semester/section."""
        query = {
            "faculty_id": ObjectId(faculty_id),
            "subject_id": ObjectId(subject_id),
            "semester": semester,
            "section": section
        }

        document = await self.collection.find_one(query)
        return self._to_entity(document) if document else None

    async def find_by_semester_and_section(
        self,
        semester: int,
        section: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a semester and section."""
        cursor = self.collection.find({
            "semester": semester,
            "section": section
        }).sort("subject_id", 1)

        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_faculty(
        self,
        faculty_id: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a faculty member."""
        query = {"faculty_id": ObjectId(faculty_id)}

        cursor = self.collection.find(query).sort("semester", 1)
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_subject(
        self,
        subject_id: str
    ) -> List[SubjectAssignment]:
        """Find all assignments for a subject."""
        query = {"subject_id": ObjectId(subject_id)}

        cursor = self.collection.find(query).sort([("semester", 1), ("section", 1)])
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def delete(self, assignment_id: str) -> bool:
        """Delete assignment by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(assignment_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def find_all(
        self,
        semester: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[SubjectAssignment]:
        """Find all assignments with optional filters."""
        query = {}
        if semester is not None:
            query["semester"] = semester
        if section is not None:
            query["section"] = section

        cursor = self.collection.find(query).sort([
            ("semester", 1),
            ("section", 1),
            ("subject_id", 1)
        ])
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_faculty_and_semester(
        self,
        faculty_id: str,
        semester: int
    ) -> List[SubjectAssignment]:
        """Find all assignments for a faculty member in a specific semester."""
        query = {
            "faculty_id": ObjectId(faculty_id),
            "semester": semester
        }

        cursor = self.collection.find(query)
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def get_distinct_sections(
        self,
        semester: int
    ) -> List[str]:
        """Get all distinct sections for a semester."""
        sections = await self.collection.distinct(
            "section",
            {"semester": semester}
        )
        return sections if sections else []
