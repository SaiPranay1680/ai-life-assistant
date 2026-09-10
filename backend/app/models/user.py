import sqlalchemy as sa
from sqlalchemy import Column, Boolean, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from ..db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    email = Column(sa.CITEXT(), unique=True, index=True)
    password_hash = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=sa.true())
    email_verified = Column(Boolean, nullable=False, server_default=sa.false())
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))

