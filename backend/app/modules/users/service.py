import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.exceptions import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.permissions import INSTITUTION_ROLES
from app.core.permissions import Role as RoleEnum
from app.core.security import hash_password, password_policy_errors
from app.modules.audit import service as audit
from app.modules.auth.models import RefreshSession
from app.modules.institutions.models import Institution, InstitutionUser
from app.modules.users.models import Role, User
from app.shared.dependencies import Principal


def assignable_roles(p: Principal) -> set[str]:
    """Which roles the caller may grant. Prevents privilege escalation."""
    if p.has_role(RoleEnum.SUPER_ADMIN):
        return {r.value for r in RoleEnum}
    if p.has_role(RoleEnum.AICTE_ADMIN):  # only the Super Admin manages AICTE/Super admins
        return {RoleEnum.STATE_ADMIN, RoleEnum.INSTITUTION_ADMIN, RoleEnum.INSTITUTION_STAFF,
                RoleEnum.VERIFICATION_OFFICER}
    if p.has_role(RoleEnum.INSTITUTION_ADMIN):
        return {RoleEnum.INSTITUTION_STAFF.value}
    return set()


def _norm(roles: set) -> set[str]:
    return {r.value if hasattr(r, "value") else r for r in roles}


def to_out(db: Session, u: User) -> dict:
    inst = db.scalar(select(InstitutionUser.institution_id).where(InstitutionUser.user_id == u.id))
    return {"id": u.id, "email": u.email, "username": u.username, "full_name": u.full_name,
            "is_active": u.is_active, "state_code": u.state_code,
            "roles": sorted(r.code for r in u.roles), "institution_id": inst}


def scoped_query(p: Principal):
    stmt = select(User)
    if p.is_platform:
        return stmt
    if p.is_institution_user:
        return stmt.join(InstitutionUser, InstitutionUser.user_id == User.id).where(
            InstitutionUser.institution_id == p.institution_id)
    if p.has_role(RoleEnum.STATE_ADMIN):
        return stmt.where(User.state_code == p.state_code)
    return stmt.where(User.id == p.user.id)


def get_visible(db: Session, p: Principal, user_id: uuid.UUID) -> User:
    u = db.scalar(scoped_query(p).where(User.id == user_id))
    if u is None:
        raise NotFound("User not found")  # 404 (not 403) so existence isn't leaked across scopes
    return u


def _roles(db: Session, codes: list[str]) -> list[Role]:
    rows = db.scalars(select(Role).where(Role.code.in_(set(codes)))).all()
    if len(rows) != len(set(codes)):
        raise ValidationFailed("Unknown role supplied")
    return list(rows)


def create_user(db: Session, p: Principal, data, ip: str | None) -> User:
    allowed = _norm(assignable_roles(p))
    if not set(data.roles) <= allowed:
        audit.record(db, "role_escalation_blocked", actor=p.user, resource_type="user",
                     details={"requested": sorted(data.roles)}, ip=ip)
        audit.security_event(db, "privilege_escalation_attempt", "high", actor_id=p.user.id,
                             actor_label=p.user.username, ip=ip, details={"requested": sorted(data.roles)})
        db.commit()
        raise Forbidden("You cannot assign one or more of the requested roles")
    errs = password_policy_errors(data.password)
    if errs:
        raise ValidationFailed("; ".join(errs))
    if db.scalar(select(User.id).where(or_(User.email == data.email.lower(), User.username == data.username))):
        raise Conflict("A user with that email or username already exists")

    needs_inst = bool(set(data.roles) & _norm(INSTITUTION_ROLES))
    inst_id = data.institution_id
    if p.is_institution_user:
        inst_id = p.institution_id  # institution admins can only create users in their own institution
    if needs_inst:
        if inst_id is None or db.get(Institution, inst_id) is None:
            raise ValidationFailed("institution_id is required for institution roles")
    elif inst_id is not None:
        raise ValidationFailed("institution_id is only valid for institution roles")
    if RoleEnum.STATE_ADMIN.value in data.roles and not data.state_code:
        raise ValidationFailed("state_code is required for State Admin")

    u = User(email=data.email.lower(), username=data.username, full_name=data.full_name,
             password_hash=hash_password(data.password), must_change_password=True,
             state_code=data.state_code)
    u.roles = _roles(db, data.roles)
    db.add(u)
    db.flush()
    if needs_inst:
        db.add(InstitutionUser(user_id=u.id, institution_id=inst_id))
    audit.record(db, "user_created", actor=p.user, resource_type="user", resource_id=u.id,
                 institution_id=inst_id, details={"roles": sorted(data.roles)}, ip=ip)
    db.commit()
    return u


def update_roles(db: Session, p: Principal, target: User, roles: list[str], ip: str | None) -> User:
    if target.id == p.user.id:
        raise Forbidden("You cannot change your own roles")
    allowed = _norm(assignable_roles(p))
    current = {r.code for r in target.roles}
    # caller must be allowed to grant the new set AND to manage the target's existing roles
    if not set(roles) <= allowed or not current <= allowed:
        audit.security_event(db, "privilege_escalation_attempt", "high", actor_id=p.user.id,
                             actor_label=p.user.username, ip=ip, details={"target": str(target.id)})
        db.commit()
        raise Forbidden("You cannot assign one or more of the requested roles")
    before = sorted(current)
    target.roles = _roles(db, roles)
    audit.record(db, "roles_changed", actor=p.user, resource_type="user", resource_id=target.id,
                 details={"before": before, "after": sorted(roles)}, ip=ip)
    db.commit()
    return target


def set_status(db: Session, p: Principal, target: User, active: bool, ip: str | None) -> User:
    if target.id == p.user.id:
        raise Forbidden("You cannot change your own status")
    if not {r.code for r in target.roles} <= _norm(assignable_roles(p)):
        raise Forbidden("You cannot manage this user")
    target.is_active = active
    if not active:
        db.execute(update(RefreshSession).where(
            RefreshSession.user_id == target.id, RefreshSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    audit.record(db, "user_activated" if active else "user_deactivated", actor=p.user,
                 resource_type="user", resource_id=target.id, ip=ip)
    db.commit()
    return target
