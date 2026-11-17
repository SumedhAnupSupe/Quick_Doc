"""Authentication + authorization dependencies.

Every protected API goes through `current_user` and `require(...)`. Data scoping (institution/state
isolation) is expressed via `Scope`, which routers/services apply to their queries.
"""
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import Forbidden, Unauthorized
from app.core.permissions import INSTITUTION_ROLES, PLATFORM_ROLES, Role
from app.core.security import decode_access_token
from app.modules.audit import service as audit
from app.modules.auth.models import RefreshSession
from app.modules.institutions.models import InstitutionUser
from app.modules.users.models import User
from app.shared.ratelimit import client_ip

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User
    roles: set[str]
    permissions: set[str]
    institution_id: uuid.UUID | None
    state_code: str | None
    session_id: uuid.UUID

    def has_role(self, *roles: Role) -> bool:
        return any(r.value in self.roles for r in roles)

    @property
    def is_platform(self) -> bool:
        return any(r.value in self.roles for r in PLATFORM_ROLES)

    @property
    def is_institution_user(self) -> bool:
        return any(r.value in self.roles for r in INSTITUTION_ROLES)


def current_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if creds is None:
        raise Unauthorized("Authentication required")
    try:
        payload = decode_access_token(creds.credentials)
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["sid"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise Unauthorized("Invalid or expired token") from None

    session = db.get(RefreshSession, session_id)
    if session is None or session.revoked_at is not None or session.user_id != user_id:
        raise Unauthorized("Session is no longer valid")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Account is disabled")

    roles = {r.code for r in user.roles}
    perms = {p.code for r in user.roles for p in r.permissions}
    inst_id = db.scalar(select(InstitutionUser.institution_id).where(InstitutionUser.user_id == user.id))
    p = Principal(user, roles, perms, inst_id, user.state_code, session_id)
    request.state.principal = p
    return p


def require(*permissions: str):
    """Dependency factory: caller must hold ALL listed permissions."""

    def dep(request: Request, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
        missing = [x for x in permissions if x not in p.permissions]
        if missing:
            audit.permission_denied(db, p.user, missing[0], path=request.url.path, ip=client_ip(request))
            db.commit()  # persist the denial even though we raise
            raise Forbidden("You do not have permission to perform this action")
        return p

    return dep


def ensure_institution_access(p: Principal, institution_id: uuid.UUID | None) -> None:
    """Institution users may only touch their own institution."""
    if p.is_institution_user and p.institution_id != institution_id:
        raise Forbidden("Access to this institution's data is not permitted")


def ensure_state_access(p: Principal, state_code: str | None) -> None:
    """State admins are limited to their assigned state."""
    if p.has_role(Role.STATE_ADMIN) and not p.is_platform and p.state_code != state_code:
        raise Forbidden("Access outside your assigned state is not permitted")
