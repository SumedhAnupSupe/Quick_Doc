import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, IdMixin, UTCDateTime, utcnow


class VerificationRequest(IdMixin, Base):
    """A queue item: an enrolment or document awaiting human review."""

    __tablename__ = "verification_requests"
    __table_args__ = (Index("ix_vreq_target", "target_type", "target_id"),)
    target_type: Mapped[str] = mapped_column(String(16))  # enrolment | document
    target_id: Mapped[uuid.UUID] = mapped_column()
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )
    state_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    vault_type: Mapped[str | None] = mapped_column(String(12), nullable=True)
    # pending | approved | rejected | correction_requested
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class VerificationRecord(IdMixin, Base):
    """Append-only decision history."""

    __tablename__ = "verification_records"
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verification_requests.id"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(24))  # approved | rejected | correction_requested
    remarks: Mapped[str] = mapped_column(Text, default="")
    previous_status: Mapped[str] = mapped_column(String(24))
    new_status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
