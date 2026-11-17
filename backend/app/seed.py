"""Seeding. `seed_rbac` is idempotent and safe everywhere; `seed_demo` is synthetic and dev-only."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS
from app.core.permissions import Role as RoleEnum
from app.core.security import hash_password
from app.modules.academics.models import SeatCategory
from app.modules.institutions.models import Institution, InstitutionType, InstitutionUser
from app.modules.users.models import Permission, Role, User

ROLE_NAMES = {
    RoleEnum.SUPER_ADMIN: "Super Admin", RoleEnum.AICTE_ADMIN: "AICTE Admin",
    RoleEnum.STATE_ADMIN: "State Admin", RoleEnum.INSTITUTION_ADMIN: "Institution Admin",
    RoleEnum.INSTITUTION_STAFF: "Institution Staff", RoleEnum.VERIFICATION_OFFICER: "Verification Officer",
}
INSTITUTION_TYPES = [
    ("10th", "10th-level institution", "10th"), ("12th", "12th-level institution", "12th"),
    ("graduation", "Graduation-level institution", "graduation"),
    ("postgraduation", "Postgraduation-level institution", "postgraduation"),
]
SEAT_CATEGORIES = [
    ("SUPERNUMERARY", "Supernumerary"), ("NRI", "NRI"), ("OCI", "OCI"),
    ("FOREIGN", "Foreign National"),
]

# Development-only, clearly synthetic credentials (documented in README; never used in production).
DEMO_PASSWORD = "Demo@12345!"


def seed_rbac(db: Session) -> None:
    perms = {p.code: p for p in db.scalars(select(Permission))}
    for code, desc in PERMISSIONS.items():
        if code not in perms:
            perms[code] = Permission(code=code, description=desc)
            db.add(perms[code])
    roles = {r.code: r for r in db.scalars(select(Role))}
    for r in RoleEnum:
        if r.value not in roles:
            roles[r.value] = Role(code=r.value, name=ROLE_NAMES[r])
            db.add(roles[r.value])
    db.flush()
    for r, codes in ROLE_PERMISSIONS.items():
        roles[r.value].permissions = [perms[c] for c in sorted(codes)]
    for code, name, level in INSTITUTION_TYPES:
        if not db.scalar(select(InstitutionType.id).where(InstitutionType.code == code)):
            db.add(InstitutionType(code=code, name=name, level=level))
    for code, name in SEAT_CATEGORIES:
        if not db.scalar(select(SeatCategory.id).where(SeatCategory.code == code)):
            db.add(SeatCategory(code=code, name=name))
    db.commit()


def _user(db: Session, username: str, name: str, role: RoleEnum, *, state: str | None = None,
          institution: Institution | None = None) -> User:
    u = db.scalar(select(User).where(User.username == username))
    if u:
        return u
    u = User(username=username, email=f"{username}@demo.apaar-nexus.example", full_name=name,
             password_hash=hash_password(DEMO_PASSWORD), state_code=state)
    u.roles = [db.scalar(select(Role).where(Role.code == role.value))]
    db.add(u)
    db.flush()
    if institution:
        db.add(InstitutionUser(user_id=u.id, institution_id=institution.id))
    return u


def _institution(db: Session, code: str, name: str, type_code: str, district: str, status: str) -> Institution:
    inst = db.scalar(select(Institution).where(Institution.code == code))
    if inst:
        return inst
    t = db.scalar(select(InstitutionType).where(InstitutionType.code == type_code))
    inst = Institution(code=code, name=name, institution_type_id=t.id, state_code="MH", state="Maharashtra",
                       district=district, address=f"{district}, Maharashtra (synthetic)",
                       contact_email=f"{code.lower()}@demo.apaar-nexus.example",
                       approval_reference=f"AICTE/DEMO/{code}", approval_status=status,
                       registration_date=date(2024, 6, 1))
    db.add(inst)
    db.flush()
    return inst


def seed_demo(db: Session) -> None:
    s = get_settings()
    if s.is_production:
        raise RuntimeError("Refusing to seed demo data in production")
    seed_rbac(db)
    pune = _institution(db, "DEMO-PGDM-001", "Demo Institute of Management, Pune", "postgraduation", "Pune", "approved")
    nagpur = _institution(db, "DEMO-ENG-002", "Demo College of Engineering, Nagpur", "graduation", "Nagpur", "approved")
    _institution(db, "DEMO-ENG-003", "Demo Technical Campus, Nashik (pending)", "graduation", "Nashik", "pending")
    _user(db, "superadmin", "Sia Superadmin", RoleEnum.SUPER_ADMIN)
    _user(db, "aicte.admin", "Arjun AICTE-Admin", RoleEnum.AICTE_ADMIN)
    _user(db, "state.mh", "Meera State-Admin (MH)", RoleEnum.STATE_ADMIN, state="MH")
    _user(db, "inst.admin.pune", "Pranav Pune-Admin", RoleEnum.INSTITUTION_ADMIN, institution=pune)
    _user(db, "inst.staff.pune", "Priya Pune-Staff", RoleEnum.INSTITUTION_STAFF, institution=pune)
    _user(db, "inst.admin.nagpur", "Nikhil Nagpur-Admin", RoleEnum.INSTITUTION_ADMIN, institution=nagpur)
    _user(db, "inst.staff.nagpur", "Neha Nagpur-Staff", RoleEnum.INSTITUTION_STAFF, institution=nagpur)
    _user(db, "verifier.1", "Vikram Verifier", RoleEnum.VERIFICATION_OFFICER)
    db.commit()


if __name__ == "__main__":
    from app.core.database import get_sessionmaker

    with get_sessionmaker()() as session:
        seed_demo(session)
        print("Seeded RBAC + demo data (synthetic). Demo password for all demo users:", DEMO_PASSWORD)
