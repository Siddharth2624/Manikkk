"""Authentication use cases."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.domain.entities.user import User, UserRole
from app.domain.interfaces.repositories import IUserRepository
from app.infrastructure.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token
)


@dataclass
class LoginRequest:
    """Login request DTO."""
    email: str
    password: str


@dataclass
class LoginResponse:
    """Login response DTO."""
    user: User
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass
class RegisterRequest:
    """Register request DTO."""
    email: str
    password: str
    full_name: str
    role: UserRole
    semester: Optional[int] = None
    section: Optional[str] = None
    roll_number: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None


@dataclass
class RegisterResponse:
    """Register response DTO."""
    user: User
    message: str


@dataclass
class ChangePasswordRequest:
    """Change password request DTO."""
    current_password: str
    new_password: str


class AuthenticationUseCase:
    """Use case for authentication operations."""

    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def login(self, request: LoginRequest) -> LoginResponse:
        """
        Authenticate a user and return tokens.

        Args:
            request: Login request with email and password

        Returns:
            Login response with user and tokens

        Raises:
            ValueError: If credentials are invalid or user is inactive
        """
        # Find user by email
        user = await self.user_repository.find_by_email(request.email)
        if not user:
            raise ValueError("Invalid email or password")

        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is inactive")

        # Generate tokens
        token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return LoginResponse(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """
        Register a new user.

        Args:
            request: Registration request

        Returns:
            Register response with created user

        Raises:
            ValueError: If user already exists or validation fails
        """
        # Check if user already exists
        if await self.user_repository.exists(request.email):
            raise ValueError("User with this email already exists")

        # Validate role-specific fields
        if request.role == UserRole.STUDENT:
            if not request.semester or not request.section:
                raise ValueError("Semester and section are required for students")
            if not 1 <= request.semester <= 8:
                raise ValueError("Semester must be between 1 and 8")
        elif request.role == UserRole.FACULTY:
            # Auto-set CSE department if not provided
            if not request.department:
                request.department = "Computer Science & Engineering"

        # Check roll number uniqueness for students
        if request.role == UserRole.STUDENT and request.roll_number:
            existing = await self.user_repository.find_by_roll_number(request.roll_number)
            if existing:
                raise ValueError("Student with this roll number already exists")

        # Check employee ID uniqueness for faculty
        if request.role == UserRole.FACULTY and request.employee_id:
            existing = await self.user_repository.find_by_employee_id(request.employee_id)
            if existing:
                raise ValueError("Faculty with this employee ID already exists")

        # Create user
        user = await self.user_repository.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
            semester=request.semester,
            section=request.section,
            roll_number=request.roll_number,
            employee_id=request.employee_id,
            department=request.department
        )

        return RegisterResponse(
            user=user,
            message="User registered successfully"
        )

    async def change_password(
        self,
        user_id: str,
        request: ChangePasswordRequest
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: ID of the user
            request: Password change request

        Returns:
            True if password changed successfully

        Raises:
            ValueError: If current password is incorrect
        """
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify current password
        if not verify_password(request.current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        # Update password
        user.password_hash = hash_password(request.new_password)
        await self.user_repository.save(user)

        return True

    async def get_current_user(self, user_id: str) -> User:
        """Get current user by ID."""
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    async def refresh_token(self, user_id: str) -> str:
        """Generate new access token for user."""
        user = await self.user_repository.find_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Invalid user")

        token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
        return create_access_token(token_data)
