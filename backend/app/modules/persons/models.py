from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, IdMixin, TimestampMixin


class Person(IdMixin, TimestampMixin, Base):
    """Identity only. A person is NOT an enrolment, and persons are never auto-merged."""

    __tablename__ = "persons"
    # Prototype identifier. Format-validated only; NOT verified against any government system.
    apaar_id: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)  # names are never unique keys
    date_of_birth: Mapped[date] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
