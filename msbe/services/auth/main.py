"""
M.DocAI MSBE Auth service.

Handles user registration, login, JWT token management, RBAC,
and admin settings for providers/models/tiers.

Endpoints:
  POST /api/v1/auth/register     — create a new user
  POST /api/v1/auth/login        — authenticate and return JWT
  POST /api/v1/auth/refresh      — refresh an existing JWT
  GET  /api/v1/users/me          — get current user profile
  PUT  /api/v1/users/me          — update current user profile
  PUT  /api/v1/users/me/password — change password
  GET  /api/v1/admin/users       — list all users (admin only)
  PUT  /api/v1/admin/users/{id}/role — change user role (admin only)
  GET  /api/v1/admin/providers   — list configured providers (admin only)
  PUT  /api/v1/admin/providers   — update providers (admin only)
  GET  /api/v1/admin/models      — list configured models (admin only)
  PUT  /api/v1/admin/models      — update models (admin only)
  GET  /api/v1/admin/tiers       — get tier-to-model mappings (admin only)
  PUT  /api/v1/admin/tiers       — update tier-to-model mappings (admin only)
  GET  /health                   — service health check
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import bcrypt
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mdocai-dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))
DATA_DIR = Path(os.getenv("AUTH_DATA_DIR", "./data"))
USERS_FILE = DATA_DIR / "users.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES = {ROLE_ADMIN, ROLE_USER}


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------


class UserStore:
    """Simple JSON file-backed user store."""

    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._users: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if self._filepath.exists():
            try:
                with open(self._filepath, "r") as f:
                    data = json.load(f)
                    self._users = {u["id"]: u for u in data}
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt users file, starting fresh")
                self._users = {}
        else:
            self._users = {}

    def _save(self):
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "w") as f:
            json.dump(list(self._users.values()), f, indent=2, default=str)

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_lower = email.lower()
        for user in self._users.values():
            if user["email"].lower() == email_lower:
                return user
        return None

    def find_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._users.get(user_id)

    def create(
        self, email: str, nickname: str, password_hash: str, role: str = ROLE_USER
    ) -> Dict[str, Any]:
        user = {
            "id": str(uuid4()),
            "email": email.lower(),
            "nickname": nickname,
            "password_hash": password_hash,
            "avatar": None,
            "tenant_id": str(uuid4()),
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[user["id"]] = user
        self._save()
        return user

    def update(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user = self._users.get(user_id)
        if not user:
            return None
        user.update(updates)
        self._save()
        return user

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._users.values())

    @property
    def count(self) -> int:
        return len(self._users)


user_store = UserStore(USERS_FILE)


# ---------------------------------------------------------------------------
# Admin settings store (providers, models, tiers)
# ---------------------------------------------------------------------------


class SettingsStore:
    """File-backed settings store for providers, models, and tier mappings."""

    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self._filepath.exists():
            try:
                with open(self._filepath, "r") as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupt settings file, using defaults")
                self._data = {}
        else:
            self._data = {}

        # Ensure default structure
        if "providers" not in self._data:
            self._data["providers"] = self._default_providers()
        if "models" not in self._data:
            self._data["models"] = self._default_models()
        if "tiers" not in self._data:
            self._data["tiers"] = self._default_tiers()
        self._save()

    def _save(self):
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "w") as f:
            json.dump(self._data, f, indent=2)

    @staticmethod
    def _default_providers() -> List[Dict[str, Any]]:
        return [
            {
                "id": "google_studio",
                "name": "Google Studio (Gemini API)",
                "type": "vlm",
                "base_url": "https://generativelanguage.googleapis.com",
                "api_key_env": "GOOGLE_STUDIO_API_KEY",
                "timeout": 60,
                "enabled": True,
            },
            {
                "id": "poe_api",
                "name": "POE API",
                "type": "llm",
                "base_url": "https://api.poe.com/v1",
                "api_key_env": "POE_API_KEY",
                "timeout": 120,
                "enabled": True,
            },
            {
                "id": "lm_studio",
                "name": "LM Studio (Local)",
                "type": "vlm",
                "base_url": "http://localhost:1234",
                "api_key_env": "",
                "timeout": 30,
                "enabled": True,
            },
            {
                "id": "bedrock",
                "name": "AWS Bedrock",
                "type": "llm",
                "base_url": "https://bedrock-runtime.ap-southeast-2.amazonaws.com",
                "api_key_env": "AWS_ACCESS_KEY_ID",
                "timeout": 120,
                "enabled": True,
            },
        ]

    @staticmethod
    def _default_models() -> List[Dict[str, Any]]:
        return [
            {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "provider": "google_studio", "max_tokens": 4096, "temperature": 0.2},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "google_studio", "max_tokens": 4096, "temperature": 0.2},
            {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro Preview", "provider": "google_studio", "max_tokens": 4096, "temperature": 0.2},
            {"id": "assistant", "name": "POE Assistant", "provider": "poe_api", "max_tokens": 4096, "temperature": 0.2},
            {"id": "gemini-3-flash", "name": "Gemini 3 Flash (POE)", "provider": "poe_api", "max_tokens": 4096, "temperature": 0.2},
            {"id": "gemini-3-pro", "name": "Gemini 3 Pro (POE)", "provider": "poe_api", "max_tokens": 4096, "temperature": 0.2},
            {"id": "qwen3-max", "name": "Qwen3 Max", "provider": "poe_api", "max_tokens": 4096, "temperature": 0.2},
            {"id": "claude-opus-4.5", "name": "Claude Opus 4.5", "provider": "poe_api", "max_tokens": 4096, "temperature": 0.2},
            {"id": "lightonocr-2-1b", "name": "LightOnOCR 2 1B", "provider": "lm_studio", "max_tokens": 4096, "temperature": 0.2},
            {"id": "claude-haiku", "name": "Claude Haiku (Bedrock)", "provider": "bedrock", "max_tokens": 4096, "temperature": 0.2},
            {"id": "claude-sonnet", "name": "Claude Sonnet (Bedrock)", "provider": "bedrock", "max_tokens": 4096, "temperature": 0.2},
        ]

    @staticmethod
    def _default_tiers() -> Dict[str, Any]:
        return {
            "parser": {
                "Rapid": {"model": "lightonocr-2-1b", "provider": "lm_studio"},
                "Normal": {"model": "claude-haiku", "provider": "bedrock"},
                "Advance": {"model": "claude-sonnet", "provider": "bedrock"},
            },
            "classifier": {
                "Rapid": {"model": "lightonocr-2-1b", "provider": "lm_studio"},
                "Normal": {"model": "claude-haiku", "provider": "bedrock"},
                "Advance": {"model": "claude-sonnet", "provider": "bedrock"},
                "Multimodal": {"model": "claude-sonnet", "provider": "bedrock"},
            },
            "extractor": {
                "Rapid": {"model": "lightonocr-2-1b", "provider": "lm_studio"},
                "Normal": {"model": "claude-haiku", "provider": "bedrock"},
                "Advance": {"model": "claude-sonnet", "provider": "bedrock"},
            },
            "splitter": {
                "Rapid": {"model": "lightonocr-2-1b", "provider": "lm_studio"},
                "Normal": {"model": "claude-haiku", "provider": "bedrock"},
                "Advance": {"model": "claude-sonnet", "provider": "bedrock"},
            },
        }

    # --- Public API ---

    @property
    def providers(self) -> List[Dict[str, Any]]:
        return self._data["providers"]

    @providers.setter
    def providers(self, value: List[Dict[str, Any]]):
        self._data["providers"] = value
        self._save()

    @property
    def models(self) -> List[Dict[str, Any]]:
        return self._data["models"]

    @models.setter
    def models(self, value: List[Dict[str, Any]]):
        self._data["models"] = value
        self._save()

    @property
    def tiers(self) -> Dict[str, Any]:
        return self._data["tiers"]

    @tiers.setter
    def tiers(self, value: Dict[str, Any]):
        self._data["tiers"] = value
        self._save()


settings_store = SettingsStore(SETTINGS_FILE)


# ---------------------------------------------------------------------------
# Default users — seeded on first start
# ---------------------------------------------------------------------------


def _seed_default_users():
    """Create default admin and user accounts if they don't exist."""
    defaults = [
        {"email": "tutm7@msb.com.vn", "nickname": "Admin", "password": "1505", "role": ROLE_ADMIN},
        {"email": "user@msb.com.vn", "nickname": "User", "password": "1505", "role": ROLE_USER},
    ]
    for u in defaults:
        if not user_store.find_by_email(u["email"]):
            pw_hash = hash_password(u["password"])
            user_store.create(
                email=u["email"],
                nickname=u["nickname"],
                password_hash=pw_hash,
                role=u["role"],
            )
            logger.info("Seeded default user: %s (%s)", u["email"], u["role"])


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRATION_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ---------------------------------------------------------------------------
# Auth middleware helper
# ---------------------------------------------------------------------------


def _get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extract and validate the user from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    payload = decode_token(auth_header[7:])
    if not payload:
        return None
    return user_store.find_by_id(payload["sub"])


def _require_auth(request: Request) -> tuple[Optional[JSONResponse], Optional[Dict[str, Any]]]:
    """Returns (error_response, user). If error_response is not None, return it."""
    user = _get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"code": 1, "message": "Unauthorized"}), None
    return None, user


def _require_admin(request: Request) -> tuple[Optional[JSONResponse], Optional[Dict[str, Any]]]:
    """Returns (error_response, user). Requires admin role."""
    err, user = _require_auth(request)
    if err:
        return err, None
    if user["role"] != ROLE_ADMIN:
        return JSONResponse(status_code=403, content={"code": 1, "message": "Admin access required"}), None
    return None, user


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=4)
    nickname: str = Field(..., min_length=1, max_length=50)


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4)


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., pattern=f"^({'|'.join(VALID_ROLES)})$")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="M.DocAI Auth Service", version="0.2.0")


@app.on_event("startup")
async def startup():
    _seed_default_users()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "auth", "users": user_store.count})


# ===========================================================================
# Auth endpoints
# ===========================================================================


@app.post("/api/v1/auth/register")
async def register(req: RegisterRequest) -> JSONResponse:
    existing = user_store.find_by_email(req.email)
    if existing:
        return JSONResponse(status_code=409, content={"code": 1, "message": "Email already registered"})

    pw_hash = hash_password(req.password)
    user_store.create(email=req.email, nickname=req.nickname, password_hash=pw_hash)
    logger.info("New user registered: %s", req.email)
    return JSONResponse({"code": 0, "message": "Registration successful"})


@app.post("/api/v1/auth/login")
async def login(req: LoginRequest) -> JSONResponse:
    user = user_store.find_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        return JSONResponse(status_code=401, content={"code": 1, "message": "Invalid email or password"})

    token = create_token(user["id"], user["email"], user["role"])
    logger.info("User logged in: %s", user["email"])

    return JSONResponse({
        "code": 0,
        "data": {
            "token": token,
            "user_id": user["id"],
            "nickname": user["nickname"],
            "email": user["email"],
            "avatar": user.get("avatar"),
            "tenant_id": user["tenant_id"],
            "role": user["role"],
        },
    })


@app.post("/api/v1/auth/refresh")
async def refresh_token(request: Request) -> JSONResponse:
    err, user = _require_auth(request)
    if err:
        return err
    new_token = create_token(user["id"], user["email"], user["role"])
    return JSONResponse({"code": 0, "data": {"token": new_token}})


# ===========================================================================
# User profile endpoints
# ===========================================================================


@app.get("/api/v1/users/me")
async def get_profile(request: Request) -> JSONResponse:
    err, user = _require_auth(request)
    if err:
        return err
    return JSONResponse({
        "code": 0,
        "data": {
            "id": user["id"],
            "email": user["email"],
            "nickname": user["nickname"],
            "avatar": user.get("avatar"),
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "created_at": user.get("created_at"),
        },
    })


@app.put("/api/v1/users/me")
async def update_profile(req: UpdateProfileRequest, request: Request) -> JSONResponse:
    err, user = _require_auth(request)
    if err:
        return err

    updates = {}
    if req.nickname is not None:
        updates["nickname"] = req.nickname
    if req.avatar is not None:
        updates["avatar"] = req.avatar

    if updates:
        user_store.update(user["id"], updates)

    updated = user_store.find_by_id(user["id"])
    return JSONResponse({
        "code": 0,
        "data": {
            "id": updated["id"],
            "email": updated["email"],
            "nickname": updated["nickname"],
            "avatar": updated.get("avatar"),
            "role": updated["role"],
        },
    })


@app.put("/api/v1/users/me/password")
async def change_password(req: ChangePasswordRequest, request: Request) -> JSONResponse:
    err, user = _require_auth(request)
    if err:
        return err

    if not verify_password(req.current_password, user["password_hash"]):
        return JSONResponse(status_code=400, content={"code": 1, "message": "Current password is incorrect"})

    new_hash = hash_password(req.new_password)
    user_store.update(user["id"], {"password_hash": new_hash})
    return JSONResponse({"code": 0, "message": "Password changed successfully"})


# ===========================================================================
# Admin: user management
# ===========================================================================


@app.get("/api/v1/admin/users")
async def list_users(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err

    users = [
        {
            "id": u["id"],
            "email": u["email"],
            "nickname": u["nickname"],
            "role": u["role"],
            "created_at": u.get("created_at"),
        }
        for u in user_store.list_all()
    ]
    return JSONResponse({"code": 0, "data": users})


@app.put("/api/v1/admin/users/{user_id}/role")
async def update_user_role(user_id: str, req: UpdateRoleRequest, request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err

    target = user_store.find_by_id(user_id)
    if not target:
        return JSONResponse(status_code=404, content={"code": 1, "message": "User not found"})

    user_store.update(user_id, {"role": req.role})
    return JSONResponse({"code": 0, "message": f"Role updated to {req.role}"})


# ===========================================================================
# Admin: provider settings
# ===========================================================================


@app.get("/api/v1/admin/providers")
async def get_providers(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err
    return JSONResponse({"code": 0, "data": settings_store.providers})


@app.put("/api/v1/admin/providers")
async def update_providers(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err
    body = await request.json()
    providers = body.get("providers")
    if not isinstance(providers, list):
        return JSONResponse(status_code=400, content={"code": 1, "message": "providers must be an array"})
    settings_store.providers = providers
    logger.info("Providers updated by admin")
    return JSONResponse({"code": 0, "data": settings_store.providers})


# ===========================================================================
# Admin: model settings
# ===========================================================================


@app.get("/api/v1/admin/models")
async def get_models(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err
    return JSONResponse({"code": 0, "data": settings_store.models})


@app.put("/api/v1/admin/models")
async def update_models(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err
    body = await request.json()
    models = body.get("models")
    if not isinstance(models, list):
        return JSONResponse(status_code=400, content={"code": 1, "message": "models must be an array"})
    settings_store.models = models
    logger.info("Models updated by admin")
    return JSONResponse({"code": 0, "data": settings_store.models})


# ===========================================================================
# Admin: tier configuration
# ===========================================================================


@app.get("/api/v1/admin/tiers")
async def get_tiers(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err
    return JSONResponse({"code": 0, "data": settings_store.tiers})


@app.put("/api/v1/admin/tiers")
async def update_tiers(request: Request) -> JSONResponse:
    err, _ = _require_admin(request)
    if err:
        return err
    body = await request.json()
    tiers = body.get("tiers")
    if not isinstance(tiers, dict):
        return JSONResponse(status_code=400, content={"code": 1, "message": "tiers must be an object"})
    settings_store.tiers = tiers
    logger.info("Tier configuration updated by admin")
    return JSONResponse({"code": 0, "data": settings_store.tiers})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AUTH_PORT", "8006"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
