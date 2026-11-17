from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.modules.audit.models import AuditLog, SecurityEvent
from app.modules.users.models import User
from tests.conftest import DEMO_PASSWORD, login


def test_passwords_are_hashed_with_argon2id(db):
    u = db.scalar(select(User).where(User.username == "superadmin"))
    assert u.password_hash.startswith("$argon2id$")
    assert DEMO_PASSWORD not in u.password_hash
    assert verify_password(DEMO_PASSWORD, u.password_hash)
    assert not verify_password("wrong", u.password_hash)
    assert hash_password("x") != hash_password("x")  # salted


def test_all_demo_roles_can_login(client):
    for name in ["superadmin", "aicte.admin", "state.mh", "inst.admin.pune",
                 "inst.staff.pune", "verifier.1"]:
        assert login(client, name).status_code == 200, name


def test_login_by_email_and_me_endpoint(client):
    r = login(client, "superadmin@demo.apaar-nexus.example")
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["roles"] == ["super_admin"]
    assert "audit:read" in me.json()["permissions"]


def test_bad_credentials_generic_error(client):
    a = login(client, "superadmin", "nope-nope-nope")
    b = login(client, "ghost-user", "nope-nope-nope")
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]  # no user enumeration


def test_protected_routes_require_auth(client):
    assert client.get("/api/v1/users").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/users", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_lockout_after_repeated_failures_and_security_event(client, db):
    for _ in range(5):
        assert login(client, "inst.staff.pune", "Wrong-password-1!").status_code == 401
    r = login(client, "inst.staff.pune", DEMO_PASSWORD)  # correct password, but locked now
    assert r.status_code == 429
    events = db.scalars(select(SecurityEvent.event_type)).all()
    assert "account_locked" in events
    assert db.scalars(select(AuditLog).where(AuditLog.action == "login_failed")).first() is not None


def test_refresh_rotation_and_reuse_detection(client, db):
    tokens = login(client, "aicte.admin").json()
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r1.status_code == 200
    new = r1.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    # replaying the old refresh token is treated as theft: everything is revoked
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": new["refresh_token"]}).status_code == 401
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new['access_token']}"})
    assert me.status_code == 401
    assert "refresh_token_reuse" in db.scalars(select(SecurityEvent.event_type)).all()


def test_logout_invalidates_session(client):
    t = login(client, "verifier.1").json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 204
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_password_change_policy_and_session_revocation(client):
    t1 = login(client, "inst.admin.pune").json()
    t2 = login(client, "inst.admin.pune").json()
    h1 = {"Authorization": f"Bearer {t1['access_token']}"}
    h2 = {"Authorization": f"Bearer {t2['access_token']}"}
    weak = client.post("/api/v1/auth/password/change", headers=h1,
                       json={"current_password": DEMO_PASSWORD, "new_password": "weakpassword"})
    assert weak.status_code == 422
    bad = client.post("/api/v1/auth/password/change", headers=h1,
                      json={"current_password": "incorrect-pass", "new_password": "Brand-New-Pass1!"})
    assert bad.status_code == 403
    ok = client.post("/api/v1/auth/password/change", headers=h1,
                     json={"current_password": DEMO_PASSWORD, "new_password": "Brand-New-Pass1!"})
    assert ok.status_code == 204
    assert client.get("/api/v1/auth/me", headers=h1).status_code == 200   # current session kept
    assert client.get("/api/v1/auth/me", headers=h2).status_code == 401   # other sessions revoked
    assert login(client, "inst.admin.pune", "Brand-New-Pass1!").status_code == 200


def test_password_reset_flow_single_use(client):
    r = client.post("/api/v1/auth/password/reset", json={"email": "verifier.1@demo.apaar-nexus.example"})
    assert r.status_code == 202
    tok = r.json()["demo_reset_token"]
    # unknown email gets the same response shape and no token
    r2 = client.post("/api/v1/auth/password/reset", json={"email": "nobody@example.com"})
    assert r2.status_code == 202 and "demo_reset_token" not in r2.json()
    assert client.post("/api/v1/auth/password/reset/confirm",
                       json={"token": tok, "new_password": "Reset-Pass-2026!"}).status_code == 204
    assert client.post("/api/v1/auth/password/reset/confirm",
                       json={"token": tok, "new_password": "Another-Pass-2026!"}).status_code == 422
    assert login(client, "verifier.1", "Reset-Pass-2026!").status_code == 200


def test_error_responses_do_not_leak_internals(client, auth):
    r = client.get("/api/v1/users/not-a-uuid", headers=auth("superadmin"))
    assert r.status_code == 422
    assert "Traceback" not in r.text
