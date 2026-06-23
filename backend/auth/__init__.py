"""
Authentication & Authorization module for Doc Intelligence.

Provides:
- JWT token creation and verification
- Password hashing (bcrypt)
- FastAPI dependencies for route protection
- User management (admin-only)
- API key authentication for webhooks
"""

from auth.dependencies import get_current_user, require_role, optional_auth  # noqa: F401
from auth.service import AuthService  # noqa: F401
