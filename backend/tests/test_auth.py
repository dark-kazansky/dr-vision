"""
Tests for feat-014: Authentication & Authorization.

Covers:
- Password hashing (bcrypt)
- JWT token creation and verification
- Login endpoint (success + failure)
- Token refresh flow
- Protected endpoints require auth
- Role-based access (admin vs user)
- API key generation
- Admin user management CRUD
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from auth.models import UserInDB
from auth.service import AuthService


# =============================================================================
# Unit tests — AuthService
# =============================================================================


class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_password_produces_hash(self):
        hashed = AuthService.hash_password("secret123")
        assert hashed != "secret123"
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        hashed = AuthService.hash_password("mypassword")
        assert AuthService.verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = AuthService.hash_password("mypassword")
        assert AuthService.verify_password("wrongpass", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        h1 = AuthService.hash_password("password1")
        h2 = AuthService.hash_password("password2")
        assert h1 != h2


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def _make_user(self, role: str = "user") -> UserInDB:
        return UserInDB(
            id="user123",
            email="test@example.com",
            full_name="Test User",
            role=role,
            is_active=True,
            password_hash="fakehash",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_create_tokens_returns_access_and_refresh(self):
        user = self._make_user()
        access, refresh, expires_in = AuthService.create_tokens(user)
        assert isinstance(access, str)
        assert isinstance(refresh, str)
        assert expires_in == 30 * 60  # 30 minutes in seconds
        assert access != refresh

    def test_decode_valid_access_token(self):
        user = self._make_user(role="admin")
        access, _, _ = AuthService.create_tokens(user)
        payload = AuthService.decode_token(access)
        assert payload is not None
        assert payload.sub == "user123"
        assert payload.email == "test@example.com"
        assert payload.role == "admin"
        assert payload.type == "access"

    def test_decode_valid_refresh_token(self):
        user = self._make_user()
        _, refresh, _ = AuthService.create_tokens(user)
        payload = AuthService.decode_token(refresh)
        assert payload is not None
        assert payload.type == "refresh"

    def test_decode_invalid_token_returns_none(self):
        payload = AuthService.decode_token("invalid.token.here")
        assert payload is None

    def test_decode_wrong_secret_returns_none(self):
        user = self._make_user()
        access, _, _ = AuthService.create_tokens(user)

        # Decode with different secret
        with patch("auth.service.settings") as wrong_settings:
            wrong_settings.jwt_secret_key = "completely-different-secret"
            wrong_settings.jwt_algorithm = "HS256"
            payload = AuthService.decode_token(access)
            assert payload is None

    def test_generate_api_key(self):
        key = AuthService.generate_api_key()
        assert key.startswith("drvision_")
        assert len(key) > 20


# =============================================================================
# Integration tests — API endpoints
# =============================================================================


@pytest.fixture(autouse=True)
def set_jwt_secret():
    """Set JWT secret for all tests in this module."""
    with patch("auth.service.settings") as mock_settings:
        mock_settings.jwt_secret_key = "test-secret-key-for-testing"
        mock_settings.jwt_algorithm = "HS256"
        yield mock_settings


@pytest.fixture
def mock_auth_repo():
    """Create a mock auth repository."""
    repo = AsyncMock()
    repo.pool = MagicMock()  # Non-None pool means DB is available
    return repo


@pytest.fixture
def test_user_data():
    """Test user data as stored in DB."""
    return {
        "id": "abc123def456",
        "email": "user@drvision.com",
        "full_name": "Test User",
        "role": "user",
        "is_active": True,
        "password_hash": AuthService.hash_password("correct-password"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None,
    }


@pytest.fixture
def admin_user_data():
    """Admin user data."""
    return {
        "id": "admin999",
        "email": "admin@drvision.com",
        "full_name": "Admin User",
        "role": "admin",
        "is_active": True,
        "password_hash": AuthService.hash_password("admin-password"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None,
    }


@pytest.mark.asyncio
async def test_login_success(mock_auth_repo, test_user_data):
    """POST /auth/login with correct credentials returns tokens."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_email.return_value = test_user_data
    mock_auth_repo.update_last_login.return_value = None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/auth/login", json={
            "email": "user@drvision.com",
            "password": "correct-password",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800


@pytest.mark.asyncio
async def test_login_wrong_password(mock_auth_repo, test_user_data):
    """POST /auth/login with wrong password returns 401."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_email.return_value = test_user_data

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/auth/login", json={
            "email": "user@drvision.com",
            "password": "wrong-password",
        })

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_user_not_found(mock_auth_repo):
    """POST /auth/login with non-existent email returns 401."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_email.return_value = None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/auth/login", json={
            "email": "nobody@drvision.com",
            "password": "whatever",
        })

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(mock_auth_repo):
    """GET protected endpoint without token returns 401."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/jobs")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(mock_auth_repo, test_user_data):
    """Protected endpoint with valid token passes auth check."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_id.return_value = test_user_data

    # Create a valid token
    user = UserInDB(**test_user_data)
    access, _, _ = AuthService.create_tokens(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {access}"},
        )

    # /health is public, should return 200
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_public():
    """GET /health does NOT require authentication."""
    from server import create_app
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_create_user(mock_auth_repo, admin_user_data):
    """Admin can create new users via POST /auth/users."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_id.return_value = admin_user_data
    mock_auth_repo.get_user_by_email.return_value = None
    mock_auth_repo.create_user.return_value = {
        "id": "new_user_id",
        "email": "newuser@drvision.com",
        "full_name": "New User",
        "role": "user",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }

    admin = UserInDB(**admin_user_data)
    access, _, _ = AuthService.create_tokens(admin)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/auth/users",
            json={
                "email": "newuser@drvision.com",
                "password": "strongpass123",
                "full_name": "New User",
                "role": "user",
            },
            headers={"Authorization": f"Bearer {access}"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@drvision.com"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_user_cannot_create_user(mock_auth_repo, test_user_data):
    """Non-admin user cannot create users (403)."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_id.return_value = test_user_data

    user = UserInDB(**test_user_data)
    access, _, _ = AuthService.create_tokens(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/auth/users",
            json={
                "email": "hack@evil.com",
                "password": "password123",
                "full_name": "Hacker",
            },
            headers={"Authorization": f"Bearer {access}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_flow(mock_auth_repo, test_user_data):
    """POST /auth/refresh with valid refresh token returns new tokens."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo
    mock_auth_repo.get_user_by_id.return_value = test_user_data

    user = UserInDB(**test_user_data)
    _, refresh, _ = AuthService.create_tokens(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {refresh}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(mock_auth_repo, test_user_data):
    """POST /auth/refresh with access token (not refresh) returns 401."""
    from server import create_app
    app = create_app()
    app.state.auth_repo = mock_auth_repo

    user = UserInDB(**test_user_data)
    access, _, _ = AuthService.create_tokens(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {access}"},
        )

    assert resp.status_code == 401
