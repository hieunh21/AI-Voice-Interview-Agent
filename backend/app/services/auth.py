"""Guest authentication: an unguessable bearer token; only its SHA-256 hash is stored."""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

TOKEN_BYTES = 32


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_guest(db: AsyncSession) -> tuple[User, str]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    user = User(guest_token_hash=hash_token(token))
    db.add(user)
    await db.commit()
    return user, token


async def user_for_token(db: AsyncSession, token: str) -> User | None:
    if not token or len(token) > 256:
        return None
    return await db.scalar(select(User).where(User.guest_token_hash == hash_token(token)))
