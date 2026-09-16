import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Text, TIMESTAMP, String
from sqlalchemy.dialects.postgresql import UUID

from ..db import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    action_id = Column(UUID(as_uuid=True), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False)
    fire_at = Column(TIMESTAMP(timezone=True), nullable=False)
    channel = Column(String(50), nullable=False, server_default="in_app")
    offset_label = Column(Text)
    idempotency_key = Column(Text, nullable=False, unique=True)
    sent_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
