import uuid
from datetime import date

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, IdMixin, TimestampMixin


class DocumentType(IdMixin, TimestampMixin, Base):
    """Admin-managed catalogue. New document types need NO schema change."""

    __tablename__ = "document_types"
    code: Mapped[str] = mapped_column(String(48), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    vault_type: Mapped[str] = mapped_column(String(12), index=True)  # central | state
    issuing_authority: Mapped[str] = mapped_column(String(160), default="")
    state_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    # Empty list => applies to all institution levels.
    applicable_levels: Mapped[list] = mapped_column(JSON, default=list)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_formats: Mapped[list] = mapped_column(JSON, default=lambda: ["pdf", "jpg", "png"])
    max_size_kb: Mapped[int] = mapped_column(Integer, default=2048)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PersonDocument(IdMixin, TimestampMixin, Base):
    """Exists only for documents actually submitted/registered. File bytes are NOT stored here."""

    __tablename__ = "person_documents"
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    document_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_types.id"), index=True)
    vault_type: Mapped[str] = mapped_column(String(12))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)  # opaque; never exposed
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    issuing_authority: Mapped[str | None] = mapped_column(String(160), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # submitted | correction_requested | approved | rejected | superseded
    submission_status: Mapped[str] = mapped_column(String(24), default="submitted", index=True)
    verification_status: Mapped[str] = mapped_column(String(24), default="pending")
    replaces_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("person_documents.id"), nullable=True
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )  # the institution that submitted it (scoping)

    document_type: Mapped[DocumentType] = relationship(lazy="joined")
