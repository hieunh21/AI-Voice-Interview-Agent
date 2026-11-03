from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UuidPrimaryKey, created_at_column


class User(UuidPrimaryKey, Base):
    """A registered user or a guest. Guests authenticate with an unguessable token (hash stored)."""

    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    guest_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = created_at_column()
