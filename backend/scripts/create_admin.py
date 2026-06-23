"""
Create Admin User Script.

Usage:
    cd backend
    DATABASE_URL=postgresql://... python scripts/create_admin.py

Or with .env file loaded:
    cd backend && python scripts/create_admin.py

The script will prompt for email and password if not provided via env vars.
"""

import asyncio
import os
import sys
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.repository import AuthRepository
from auth.service import AuthService

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    print("Export it or add to your .env file.")
    sys.exit(1)


async def main():
    import asyncpg

    # Get user input
    email = os.environ.get("ADMIN_EMAIL") or input("Admin email: ").strip()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    name = os.environ.get("ADMIN_NAME", "Admin")

    if not email or not password:
        print("ERROR: Email and password are required.")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    # Connect to DB
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    repo = AuthRepository(pool)
    await repo.init_schema()

    # Check if user already exists
    existing = await repo.get_user_by_email(email)
    if existing:
        print(f"User {email} already exists (role: {existing['role']})")
        await pool.close()
        return

    # Create admin user
    password_hash = AuthService.hash_password(password)
    user = await repo.create_user(
        email=email,
        full_name=name,
        password_hash=password_hash,
        role="admin",
    )

    print(f"✅ Admin user created:")
    print(f"   Email: {user['email']}")
    print(f"   Name:  {user['full_name']}")
    print(f"   Role:  {user['role']}")
    print(f"   ID:    {user['id']}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
