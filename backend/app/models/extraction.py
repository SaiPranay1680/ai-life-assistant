import sqlalchemy as sa
from sqlalchemy import Column, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from ..db import Base


class ExtractionField(Base):
    __tablename__ = "extraction_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(Text, nullable=False)
    raw_value = Column(Text)
    normalized_value = Column(Text)
    confidence = Column(Float)
    page_number = Column(Integer)
    evidence_snippet = Column(Text)
