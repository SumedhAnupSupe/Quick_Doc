import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdMixin, TimestampMixin, UTCDateTime, utcnow


class InstitutionType(IdMixin, Base):
    __tablename__ = "institution_types"
    code: Mapped[str] = mapped_column(String(32), unique=True)  # e.g. "graduation"
    name: Mapped[str] = mapped_column(String(80))
    level: Mapped[str] = mapped_column(String(32))  # 10th | 12th | graduation | postgraduation


class Institution(IdMixin, TimestampMixin, Base):
    __tablename__ = "institutions"
    name: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    institution_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution_types.id"))
    address: Mapped[str] = mapped_column(Text, default="")
    state_code: Mapped[str] = mapped_column(String(8), index=True)
    state: Mapped[str] = mapped_column(String(80))
    district: Mapped[str] = mapped_column(String(80))
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # pending | approved | rejected | suspended | deactivated
    approval_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    registration_date: Mapped[date] = mapped_column(Date, default=date.today)

    institution_type: Mapped[InstitutionType] = relationship(lazy="joined")


class InstitutionStatusHistory(IdMixin, Base):
    __tablename__ = "institution_status_history"
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20))
    remarks: Mapped[str] = mapped_column(Text, default="")
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class InstitutionUser(Base):
    __tablename__ = "institution_users"
    __table_args__ = (UniqueConstraint("user_id"),)  # a user belongs to one institution
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
