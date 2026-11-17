import uuid
from datetime import timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import utcnow
from app.core.exceptions import Forbidden, TooManyRequests, Unauthorized, ValidationFailed
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    password_policy_errors,
    verify_password,
)
from app.modules.audit import service as audit
from app.modules.auth.models import LoginAttempt, PasswordResetToken, RefreshSession
from app.modules.users.models import User

# A valid Argon2id hash of a random string, verified when the account doesn't exist so that
# response time doesn't reveal which identifiers are registered.
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalisation")


def _issue_session(db: Session, user: User, ip: str | None, ua: str | None) -> tuple[str, str, int]:
    s = get_settings()
    raw_refresh = new_refresh_token()
    session = RefreshSession(
        user_id=user.id, token_hash=hash_token(raw_refresh),
        expires_at=utcnow() + timedelta(days=s.refresh_token_days),
        ip_address=ip, user_agent=(ua or "")[:255] or None,
    )
    db.add(session)
    db.flush()
    return create_access_token(user.id, session.id), raw_refresh, s.access_token_minutes * 60


def login(db: Session, identifier: str, password: str, ip: str | None, ua: str | None):
    s = get_settings()
    ident = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(func.lower(User.email) == ident, func.lower(User.username) == ident)))

    def fail(reason: str, status: int = 401):
        db.add(LoginAttempt(identifier=ident[:254], user_id=getattr(user, "id", None), success=False, ip_address=ip))
        audit.record(db, "login_failed", actor=user, actor_label=ident[:160],
                     resource_type="user", resource_id=getattr(user, "id", None),
                     details={"reason": reason}, ip=ip)
        db.flush()
        _detect_failed_login_burst(db, ident, user, ip)
        db.commit()
        if status == 429:
            raise TooManyRequests("Account temporarily locked due to repeated failed logins")
        raise Unauthorized("Invalid credentials")

    if user is None:
        verify_password(password, _DUMMY_HASH)
        fail("unknown_user")
    assert user is not None
    if user.locked_until and user.locked_until > utcnow():
        fail("locked", 429)
    if not user.is_active:
        verify_password(password, user.password_hash)
        fail("inactive")
    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= s.max_failed_logins:
            user.locked_until = utcnow() + timedelta(minutes=s.lockout_minutes)
            user.failed_login_count = 0
            audit.security_event(db, "account_locked", "high", actor_id=user.id,
                                 actor_label=user.username, ip=ip,
                                 details={"lockout_minutes": s.lockout_minutes})
        fail("bad_password")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    db.add(LoginAttempt(identifier=ident[:254], user_id=user.id, success=True, ip_address=ip))
    access, refresh, ttl = _issue_session(db, user, ip, ua)
    audit.record(db, "login", actor=user, resource_type="user", resource_id=user.id, ip=ip)
    db.commit()
    return access, refresh, ttl, user


def _detect_failed_login_burst(db: Session, ident: str, user: User | None, ip: str | None) -> None:
    since = utcnow() - timedelta(minutes=audit.WINDOW_MINUTES)
    n = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.identifier == ident, LoginAttempt.success.is_(False), LoginAttempt.created_at >= since)) or 0
    if n >= audit.FAILED_LOGIN_THRESHOLD and n % audit.FAILED_LOGIN_THRESHOLD == 0:
        audit.security_event(db, "repeated_failed_logins", "medium",
                             actor_id=getattr(user, "id", None), actor_label=ident[:160], ip=ip,
                             details={"attempts": n, "window_min": audit.WINDOW_MINUTES})


def refresh(db: Session, raw_token: str, ip: str | None, ua: str | None):
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token)))
    if session is None:
        raise Unauthorized("Invalid refresh token")
    user = db.get(User, session.user_id)
    if session.revoked_at is not None:
        # A rotated token was replayed: assume theft and kill every session for this user.
        db.execute(update(RefreshSession).where(
            RefreshSession.user_id == session.user_id, RefreshSession.revoked_at.is_(None)
        ).values(revoked_at=utcnow()))
        audit.security_event(db, "refresh_token_reuse", "high", actor_id=session.user_id,
                             actor_label=getattr(user, "username", None), ip=ip)
        db.commit()
        raise Unauthorized("Invalid refresh token")
    if session.expires_at < utcnow() or user is None or not user.is_active:
        raise Unauthorized("Session expired")
    access, new_raw, ttl = _issue_session(db, user, ip, ua)
    new_session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_token(new_raw)))
    session.revoked_at = utcnow()
    session.replaced_by = new_session.id if new_session else None
    db.commit()
    return access, new_raw, ttl, user


def logout(db: Session, user: User, session_id: uuid.UUID, ip: str | None) -> None:
    session = db.get(RefreshSession, session_id)
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
    audit.record(db, "logout", actor=user, resource_type="user", resource_id=user.id, ip=ip)
    db.commit()


def change_password(db: Session, user: User, current: str, new: str, keep_session: uuid.UUID, ip: str | None) -> None:
    if not verify_password(current, user.password_hash):
        raise Forbidden("Current password is incorrect")
    errs = password_policy_errors(new)
    if errs:
        raise ValidationFailed("; ".join(errs))
    if verify_password(new, user.password_hash):
        raise ValidationFailed("New password must differ from the current password")
    user.password_hash = hash_password(new)
    user.must_change_password = False
    db.execute(update(RefreshSession).where(
        RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None),
        RefreshSession.id != keep_session).values(revoked_at=utcnow()))
    audit.record(db, "password_changed", actor=user, resource_type="user", resource_id=user.id, ip=ip)
    db.commit()


def request_reset(db: Session, email: str, ip: str | None) -> str | None:
    """Always behaves the same to the caller. Returns the raw token only so the router can expose
    it in demo mode (there is no email provider in this prototype)."""
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    raw = None
    if user and user.is_active:
        raw = new_refresh_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(raw),
                                  expires_at=utcnow() + timedelta(minutes=30)))
        audit.record(db, "password_reset_requested", actor=user, resource_type="user", resource_id=user.id, ip=ip)
    db.commit()
    return raw


def confirm_reset(db: Session, raw_token: str, new_password: str, ip: str | None) -> None:
    tok = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw_token)))
    if tok is None or tok.used_at is not None or tok.expires_at < utcnow():
        raise ValidationFailed("Reset link is invalid or has expired")
    errs = password_policy_errors(new_password)
    if errs:
        raise ValidationFailed("; ".join(errs))
    user = db.get(User, tok.user_id)
    assert user is not None
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    tok.used_at = utcnow()
    db.execute(update(RefreshSession).where(
        RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    audit.record(db, "password_reset_completed", actor=user, resource_type="user", resource_id=user.id, ip=ip)
    db.commit()
