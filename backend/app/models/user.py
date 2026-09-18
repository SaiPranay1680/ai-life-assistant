import uuid
import sqlalchemy as sa
from sqlalchemy import Boolean, Column, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import relationship

from ..db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    email = Column(CITEXT(), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=sa.true())
    email_verified = Column(Boolean, nullable=False, server_default=sa.false())
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    workspace = relationship("Workspace", back_populates="owner", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    first_name = Column(Text)
    last_name = Column(Text)
    display_name = Column(Text)
    avatar_url = Column(Text)
    locale = Column(Text)
    timezone = Column(Text)

    user = relationship("User", back_populates="profile")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )
    name = Column(Text, nullable=False)
    owner_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

    owner = relationship("User", back_populates="workspace")
