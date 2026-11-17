import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, IdMixin, UTCDateTime, utcnow


class DuplicateCase(IdMixin, Base):
    __tablename__ = "duplicate_cases"
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    matching_identifier_type: Mapped[str] = mapped_column(String(24), default="apaar_id")
    detection_reason: Mapped[str] = mapped_column(Text)
    # open | info_requested | resolved
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    # legitimate_transfer | confirmed_duplicate | not_a_duplicate
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class DuplicateCaseEnrolment(Base):
    __tablename__ = "duplicate_case_enrolments"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("duplicate_cases.id"), primary_key=True)
    enrolment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_enrolments.id"), primary_key=True
    )


class DuplicateCaseEvent(IdMixin, Base):
    __tablename__ = "duplicate_case_events"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("duplicate_cases.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    remarks: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class OtpChallenge(IdMixin, Base):
    """Simulated OTP. Only a digest is stored; the value is never logged or audited."""

    __tablename__ = "otp_challenges"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("duplicate_cases.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
