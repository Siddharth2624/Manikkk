"""Study material use cases."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import date, datetime
from pathlib import Path

from bson import ObjectId

from app.domain.entities.request_context import RequestContext
from app.domain.entities.study_material import StudyMaterial, MaterialType
from app.domain.exceptions import AuthorizationError, ValidationError
from app.domain.interfaces.repositories import (
    IStudyMaterialRepository,
    ISubjectRepository,
    ISubjectAssignmentRepository,
)
from app.domain.interfaces.file_storage import IFileStorageService


@dataclass
class UploadMaterialRequest:
    """Request to upload study material."""
    title: str
    description: Optional[str]
    subject_id: str
    semester: int
    sections: List[str]
    faculty_id: str
    file_content: bytes
    file_name: str
    tags: List[str]
    is_public: bool = True


@dataclass
class SearchMaterialRequest:
    """Request to search study materials."""
    query: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None
    subject_id: Optional[str] = None


class StudyMaterialUseCase:
    """Use case for study material operations."""

    def __init__(
        self,
        material_repository: IStudyMaterialRepository,
        subject_repository: ISubjectRepository,
        assignment_repository: ISubjectAssignmentRepository,
        file_storage: IFileStorageService
    ):
        self.material_repository = material_repository
        self.subject_repository = subject_repository
        self.assignment_repository = assignment_repository
        self.file_storage = file_storage

    async def upload_material(
        self,
        ctx: RequestContext,
        request: UploadMaterialRequest
    ) -> StudyMaterial:
        """
        Upload a study material.

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

        # Input validation: Validate file_content is not empty
        if not request.file_content:
            raise ValidationError("File content cannot be empty", field="file_content")

        # Role check: ONLY FACULTY can upload materials
        if not ctx.is_faculty():
            raise AuthorizationError("Only faculty can upload study materials")

        # Verify subject exists
        subject = await self.subject_repository.find_by_id(request.subject_id)
        if not subject:
            raise ValidationError("Subject not found", field="subject_id")

        # Faculty assignment check: Faculty must be assigned to teach this subject
        # Check if faculty is assigned to at least one of the sections for this subject
        has_assignment = False
        for section in request.sections:
            assignment = await self.assignment_repository.find_faculty_assignment(
                faculty_id=ctx.user_id,
                subject_id=request.subject_id,
                semester=request.semester,
                section=section
            )
            if assignment:
                has_assignment = True
                break

        if not has_assignment:
            raise AuthorizationError(
                "Faculty must be assigned to teach this subject for the specified semester/section"
            )

        # Determine material type from file extension
        material_type = self._get_material_type(request.file_name)

        # Save file
        file_path = await self.file_storage.save_upload(
            file_content=request.file_content,
            filename=request.file_name,
            folder=f"semester_{request.semester}"
        )

        # Create material record
        material = StudyMaterial(
            id="",
            title=request.title,
            description=request.description,
            subject_id=request.subject_id,
            semester=request.semester,
            sections=request.sections,
            faculty_id=request.faculty_id,
            material_type=material_type,
            file_url=file_path,
            file_name=request.file_name,
            file_size=len(request.file_content),
            upload_date=date.today(),
            download_count=0,
            tags=request.tags,
            is_public=request.is_public,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
                semester=request.semester
            )

        if request.subject_id:
            # By subject
            return await self.material_repository.find_by_subject(
                subject_id=request.subject_id,
                semester=request.semester
            )

        # By semester
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

        if material.faculty_id != requesting_faculty_id:
            raise ValueError("You don't have permission to delete this material")

        # Delete file
        await self.file_storage.delete_file(material.file_url)

        # Delete record
        return await self.material_repository.delete(material_id)

    async def increment_downloads(self, material_id: str) -> bool:
        """Increment download count for a material."""
        return await self.material_repository.increment_download_count(material_id)

    def _get_material_type(self, filename: str) -> MaterialType:
        """Determine material type from filename."""
        ext = Path(filename).suffix.lower()

        type_map = {
            ".pdf": MaterialType.PDF,
            ".doc": MaterialType.DOCUMENT,
            ".docx": MaterialType.DOCUMENT,
            ".ppt": MaterialType.PRESENTATION,
            ".pptx": MaterialType.PRESENTATION,
            ".zip": MaterialType.ARCHIVE,
            ".rar": MaterialType.ARCHIVE
        }

        return type_map.get(ext, MaterialType.OTHER)
