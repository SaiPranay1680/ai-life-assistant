import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import relationship

from ..db import Base

OTP_PASSWORD_RESET = "PASSWORD_RESET"
OTP_ACCOUNT_VERIFICATION = "ACCOUNT_VERIFICATION"


class AuthOtpCode(Base):
    __tablename__ = "auth_otp_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(CITEXT(), nullable=False)
    otp_hash = Column(Text, nullable=False)
    otp_type = Column(Text, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, server_default=sa.text("0"))
    max_attempts = Column(Integer, nullable=False, server_default=sa.text("5"))
    used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()"))

    user = relationship("User")
