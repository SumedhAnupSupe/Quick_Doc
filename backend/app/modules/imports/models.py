import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, IdMixin, UTCDateTime, utcnow


class BulkImportJob(IdMixin, Base):
    __tablename__ = "bulk_import_jobs"
    __table_args__ = (UniqueConstraint("institution_id", "file_sha256"),)  # idempotency
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    import_type: Mapped[str] = mapped_column(String(24), default="student_enrolments")
    original_filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    # previewed | confirmed | failed | cancelled
    status: Mapped[str] = mapped_column(String(16), default="previewed", index=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class BulkImportRow(IdMixin, Base):
    __tablename__ = "bulk_import_rows"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bulk_import_jobs.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    raw: Mapped[dict] = mapped_column(JSON)
    # valid | invalid | duplicate | imported
    status: Mapped[str] = mapped_column(String(12), index=True)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    enrolment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("student_enrolments.id"), nullable=True
    )
