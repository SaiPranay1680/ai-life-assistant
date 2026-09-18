import sqlalchemy as sa
from sqlalchemy import Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from ..db import Base


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"))
    provider = Column(Text, nullable=False)
    provider_user_id = Column(Text, nullable=False)
    provider_username = Column(Text)
    id_token = Column(Text)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
