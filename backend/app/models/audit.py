from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    event_type = Column(Text, nullable=False)
    event = Column(Text, nullable=False)
    ip_address = Column(Text)
    user_agent = Column(Text)
    event_metadata = Column("metadata", JSONB, server_default=sa.text("'{}'::jsonb"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


async def record_audit(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    event: str,
    event_type: str = "upload",
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            event_type=event_type,
            event=event,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=metadata or {},
        )
    )
