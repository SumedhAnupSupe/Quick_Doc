import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import Forbidden
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserOut, UserRoles, UserStatus, UserUpdate
from app.shared.dependencies import Principal, require
from app.shared.pagination import Page, PageParams, paginate
from app.shared.ratelimit import client_ip

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserOut])
def list_users(q: str | None = Query(None, max_length=100), params: PageParams = Depends(),
               p: Principal = Depends(require("user:read")), db: Session = Depends(get_db)):
    stmt = service.scoped_query(p)
    if q:
        like = f"%{q.lower()}%"
        from sqlalchemy import func
        stmt = stmt.where(or_(func.lower(User.full_name).like(like), func.lower(User.email).like(like),
                              func.lower(User.username).like(like)))
    rows, total = paginate(db, stmt.order_by(User.full_name), params)
    return Page(items=[service.to_out(db, u) for u in rows], total=total, page=params.page,
                page_size=params.page_size)


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, request: Request, p: Principal = Depends(require("user:manage")),
                db: Session = Depends(get_db)):
    return service.to_out(db, service.create_user(db, p, body, client_ip(request)))


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, p: Principal = Depends(require("user:read")), db: Session = Depends(get_db)):
    return service.to_out(db, service.get_visible(db, p, user_id))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, request: Request,
                p: Principal = Depends(require("user:read")), db: Session = Depends(get_db)):
    target = service.get_visible(db, p, user_id)
    # users may edit their own profile; managing others needs user:manage
    if target.id != p.user.id and "user:manage" not in p.permissions:
        raise Forbidden("You do not have permission to perform this action")
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.email is not None:
        target.email = body.email.lower()
    from app.modules.audit import service as audit
    audit.record(db, "user_updated", actor=p.user, resource_type="user", resource_id=target.id,
                 ip=client_ip(request))
    db.commit()
    return service.to_out(db, target)


@router.patch("/{user_id}/status", response_model=UserOut)
def set_status(user_id: uuid.UUID, body: UserStatus, request: Request,
               p: Principal = Depends(require("user:manage")), db: Session = Depends(get_db)):
    target = service.get_visible(db, p, user_id)
    return service.to_out(db, service.set_status(db, p, target, body.is_active, client_ip(request)))


@router.put("/{user_id}/roles", response_model=UserOut)
def set_roles(user_id: uuid.UUID, body: UserRoles, request: Request,
              p: Principal = Depends(require("user:manage")), db: Session = Depends(get_db)):
    target = service.get_visible(db, p, user_id)
    return service.to_out(db, service.update_roles(db, p, target, body.roles, client_ip(request)))
