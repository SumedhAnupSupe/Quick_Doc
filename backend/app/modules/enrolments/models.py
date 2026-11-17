import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdMixin, TimestampMixin, UTCDateTime, utcnow
from app.modules.academics.models import AcademicProgramme, AcademicYear, SeatCategory
from app.modules.institutions.models import Institution
from app.modules.persons.models import Person

# Enrolment lifecycle
ACTIVE = "active"
HISTORICAL = "historical"  # e.g. completed / past year
TRANSFERRED = "transferred"
CANCELLED = "cancelled"
UNDER_REVIEW = "under_review"  # held while a duplicate case is open


class StudentEnrolment(IdMixin, TimestampMixin, Base):
    __tablename__ = "student_enrolments"
    __table_args__ = (Index("ix_enrol_person_status", "person_id", "enrolment_status"),)

    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_programmes.id"), index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seat_categories.id"), nullable=True
    )  # null = general intake
    admission_date: Mapped[date] = mapped_column(Date)
    enrolment_status: Mapped[str] = mapped_column(String(20), default=ACTIVE, index=True)
    # draft | submitted | correction_requested | approved | rejected
    submission_status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified")
    transferred_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("student_enrolments.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    person: Mapped[Person] = relationship(lazy="joined")
    institution: Mapped[Institution] = relationship(lazy="joined")
    programme: Mapped[AcademicProgramme] = relationship(lazy="joined")
    academic_year: Mapped[AcademicYear] = relationship(lazy="joined")
    category: Mapped[SeatCategory | None] = relationship(lazy="joined")


class EnrolmentStatusHistory(IdMixin, Base):
    __tablename__ = "enrolment_status_history"
    enrolment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_enrolments.id"), index=True)
    field: Mapped[str] = mapped_column(String(32))  # enrolment_status | submission_status | ...
    previous_value: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_value: Mapped[str] = mapped_column(String(32))
    remarks: Mapped[str] = mapped_column(Text, default="")
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
