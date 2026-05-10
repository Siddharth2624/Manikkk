"""Authentication tests."""

import pytest
from app.use_cases.auth import AuthenticationUseCase, RegisterRequest
from app.domain.entities.user import UserRole
from app.adapters.repositories import UserRepository


@pytest.mark.asyncio
async def test_register_student(test_db, test_user_data):
    """Test student registration."""
    from app.adapters.repositories.user_repository import UserRepository

    user_repo = UserRepository(test_db)
    auth_use_case = AuthenticationUseCase(user_repo)

    request = RegisterRequest(
        email=test_user_data["email"],
        password=test_user_data["password"],
        full_name=test_user_data["full_name"],
        role=UserRole.STUDENT,
        semester=test_user_data["semester"],
        section=test_user_data["section"]
    )

    response = await auth_use_case.register(request)

    assert response.user.email == test_user_data["email"]
    assert response.user.role == UserRole.STUDENT
    assert response.user.semester == 1
    assert response.user.section == "A"
    assert response.user.is_active is True


@pytest.mark.asyncio
async def test_register_duplicate_email(test_db, test_user_data):
    """Test that duplicate email registration fails."""
    user_repo = UserRepository(test_db)
    auth_use_case = AuthenticationUseCase(user_repo)

    request = RegisterRequest(
        email=test_user_data["email"],
        password=test_user_data["password"],
        full_name=test_user_data["full_name"],
        role=UserRole.STUDENT,
        semester=1,
        section="A"
    )

    # First registration should succeed
    await auth_use_case.register(request)

    # Second registration should fail
    with pytest.raises(ValueError, match="already exists"):
        await auth_use_case.register(request)


@pytest.mark.asyncio
async def test_login_success(test_db, test_user_data):
    """Test successful login."""
    user_repo = UserRepository(test_db)
    auth_use_case = AuthenticationUseCase(user_repo)

    # Register user first
    register_request = RegisterRequest(
        email=test_user_data["email"],
        password=test_user_data["password"],
        full_name=test_user_data["full_name"],
        role=UserRole.STUDENT,
        semester=1,
        section="A"
    )
    await auth_use_case.register(register_request)

    # Now login
    from app.use_cases.auth import LoginRequest
    login_request = LoginRequest(
        email=test_user_data["email"],
        password=test_user_data["password"]
    )
    response = await auth_use_case.login(login_request)

    assert response.user.email == test_user_data["email"]
    assert response.access_token is not None
    assert response.refresh_token is not None


@pytest.mark.asyncio
async def test_login_invalid_password(test_db, test_user_data):
    """Test login with invalid password."""
    user_repo = UserRepository(test_db)
    auth_use_case = AuthenticationUseCase(user_repo)

    # Register user first
    register_request = RegisterRequest(
        email=test_user_data["email"],
        password=test_user_data["password"],
        full_name=test_user_data["full_name"],
        role=UserRole.STUDENT,
        semester=1,
        section="A"
    )
    await auth_use_case.register(register_request)

    # Try login with wrong password
    from app.use_cases.auth import LoginRequest
    login_request = LoginRequest(
        email=test_user_data["email"],
        password="WrongPassword123!"
    )

    with pytest.raises(ValueError, match="Invalid email or password"):
        await auth_use_case.login(login_request)
