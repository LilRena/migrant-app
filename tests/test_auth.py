"""Tests for Stage 1: auth endpoints and role guards."""
from datetime import datetime, timedelta
from jose import jwt
from app.config import settings


# helpers

def register(client, email="test@example.com", password="secret123", full_name="Test User"):
    return client.post("/auth/register", json={
        "email": email, "password": password, "full_name": full_name
    })


def login(client, email="test@example.com", password="secret123"):
    return client.post("/auth/login", json={"email": email, "password": password})


# --- register ---

def test_register_returns_user(client):
    r = register(client)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "student"
    assert "id" in data


def test_register_role_is_always_student(client):
    r = register(client, email="a@example.com")
    assert r.json()["role"] == "student"


def test_register_duplicate_email_returns_400(client):
    register(client, email="dup@example.com")
    r = register(client, email="dup@example.com")
    assert r.status_code == 400


# --- login ---

def test_login_returns_token(client):
    register(client, email="login@example.com")
    r = login(client, email="login@example.com")
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["token_type"] == "bearer"


def test_wrong_password_returns_401(client):
    register(client, email="wp@example.com", password="correct")
    r = login(client, email="wp@example.com", password="wrong")
    assert r.status_code == 401


def test_wrong_email_returns_401(client):
    r = login(client, email="nobody@example.com", password="any")
    assert r.status_code == 401


def test_wrong_email_and_wrong_password_same_message(client):
    """Both bad-email and bad-password must return the identical error detail."""
    register(client, email="same@example.com", password="correct")
    r_bad_email = login(client, email="noone@example.com", password="x")
    r_bad_pass = login(client, email="same@example.com", password="wrong")
    assert r_bad_email.status_code == r_bad_pass.status_code == 401
    assert r_bad_email.json()["detail"] == r_bad_pass.json()["detail"]


# --- /auth/me ---

def test_me_returns_current_user(client):
    register(client, email="me@example.com")
    token = login(client, email="me@example.com").json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_me_without_token_returns_401(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


# --- expired token ---

def test_expired_token_returns_401(client):
    register(client, email="exp@example.com")
    # create a token that expired 1 second ago
    expired_payload = {
        "sub": "exp@example.com",
        "exp": datetime.utcnow() - timedelta(seconds=1),
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401


# --- role guard ---

def test_student_on_staff_endpoint_returns_403(client):
    register(client, email="student@example.com")
    token = login(client, email="student@example.com").json()["access_token"]
    r = client.get("/staff/students", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
