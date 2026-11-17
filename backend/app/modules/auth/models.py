import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, IdMixin, UTCDateTime, utcnow


class RefreshSession(IdMixin, Base):
    """One row per login session. Refresh tokens are rotated; only a digest is stored."""

    __tablename__ = "refresh_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class LoginAttempt(IdMixin, Base):
    __tablename__ = "login_attempts"
    identifier: Mapped[str] = mapped_column(String(254), index=True)  # email/username as typed
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)


class PasswordResetToken(IdMixin, Base):
    """Prototype reset flow: no email provider is integrated; only a digest is stored."""

    __tablename__ = "password_reset_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
