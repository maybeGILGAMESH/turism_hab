from uuid import uuid4

from fastapi.testclient import TestClient

from app import app
from settings import get_settings

client = TestClient(app)


def test_health_is_explicit_when_index_missing():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}


def test_catalog_contract():
    response = client.get("/api/objects")
    assert response.status_code == 200
    objects = response.json()["objects"]
    assert len(objects) == 44
    assert {"id", "slug", "name", "category", "municipality", "coordinates"} <= objects[0].keys()


def test_route_contract():
    response = client.post(
        "/api/plan-route", json={"latitude": 48.48, "longitude": 135.071, "limit": 5}
    )
    assert response.status_code == 200
    assert len(response.json()["route"]) == 5


def test_public_registration_cannot_create_admin():
    response = client.post(
        "/auth/register",
        json={
            "email": "visitor-contract@example.com",
            "password": "secure-password-123",
            "role": "admin",
        },
    )
    assert response.status_code in {200, 409}
    if response.status_code == 200:
        assert response.json()["user"]["role"] == "user"


def test_invalid_upload_is_rejected():
    response = client.post(
        "/api/recognize", files={"file": ("bad.txt", b"not image", "text/plain")}
    )
    assert response.status_code == 415


def test_auth_lifecycle_and_history_contract():
    email = f"visitor-{uuid4().hex}@example.com"
    password = "secure-password-123"
    created = client.post("/auth/register", json={"email": email, "password": password})
    assert created.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200
    history = client.get("/auth/me/recognized", headers=headers)
    assert history.status_code == 200
    assert history.json() == []
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_regular_user_cannot_reindex():
    email = f"visitor-{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register", json={"email": email, "password": "secure-password-123"}
    )
    assert response.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": "secure-password-123"})
    token = login.json()["access_token"]
    denied = client.post("/api/admin/reindex", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403


def test_bootstrap_admin_login():
    settings = get_settings()
    response = client.post(
        "/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
