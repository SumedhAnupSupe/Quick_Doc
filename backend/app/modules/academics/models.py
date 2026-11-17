import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdMixin, TimestampMixin, UTCDateTime, utcnow


class AcademicYear(IdMixin, Base):
    __tablename__ = "academic_years"
    label: Mapped[str] = mapped_column(String(9), unique=True)  # "2025-26"
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class AcademicProgramme(IdMixin, TimestampMixin, Base):
    __tablename__ = "academic_programmes"
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    level: Mapped[str] = mapped_column(String(32))  # matches institution_types.level
    duration_years: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SeatCategory(IdMixin, Base):
    """Centrally managed seat/admission categories (NRI, OCI, Foreign National, ...)."""

    __tablename__ = "seat_categories"
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ApprovedIntake(IdMixin, TimestampMixin, Base):
    __tablename__ = "approved_intakes"
    __table_args__ = (
        UniqueConstraint("institution_id", "programme_id", "academic_year_id"),
        CheckConstraint("approved_intake >= 0", name="ck_intake_nonneg"),
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_programmes.id"))
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id"))
    approved_intake: Mapped[int] = mapped_column(Integer)  # base (general) intake
    approval_reference: Mapped[str] = mapped_column(String(80))
    effective_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | revoked
    revision: Mapped[int] = mapped_column(Integer, default=1)

    category_seats: Mapped[list["IntakeCategorySeat"]] = relationship(
        back_populates="intake", cascade="all, delete-orphan", lazy="selectin"
    )
    programme: Mapped[AcademicProgramme] = relationship(lazy="joined")
    academic_year: Mapped[AcademicYear] = relationship(lazy="joined")


class IntakeCategorySeat(IdMixin, Base):
    __tablename__ = "intake_category_seats"
    __table_args__ = (
        UniqueConstraint("intake_id", "category_id"),
        CheckConstraint("seats >= 0", name="ck_category_seats_nonneg"),
    )
    intake_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approved_intakes.id"), index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seat_categories.id"))
    seats: Mapped[int] = mapped_column(Integer)

    intake: Mapped[ApprovedIntake] = relationship(back_populates="category_seats")
    category: Mapped[SeatCategory] = relationship(lazy="joined")


class IntakeRevision(IdMixin, Base):
    """Immutable snapshot written before every intake change; nothing is silently overwritten."""

    __tablename__ = "intake_revisions"
    intake_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approved_intakes.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text, default="")
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
