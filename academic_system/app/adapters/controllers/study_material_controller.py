"""Study material controller - FastAPI routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User
from app.domain.entities.request_context import RequestContext
from app.domain.interfaces.repositories import (
    IStudyMaterialRepository, ISubjectRepository, ISubjectAssignmentRepository
)
from app.domain.exceptions import AuthorizationError, ValidationError
from app.adapters.repositories import (
    StudyMaterialRepository, SubjectRepository, SubjectAssignmentRepository
)
from app.adapters.services import LocalFileStorageService
from app.use_cases.study_material import StudyMaterialUseCase
from app.infrastructure.dependencies import get_current_user, get_current_faculty_or_admin
from app.infrastructure.authorization import get_request_context
from app.infrastructure.database import get_database
from app.infrastructure.config import settings
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/materials", tags=["Study Materials"])


# DTOs
class UploadMaterialRequest(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: str
    semester: int
    sections: List[str] = []
    tags: List[str] = []
    is_public: bool = True


async def get_study_material_use_case(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> StudyMaterialUseCase:
    """Dependency to get study material use case."""
    material_repo = StudyMaterialRepository(db)
    subject_repo = SubjectRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    file_storage = LocalFileStorageService()
    return StudyMaterialUseCase(material_repo, subject_repo, assignment_repo, file_storage)


@router.post("/upload")
async def upload_material(
    metadata: UploadMaterialRequest,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_request_context),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Upload study material (faculty only)."""
    # Read file content
    content = await file.read()

    from app.use_cases.study_material import UploadMaterialRequest as UploadRequest

    request = UploadRequest(
        title=metadata.title,
        description=metadata.description,
        subject_id=metadata.subject_id,
        semester=metadata.semester,
        sections=metadata.sections,
        faculty_id=ctx.user_id,
        file_content=content,
        file_name=file.filename,
        tags=metadata.tags,
        is_public=metadata.is_public
    )

    material = await material_use_case.upload_material(ctx, request)

    return {
        "id": material.id,
        "title": material.title,
        "file_url": material.file_url,
        "file_name": material.file_name,
        "file_size_mb": material.get_file_size_mb(),
        "message": "Material uploaded successfully"
    }


@router.get("")
async def list_materials(
    semester: Optional[int] = None,
    section: Optional[str] = None,
    subject_id: Optional[str] = None,
    query: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """List study materials (filtered by user role)."""
    from app.use_cases.study_material import SearchMaterialRequest

    # Students can only see materials for their semester
    if current_user.is_student():
        semester = current_user.semester
        section = current_user.section

    request = SearchMaterialRequest(
        query=query,
        semester=semester,
        section=section,
        subject_id=subject_id
    )

    materials = await material_use_case.get_materials(request)

    return {
        "materials": [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "subject_id": m.subject_id,
                "semester": m.semester,
                "sections": m.sections,
                "faculty_id": m.faculty_id,
                "file_name": m.file_name,
                "file_size_mb": m.get_file_size_mb(),
                "material_type": m.material_type.value,
                "upload_date": m.upload_date.isoformat(),
                "download_count": m.download_count,
                "tags": m.tags
            }
            for m in materials
        ]
    }


@router.get("/{material_id}")
async def get_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Get study material details."""
    material = await material_use_case.get_material(material_id)

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    # Check access permission
    if current_user.is_student():
        if not material.is_visible_to(current_user.semester, current_user.section):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this material"
            )

    return {
        "id": material.id,
        "title": material.title,
        "description": material.description,
        "subject_id": material.subject_id,
        "semester": material.semester,
        "sections": material.sections,
        "faculty_id": material.faculty_id,
        "file_name": material.file_name,
        "file_size_mb": material.get_file_size_mb(),
        "material_type": material.material_type.value,
        "upload_date": material.upload_date.isoformat(),
        "download_count": material.download_count,
        "tags": material.tags
    }


@router.get("/{material_id}/download")
async def download_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Download study material file."""
    material = await material_use_case.get_material(material_id)

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    # Check access permission
    if current_user.is_student():
        if not material.is_visible_to(current_user.semester, current_user.section):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to download this material"
            )

    # Increment download count
    await material_use_case.increment_downloads(material_id)

    # Get file path
    file_path = Path(settings.upload_dir) / material.file_url.replace("/static/uploads/", "")

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        filename=material.file_name,
        media_type="application/octet-stream"
    )


@router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Delete study material (owner faculty or admin only)."""
    try:
        if current_user.is_faculty():
            await material_use_case.delete_material(material_id, current_user.id)
        else:
            # Admin can delete any material
            await material_use_case.delete_material(material_id, None)

        return {"message": "Material deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
