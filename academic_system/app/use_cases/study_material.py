"""Study material use cases."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import date, datetime

from bson import ObjectId

from app.domain.entities.request_context import RequestContext
from app.domain.entities.study_material import StudyMaterial, MaterialType
from app.domain.exceptions import AuthorizationError, ValidationError
from app.domain.interfaces.repositories import (
    IStudyMaterialRepository,
    ISubjectRepository,
    ISubjectAssignmentRepository,
)


@dataclass
class UploadMaterialRequest:
    """Request to create a link-based study material."""
    title: str
    description: Optional[str]
    subject_id: str
    semester: int
    sections: List[str]
    faculty_id: str
    material_url: str
    material_date: date
    tags: List[str]
    is_public: bool = True


@dataclass
class SearchMaterialRequest:
    """Request to search study materials."""
    query: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None
    subject_id: Optional[str] = None
    faculty_id: Optional[str] = None


class StudyMaterialUseCase:
    """Use case for study material operations."""

    def __init__(
        self,
        material_repository: IStudyMaterialRepository,
        subject_repository: ISubjectRepository,
        assignment_repository: ISubjectAssignmentRepository,
        file_storage=None
    ):
        self.material_repository = material_repository
        self.subject_repository = subject_repository
        self.assignment_repository = assignment_repository

    async def upload_material(
        self,
        ctx: RequestContext,
        request: UploadMaterialRequest
    ) -> StudyMaterial:
        """
        Create a link-based study material.

        Args:
            ctx: Request context for authorization
            request: Upload material request

        Returns:
            Created study material

        Raises:
            ValidationError: If input validation fails
            AuthorizationError: If user is not authorized
        """
        # Input validation: Validate subject_id is valid ObjectId
        try:
            ObjectId(request.subject_id)
        except Exception:
            raise ValidationError("Invalid subject_id format", field="subject_id")

        if not request.title.strip():
            raise ValidationError("Title is required", field="title")

        if not request.material_url.startswith(("http://", "https://")):
            raise ValidationError("Material link must start with http:// or https://", field="material_url")

        # Role check: ONLY FACULTY can upload materials
        if not ctx.is_faculty():
            raise AuthorizationError("Only faculty can upload study materials")

        # Verify subject exists
        subject = await self.subject_repository.find_by_id(request.subject_id)
        if not subject:
            raise ValidationError("Subject not found", field="subject_id")

        assignments = await self.assignment_repository.find_by_faculty(ctx.user_id)
        matching_assignments = [
            assignment for assignment in assignments
            if assignment.subject_id == request.subject_id
            and assignment.semester == request.semester
        ]

        if not matching_assignments:
            raise AuthorizationError(
                "Faculty must be assigned to teach this subject for the selected semester"
            )

        assigned_sections = sorted({assignment.section for assignment in matching_assignments})
        requested_sections = [section.strip().upper() for section in request.sections if section.strip()]
        sections = requested_sections or assigned_sections

        invalid_sections = sorted(set(sections) - set(assigned_sections))
        if invalid_sections:
            raise AuthorizationError(
                f"Faculty is not assigned to this subject for section(s): {', '.join(invalid_sections)}"
            )

        # Create material record
        material = StudyMaterial(
            id="",
            title=request.title.strip(),
            description=request.description.strip() if request.description else None,
            subject_id=request.subject_id,
            semester=request.semester,
            sections=sections,
            faculty_id=ctx.user_id,
            material_url=request.material_url.strip(),
            material_date=request.material_date,
            access_count=0,
            tags=request.tags,
            is_public=request.is_public,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            material_type=MaterialType.LINK
        )

        return await self.material_repository.save(material)

    async def get_materials(
        self,
        request: SearchMaterialRequest
    ) -> List[StudyMaterial]:
        """
        Get study materials based on search criteria.

        Args:
            request: Search criteria

        Returns:
            List of study materials
        """
        if request.query:
            # Text search
            return await self.material_repository.search(
                query=request.query,
                semester=request.semester,
                section=request.section,
                faculty_id=request.faculty_id,
                subject_id=request.subject_id
            )

        if request.subject_id:
            # By subject
            materials = await self.material_repository.find_by_subject(
                subject_id=request.subject_id,
                semester=request.semester,
                section=request.section,
                faculty_id=request.faculty_id
            )
            return materials

        if request.faculty_id:
            materials = await self.material_repository.find_by_faculty(request.faculty_id)
            if request.semester is not None:
                materials = [m for m in materials if m.semester == request.semester]
            return materials

        if request.semester is None:
            return []

        return await self.material_repository.find_by_semester(
            semester=request.semester,
            section=request.section
        )

    async def get_material(self, material_id: str) -> Optional[StudyMaterial]:
        """Get a specific study material by ID."""
        return await self.material_repository.find_by_id(material_id)

    async def delete_material(
        self,
        material_id: str,
        requesting_faculty_id: str
    ) -> bool:
        """
        Delete a study material.

        Args:
            material_id: ID of material to delete
            requesting_faculty_id: ID of faculty making the request

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If user doesn't have permission
        """
        material = await self.material_repository.find_by_id(material_id)
        if not material:
            raise ValueError("Material not found")

        if requesting_faculty_id and material.faculty_id != requesting_faculty_id:
            raise ValueError("You don't have permission to delete this material")

        # Delete record
        return await self.material_repository.delete(material_id)

    async def increment_downloads(self, material_id: str) -> bool:
        """Increment access count for a material."""
        return await self.material_repository.increment_download_count(material_id)
