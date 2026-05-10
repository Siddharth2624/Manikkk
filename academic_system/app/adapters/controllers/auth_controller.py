"""Authentication controller - FastAPI routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User, UserRole
from app.domain.interfaces.repositories import IUserRepository
from app.adapters.repositories import UserRepository
from app.use_cases.auth import (
    AuthenticationUseCase,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ChangePasswordRequest
)
from app.infrastructure.dependencies import get_current_user, get_current_admin
from app.infrastructure.database import get_database

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_auth_use_case(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> AuthenticationUseCase:
    """Dependency to get auth use case."""
    user_repo = UserRepository(db)
    return AuthenticationUseCase(user_repo)


@router.post("/login", response_model=dict)
async def login(
    request: LoginRequest,
    auth_use_case: AuthenticationUseCase = Depends(get_auth_use_case)
):
    """Login with email and password."""
    try:
        response = await auth_use_case.login(request)
        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.full_name,
                "role": response.user.role.value,
                "semester": response.user.semester,
                "section": response.user.section
            },
            "access_token": response.access_token,
            "refresh_token": response.refresh_token,
            "token_type": response.token_type
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/register", response_model=dict)
async def register(
    request: RegisterRequest,
    auth_use_case: AuthenticationUseCase = Depends(get_auth_use_case)
):
    """Register a new user (admin only for students/faculty)."""
    try:
        response = await auth_use_case.register(request)
        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.full_name,
                "role": response.user.role.value
            },
            "message": response.message
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    auth_use_case: AuthenticationUseCase = Depends(get_auth_use_case)
):
    """Change current user's password."""
    try:
        await auth_use_case.change_password(current_user.id, request)
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "semester": current_user.semester,
        "section": current_user.section,
        "roll_number": current_user.roll_number,
        "department": current_user.department
    }


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    auth_use_case: AuthenticationUseCase = Depends(get_auth_use_case)
):
    """Refresh access token."""
    token = await auth_use_case.refresh_token(current_user.id)
    return {"access_token": token, "token_type": "bearer"}
