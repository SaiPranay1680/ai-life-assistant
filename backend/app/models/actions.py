import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID

from ..db import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    action_type = Column(String(50), nullable=False)
    due_at = Column(Date)
    due_label = Column(Text)
    priority = Column(String(20), nullable=False, server_default="medium")
    status = Column(String(50), nullable=False, server_default="suggested")
    confidence = Column(Float)
    explanation = Column(Text)
    evidence = Column(Text)
    reminder_default = Column(Text)
    requires_confirmation = Column(Boolean, nullable=False, server_default=sa.text("true"))
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
