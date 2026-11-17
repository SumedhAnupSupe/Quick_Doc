"""Audit + security-event writers. Append-only: this module only ever INSERTs."""
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.modules.audit.models import AuditLog, SecurityEvent

_SENSITIVE_KEYS = ("password", "token", "otp", "secret", "authorization", "code", "content")

# Configurable thresholds for security monitoring.
FAILED_LOGIN_THRESHOLD = 5
PERMISSION_DENIED_THRESHOLD = 5
EXPORT_THRESHOLD = 10
WINDOW_MINUTES = 10


def sanitize(details: dict[str, Any] | None) -> dict[str, Any]:
    """Drop anything that looks like a credential/OTP/content from audit metadata."""
    out: dict[str, Any] = {}
    for k, v in (details or {}).items():
        if any(s in k.lower() for s in _SENSITIVE_KEYS):
            continue
        out[k] = v if isinstance(v, (str, int, float, bool, type(None), list, dict)) else str(v)
    return out


def mask_apaar(apaar_id: str | None) -> str | None:
    if not apaar_id:
        return apaar_id
    return "*" * max(len(apaar_id) - 4, 0) + apaar_id[-4:]


def record(
    db: Session,
    action: str,
    *,
    actor=None,
    actor_label: str | None = None,
    resource_type: str | None = None,
    resource_id: Any = None,
    institution_id: uuid.UUID | None = None,
    details: dict | None = None,
    correlation_id: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=getattr(actor, "id", None),
        actor_label=actor_label or getattr(actor, "username", None),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        institution_id=institution_id,
        details=sanitize(details),
        correlation_id=correlation_id,
        ip_address=ip,
    )
    db.add(entry)
    return entry


def security_event(
    db: Session,
    event_type: str,
    severity: str,
    *,
    actor_id: uuid.UUID | None = None,
    actor_label: str | None = None,
    ip: str | None = None,
    details: dict | None = None,
) -> SecurityEvent:
    ev = SecurityEvent(
        event_type=event_type, severity=severity, actor_id=actor_id,
        actor_label=actor_label, ip_address=ip, details=sanitize(details),
    )
    db.add(ev)
    return ev


def recent_audit_count(db: Session, action: str, actor_id: uuid.UUID, minutes: int = WINDOW_MINUTES) -> int:
    since = utcnow() - timedelta(minutes=minutes)
    return db.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == action, AuditLog.actor_id == actor_id, AuditLog.created_at >= since
        )
    ) or 0


def permission_denied(db: Session, user, permission: str, *, path: str | None, ip: str | None) -> None:
    """Audit a 403 and raise a security event when denials repeat."""
    record(db, "permission_denied", actor=user, resource_type="api",
           details={"permission": permission, "path": path}, ip=ip)
    db.flush()
    if recent_audit_count(db, "permission_denied", user.id) >= PERMISSION_DENIED_THRESHOLD:
        exists = db.scalar(
            select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.event_type == "repeated_permission_failures",
                SecurityEvent.actor_id == user.id, SecurityEvent.status == "open",
            )
        )
        if not exists:
            security_event(db, "repeated_permission_failures", "medium", actor_id=user.id,
                           actor_label=user.username, ip=ip,
                           details={"threshold": PERMISSION_DENIED_THRESHOLD, "window_min": WINDOW_MINUTES})
