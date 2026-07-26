from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime
from ..db import Base


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    identifier: Mapped[str] = mapped_column(String, index=True)   # phone or email
    code: Mapped[str] = mapped_column(String)                      # 4-digit or UUID token
    kind: Mapped[str] = mapped_column(String)                      # "sms" | "email"
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow())
