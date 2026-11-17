from sqlalchemy import select

from app.modules.audit.models import AuditLog, SecurityEvent
from app.modules.institutions.models import Institution
from app.modules.users.models import User

NEW_PW = "Fresh-Start-2026!"


def _user_id(db, username):
    return str(db.scalar(select(User.id).where(User.username == username)))


def _inst_id(db, code):
    return str(db.scalar(select(Institution.id).where(Institution.code == code)))


def _new_user(role, **extra):
    return {"email": "new.person@example.com", "username": "new.person", "full_name": "New Person",
            "password": NEW_PW, "roles": [role], **extra}


def test_institution_staff_cannot_use_admin_endpoints(client, auth):
    h = auth("inst.staff.pune")
    assert client.get("/api/v1/users", headers=h).status_code == 403
    assert client.post("/api/v1/users", headers=h, json=_new_user("institution_staff")).status_code == 403


def test_permission_denied_is_audited_and_repeated_denials_raise_security_event(client, auth, db):
    h = auth("inst.staff.pune")
    for _ in range(5):
        assert client.get("/api/v1/users", headers=h).status_code == 403
    assert db.scalars(select(AuditLog).where(AuditLog.action == "permission_denied")).all()
    assert "repeated_permission_failures" in db.scalars(select(SecurityEvent.event_type)).all()


def test_user_cannot_change_own_role_to_super_admin(client, auth, db):
    # Even the highest-privileged *institution* user cannot self-promote.
    h = auth("inst.admin.pune")
    me = _user_id(db, "inst.admin.pune")
    r = client.put(f"/api/v1/users/{me}/roles", headers=h, json={"roles": ["super_admin"]})
    assert r.status_code == 403
    roles = {r.code for r in db.get(User, __import__("uuid").UUID(me)).roles}
    assert roles == {"institution_admin"}


def test_super_admin_cannot_change_own_roles_either(client, auth, db):
    h = auth("superadmin")
    me = _user_id(db, "superadmin")
    assert client.put(f"/api/v1/users/{me}/roles", headers=h, json={"roles": ["aicte_admin"]}).status_code == 403


def test_aicte_admin_cannot_create_super_admin_or_aicte_admin(client, auth, db):
    h = auth("aicte.admin")
    for role in ("super_admin", "aicte_admin"):
        r = client.post("/api/v1/users", headers=h, json=_new_user(role))
        assert r.status_code == 403, role
    assert "privilege_escalation_attempt" in db.scalars(select(SecurityEvent.event_type)).all()
    # ...but can create a state admin
    ok = client.post("/api/v1/users", headers=h, json=_new_user("state_admin", state_code="MH"))
    assert ok.status_code == 201


def test_super_admin_can_create_aicte_admin(client, auth):
    r = client.post("/api/v1/users", headers=auth("superadmin"), json=_new_user("aicte_admin"))
    assert r.status_code == 201
    assert r.json()["roles"] == ["aicte_admin"]


def test_institution_admin_creates_staff_only_inside_own_institution(client, auth, db):
    h = auth("inst.admin.pune")
    # Tries to smuggle the user into Nagpur: server forces the caller's own institution
    r = client.post("/api/v1/users", headers=h,
                    json=_new_user("institution_staff", institution_id=_inst_id(db, "DEMO-ENG-002")))
    assert r.status_code == 201
    assert r.json()["institution_id"] == _inst_id(db, "DEMO-PGDM-001")
    # cannot mint another admin or any platform role
    assert client.post("/api/v1/users", headers=h,
                       json={**_new_user("institution_admin"), "username": "x.y", "email": "x@y.com"}).status_code == 403


def test_institution_admin_cannot_see_or_manage_other_institution_users(client, auth, db):
    h = auth("inst.admin.pune")
    listed = client.get("/api/v1/users", headers=h).json()
    usernames = {u["email"].split("@")[0] for u in listed["items"]}
    assert usernames == {"inst.admin.pune", "inst.staff.pune"}
    other = _user_id(db, "inst.staff.nagpur")
    assert client.get(f"/api/v1/users/{other}", headers=h).status_code == 404  # existence not leaked
    assert client.patch(f"/api/v1/users/{other}/status", headers=h, json={"is_active": False}).status_code == 404


def test_deactivating_user_revokes_sessions(client, auth, db):
    staff_h = auth("inst.staff.pune")
    assert client.get("/api/v1/auth/me", headers=staff_h).status_code == 200
    target = _user_id(db, "inst.staff.pune")
    r = client.patch(f"/api/v1/users/{target}/status", headers=auth("inst.admin.pune"), json={"is_active": False})
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=staff_h).status_code == 401


def test_duplicate_username_rejected_and_weak_password_rejected(client, auth):
    h = auth("superadmin")
    assert client.post("/api/v1/users", headers=h, json=_new_user("verification_officer")).status_code == 201
    assert client.post("/api/v1/users", headers=h, json=_new_user("verification_officer")).status_code == 409
    weak = {**_new_user("verification_officer"), "username": "weak.one", "email": "w@e.com", "password": "short"}
    assert client.post("/api/v1/users", headers=h, json=weak).status_code == 422


def test_state_admin_limited_to_own_state_users_and_readonly(client, auth, db):
    h = auth("state.mh")
    r = client.get("/api/v1/users", headers=h)
    assert r.status_code == 200
    assert all(u["state_code"] == "MH" for u in r.json()["items"])
    assert client.post("/api/v1/users", headers=h, json=_new_user("institution_staff")).status_code == 403


def test_user_creation_and_role_changes_are_audited_without_secrets(client, auth, db):
    client.post("/api/v1/users", headers=auth("superadmin"), json=_new_user("verification_officer"))
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "user_created")).first()
    assert entry is not None
    blob = str(entry.details) + str(entry.actor_label)
    assert NEW_PW not in blob


def test_audit_log_has_no_mutation_endpoints(client, auth):
    h = auth("superadmin")
    # The platform exposes no write/delete route for audit logs at all
    for method in ("post", "put", "patch", "delete"):
        r = getattr(client, method)("/api/v1/audit-logs", headers=h)
        assert r.status_code in (404, 405)


def test_security_headers_and_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-request-id"]
