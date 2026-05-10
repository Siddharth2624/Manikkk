from fastapi import Depends

from app.domain.entities.request_context import RequestContext
from app.domain.entities.user import User
from .dependencies import get_current_user

async def get_request_context(
    current_user: User = Depends(get_current_user)
) -> RequestContext:
    """Convert User to RequestContext for service layer."""
    return RequestContext.from_user(current_user)
