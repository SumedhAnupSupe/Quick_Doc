from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenPair,
)
from app.shared.dependencies import Principal, current_principal
from app.shared.ratelimit import client_ip, login_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _pair(access: str, refresh: str, ttl: int, user) -> TokenPair:
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=ttl,
                     must_change_password=user.must_change_password)


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    login_limiter.check(ip or "unknown")
    a, r, ttl, user = service.login(db, body.identifier, body.password, ip, request.headers.get("user-agent"))
    return _pair(a, r, ttl, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    a, r, ttl, user = service.refresh(db, body.refresh_token, client_ip(request), request.headers.get("user-agent"))
    return _pair(a, r, ttl, user)


@router.post("/logout", status_code=204)
def logout(request: Request, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    service.logout(db, p.user, p.session_id, client_ip(request))


@router.post("/password/change", status_code=204)
def password_change(body: PasswordChange, request: Request, p: Principal = Depends(current_principal),
                    db: Session = Depends(get_db)):
    service.change_password(db, p.user, body.current_password, body.new_password, p.session_id, client_ip(request))


@router.post("/password/reset", status_code=202)
def password_reset(body: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    login_limiter.check(f"reset:{client_ip(request) or 'unknown'}")
    raw = service.request_reset(db, body.email, client_ip(request))
    resp: dict = {"detail": "If that account exists, a reset link has been issued."}
    s = get_settings()
    if raw and s.demo_mode and not s.is_production:
        resp["demo_reset_token"] = raw  # prototype only: there is no email provider
    return resp


@router.post("/password/reset/confirm", status_code=204)
def password_reset_confirm(body: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    service.confirm_reset(db, body.token, body.new_password, client_ip(request))


@router.get("/me", response_model=MeResponse)
def me(p: Principal = Depends(current_principal)):
    u = p.user
    return MeResponse(
        id=str(u.id), email=u.email, username=u.username, full_name=u.full_name,
        roles=sorted(p.roles), permissions=sorted(p.permissions),
        institution_id=str(p.institution_id) if p.institution_id else None,
        state_code=p.state_code, must_change_password=u.must_change_password,
    )
