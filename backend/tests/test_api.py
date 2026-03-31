"""Tests for core API endpoints — auth, health, public search."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ── Health Check ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── Auth Endpoints ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "StrongPass1",
        "full_name": "Test User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com",
        "password": "StrongPass1",
        "full_name": "User One",
    })
    response = await client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com",
        "password": "StrongPass1",
        "full_name": "User Two",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "short",
        "full_name": "Weak User",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "StrongPass1",
        "full_name": "Login User",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "StrongPass1",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": "StrongPass1",
        "full_name": "Wrong User",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "WrongPass1",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authorized(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "me@example.com",
        "password": "StrongPass1",
        "full_name": "Me User",
    })
    token = reg.json()["access_token"]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


# ── Public Search ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_public_search_empty(client: AsyncClient):
    response = await client.get("/api/v1/public/search?q=Nobody+Here")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_public_search_too_short(client: AsyncClient):
    response = await client.get("/api/v1/public/search?q=X")
    assert response.status_code == 422  # Validation error


# ── Admin Bootstrap (first user = admin) ─────────────────────────────────

@pytest.mark.asyncio
async def test_first_user_becomes_admin(client: AsyncClient):
    """The very first user registered should automatically be admin."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "founder@cloakhaven.com",
        "password": "StrongPass1",
        "full_name": "Founder",
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_admin"] is True


@pytest.mark.asyncio
async def test_second_user_not_admin(client: AsyncClient):
    """Subsequent users should NOT be admin."""
    await client.post("/api/v1/auth/register", json={
        "email": "first@cloakhaven.com",
        "password": "StrongPass1",
        "full_name": "First",
    })
    reg2 = await client.post("/api/v1/auth/register", json={
        "email": "second@cloakhaven.com",
        "password": "StrongPass1",
        "full_name": "Second",
    })
    token = reg2.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_admin"] is False


# ── Scan Lookup (polling endpoint) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_lookup_unknown_name(client: AsyncClient):
    response = await client.get("/api/v1/scan/lookup/Unknown%20Person")
    assert response.status_code == 200
    data = response.json()
    assert data["needs_fresh_scan"] is True
    assert data["is_cached"] is False
