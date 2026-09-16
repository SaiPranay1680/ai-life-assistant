import sqlalchemy as sa
from sqlalchemy import Column, Boolean, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from ..db import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(Text, nullable=False)
    revoked = Column(Boolean, nullable=False, server_default=sa.false())
    issued_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    ip_address = Column(Text)
    user_agent = Column(Text)
    replaced_by = Column(UUID(as_uuid=True), sa.ForeignKey("refresh_tokens.id"))
