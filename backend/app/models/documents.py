import sqlalchemy as sa
from sqlalchemy import Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from ..db import Base


class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    owner_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"))
    organization_id = Column(UUID(as_uuid=True), sa.ForeignKey("organizations.id"))
    title = Column(Text)
    content = Column(Text)
    storage_key = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
