import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.database import Base, get_db
from app.main import app
from app.seed import DEMO_PASSWORD, seed_demo
from app.shared.ratelimit import login_limiter


@pytest.fixture()
def engine():
    from sqlalchemy import create_engine

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def SessionLocal(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def db(SessionLocal):
    with SessionLocal() as s:
        seed_demo(s)
        yield s


@pytest.fixture()
def client(SessionLocal, db):
    def _get_db():
        with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db
    login_limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, username: str, password: str = DEMO_PASSWORD):
    r = client.post("/api/v1/auth/login", json={"identifier": username, "password": password})
    return r


@pytest.fixture()
def auth(client):
    """auth('username') -> headers with a valid bearer token."""
    def _auth(username: str):
        r = login(client, username)
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _auth
