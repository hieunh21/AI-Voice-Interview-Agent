import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.auth import create_guest

router = APIRouter(prefix="/auth", tags=["auth"])


class GuestToken(BaseModel):
    user_id: uuid.UUID
    token: str


@router.post("/guest", response_model=GuestToken, status_code=status.HTTP_201_CREATED)
async def create_guest_session(db: SessionDep) -> GuestToken:
    """Create a guest identity. The token is returned once; only its hash is stored."""
    user, token = await create_guest(db)
    return GuestToken(user_id=user.id, token=token)
