"""Study material controller - FastAPI routes."""

from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.adapters.repositories import StudyMaterialRepository, SubjectAssignmentRepository, SubjectRepository
from app.domain.entities.request_context import RequestContext
from app.domain.entities.study_material import StudyMaterial
from app.domain.entities.user import User
from app.domain.exceptions import AuthorizationError, ValidationError
from app.domain.interfaces.repositories import (
    ISubjectAssignmentRepository,
    ISubjectRepository,
    IUserRepository,
)
from app.infrastructure.authorization import get_request_context
from app.infrastructure.database import get_database
from app.infrastructure.dependencies import (
    get_current_user,
    get_subject_assignment_repository,
    get_subject_repository,
    get_user_repository,
)
from app.use_cases.study_material import StudyMaterialUseCase

router = APIRouter(prefix="/materials", tags=["Study Materials"])


class CreateMaterialRequest(BaseModel):
    title: str
    material_url: str
    material_date: date = Field(default_factory=date.today)
    subject_id: str
    semester: int
    sections: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_public: bool = True


async def get_study_material_use_case(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> StudyMaterialUseCase:
    """Dependency to get study material use case."""
    material_repo = StudyMaterialRepository(db)
    subject_repo = SubjectRepository(db)
    assignment_repo = SubjectAssignmentRepository(db)
    return StudyMaterialUseCase(material_repo, subject_repo, assignment_repo)


async def _serialize_material(
    material: StudyMaterial,
    subject_repo: ISubjectRepository,
    user_repo: IUserRepository,
    subject_cache: Dict[str, object],
    faculty_cache: Dict[str, object],
) -> Dict:
    subject = subject_cache.get(material.subject_id)
    if subject is None:
        subject = await subject_repo.find_by_id(material.subject_id)
        subject_cache[material.subject_id] = subject

    faculty = faculty_cache.get(material.faculty_id)
    if faculty is None:
        faculty = await user_repo.find_by_id(material.faculty_id)
        faculty_cache[material.faculty_id] = faculty

    return {
        "id": material.id,
        "title": material.title,
        "description": material.description,
        "subject_id": material.subject_id,
        "subject": {
            "id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "semester": subject.semester,
            "subject_type": subject.subject_type.value if hasattr(subject.subject_type, "value") else subject.subject_type,
        } if subject else None,
        "semester": material.semester,
        "sections": material.sections,
        "faculty_id": material.faculty_id,
        "faculty_name": faculty.full_name if faculty else "",
        "material_url": material.material_url,
        "material_date": material.material_date.isoformat(),
        "access_count": material.access_count,
        "material_type": material.material_type.value,
        "tags": material.tags,
        "created_at": material.created_at.isoformat(),
        "updated_at": material.updated_at.isoformat(),
    }


def _ensure_material_access(material: StudyMaterial, current_user: User) -> None:
    if current_user.is_admin():
        return

    if current_user.is_faculty() and material.faculty_id == current_user.id:
        return

    if current_user.is_student() and material.is_visible_to(current_user.semester, current_user.section):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to access this material"
    )


@router.get("/subjects")
async def list_material_subjects(
    semester: Optional[int] = Query(None, ge=1, le=8),
    current_user: User = Depends(get_current_user),
    subject_repo: ISubjectRepository = Depends(get_subject_repository),
    assignment_repo: ISubjectAssignmentRepository = Depends(get_subject_assignment_repository),
):
    """List subjects relevant to the current user for study materials."""
    if current_user.is_faculty():
        assignments = await assignment_repo.find_by_faculty(current_user.id)
        if semester is not None:
            assignments = [a for a in assignments if a.semester == semester]
    elif current_user.is_student():
        assignments = await assignment_repo.find_by_semester_and_section(
            semester=current_user.semester,
            section=current_user.section,
        )
    else:
        subjects = await subject_repo.find_all(semester=semester, limit=100)
        return {
            "subjects": [
                {
                    "subject_id": subject.id,
                    "subject": {
                        "id": subject.id,
                        "code": subject.code,
                        "name": subject.name,
                        "semester": subject.semester,
                        "subject_type": subject.subject_type.value if hasattr(subject.subject_type, "value") else subject.subject_type,
                    },
                    "semester": subject.semester,
                    "sections": [],
                }
                for subject in subjects
            ]
        }

    grouped: Dict[tuple, Dict] = {}
    for assignment in assignments:
        key = (assignment.subject_id, assignment.semester)
        if key not in grouped:
            subject = await subject_repo.find_by_id(assignment.subject_id)
            grouped[key] = {
                "subject_id": assignment.subject_id,
                "subject": {
                    "id": subject.id,
                    "code": subject.code,
                    "name": subject.name,
                    "semester": subject.semester,
                    "subject_type": subject.subject_type.value if hasattr(subject.subject_type, "value") else subject.subject_type,
                } if subject else None,
                "semester": assignment.semester,
                "sections": [],
            }
        grouped[key]["sections"].append(assignment.section)

    return {
        "subjects": [
            {
                **item,
                "sections": sorted(set(item["sections"])),
            }
            for item in sorted(grouped.values(), key=lambda x: (x["semester"], x["subject"]["code"] if x["subject"] else ""))
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_material(
    request_data: CreateMaterialRequest,
    ctx: RequestContext = Depends(get_request_context),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Create a link-based study material record (faculty only)."""
    from app.use_cases.study_material import UploadMaterialRequest

    request = UploadMaterialRequest(
        title=request_data.title,
        description=request_data.description,
        subject_id=request_data.subject_id,
        semester=request_data.semester,
        sections=request_data.sections,
        faculty_id=ctx.user_id,
        material_url=request_data.material_url,
        material_date=request_data.material_date,
        tags=request_data.tags,
        is_public=request_data.is_public
    )

    try:
        material = await material_use_case.upload_material(ctx, request)
        return {
            "id": material.id,
            "title": material.title,
            "material_url": material.material_url,
            "material_date": material.material_date.isoformat(),
            "message": "Material link saved successfully"
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )


@router.post("/upload", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_material_legacy_path(
    request_data: CreateMaterialRequest,
    ctx: RequestContext = Depends(get_request_context),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Backward-compatible path for clients still calling /materials/upload."""
    return await create_material(request_data, ctx, material_use_case)


@router.get("")
async def list_materials(
    semester: Optional[int] = Query(None, ge=1, le=8),
    section: Optional[str] = None,
    subject_id: Optional[str] = None,
    query: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case),
    subject_repo: ISubjectRepository = Depends(get_subject_repository),
    user_repo: IUserRepository = Depends(get_user_repository),
):
    """List study material links filtered by user role."""
    from app.use_cases.study_material import SearchMaterialRequest

    faculty_id = None
    if current_user.is_student():
        semester = current_user.semester
        section = current_user.section
    elif current_user.is_faculty():
        faculty_id = current_user.id

    request = SearchMaterialRequest(
        query=query,
        semester=semester,
        section=section,
        subject_id=subject_id,
        faculty_id=faculty_id
    )

    materials = await material_use_case.get_materials(request)
    subject_cache: Dict[str, object] = {}
    faculty_cache: Dict[str, object] = {}

    return {
        "materials": [
            await _serialize_material(material, subject_repo, user_repo, subject_cache, faculty_cache)
            for material in materials
        ]
    }


@router.get("/{material_id}")
async def get_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case),
    subject_repo: ISubjectRepository = Depends(get_subject_repository),
    user_repo: IUserRepository = Depends(get_user_repository),
):
    """Get study material details."""
    material = await material_use_case.get_material(material_id)

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    _ensure_material_access(material, current_user)

    return await _serialize_material(material, subject_repo, user_repo, {}, {})


@router.post("/{material_id}/access")
async def access_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Record access and return the external material link."""
    material = await material_use_case.get_material(material_id)

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    _ensure_material_access(material, current_user)
    await material_use_case.increment_downloads(material_id)
    return {"material_url": material.material_url}


@router.get("/{material_id}/download")
async def download_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    material_use_case: StudyMaterialUseCase = Depends(get_study_material_use_case)
):
    """Open the external study material link."""
    material = await material_use_case.get_material(material_id)

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    _ensure_material_access(material, current_user)
    await material_use_case.increment_downloads(material_id)
    return RedirectResponse(material.material_url)


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
        elif current_user.is_admin():
            await material_use_case.delete_material(material_id, None)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only faculty or admin can delete materials"
            )

        return {"message": "Material deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
