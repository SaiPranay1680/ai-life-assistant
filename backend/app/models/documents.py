import sqlalchemy as sa
from sqlalchemy import BigInteger, Column, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID

from ..db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    original_filename = Column(Text)
    extension = Column(String(20))
    declared_mime = Column(String(100))
    detected_mime = Column(String(100))
    file_size = Column(BigInteger)
    sha256 = Column(String(64))
    storage_key = Column(Text)
    scan_status = Column(String(50), server_default="pending")
    processing_status = Column(String(50), server_default="uploaded")
    document_type = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
