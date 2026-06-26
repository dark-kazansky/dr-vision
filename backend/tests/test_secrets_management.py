"""
Tests for feat-015: Secrets Management & Production Config.

Verifies:
- Settings loads from environment variables
- No hardcoded secrets in defaults
- CORS_ORIGINS parsed from comma-separated string
- check_required_secrets() reports missing secrets
- Settings fails gracefully without secrets
"""

import os
from unittest.mock import patch


class TestSecretsManagement:
    """Test that secrets are properly managed via environment variables."""

    def test_no_hardcoded_database_url_default(self):
        """database_url should be None when not set via env."""
        with patch.dict(os.environ, {}, clear=True):
            from settings import Settings

            # Temporarily override .env file loading
            s = Settings(_env_file=None)
            assert s.database_url is None

    def test_no_hardcoded_minio_credentials(self):
        """MinIO credentials should be None when not set via env."""
        with patch.dict(os.environ, {}, clear=True):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.minio_access_key is None
            assert s.minio_secret_key is None

    def test_database_url_from_env(self):
        """database_url should read from DATABASE_URL env var."""
        test_url = "postgresql://user:pass@host:5432/db"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}, clear=True):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.database_url == test_url

    def test_minio_credentials_from_env(self):
        """MinIO credentials should read from env vars."""
        with patch.dict(
            os.environ,
            {"MINIO_ACCESS_KEY": "mykey", "MINIO_SECRET_KEY": "mysecret"},
            clear=True,
        ):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.minio_access_key == "mykey"
            assert s.minio_secret_key == "mysecret"

    def test_cors_origins_comma_separated(self):
        """CORS_ORIGINS should parse comma-separated origins."""
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "https://app.example.com, https://admin.example.com"},
            clear=True,
        ):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.cors_origins == [
                "https://app.example.com",
                "https://admin.example.com",
            ]

    def test_cors_origins_single_value(self):
        """CORS_ORIGINS with single value should work."""
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "http://localhost:3000"},
            clear=True,
        ):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.cors_origins == ["http://localhost:3000"]

    def test_cors_origins_default(self):
        """CORS_ORIGINS default should be localhost:3000 (not wildcard *)."""
        with patch.dict(os.environ, {}, clear=True):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.cors_origins == ["http://localhost:3000"]
            assert "*" not in s.cors_origins

    def test_check_required_secrets_all_missing(self):
        """check_required_secrets reports all missing when no env set."""
        with patch.dict(os.environ, {}, clear=True):
            from settings import Settings

            s = Settings(_env_file=None)
            missing = s.check_required_secrets()
            assert "DATABASE_URL" in missing
            assert "MINIO_ACCESS_KEY" in missing
            assert "MINIO_SECRET_KEY" in missing

    def test_check_required_secrets_all_present(self):
        """check_required_secrets returns empty when all secrets set."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://x:x@localhost/x",
                "MINIO_ACCESS_KEY": "key",
                "MINIO_SECRET_KEY": "secret",
            },
            clear=True,
        ):
            from settings import Settings

            s = Settings(_env_file=None)
            assert s.check_required_secrets() == []

    def test_check_required_secrets_partial(self):
        """check_required_secrets reports only the missing ones."""
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://x:x@localhost/x"},
            clear=True,
        ):
            from settings import Settings

            s = Settings(_env_file=None)
            missing = s.check_required_secrets()
            assert "DATABASE_URL" not in missing
            assert "MINIO_ACCESS_KEY" in missing
            assert "MINIO_SECRET_KEY" in missing


class TestEnvExampleFiles:
    """Test that .env.example files exist and document required vars."""

    def test_root_env_example_exists(self):
        """Root .env.example should exist."""
        from pathlib import Path

        root = Path(__file__).parent.parent.parent / ".env.example"
        assert root.exists(), f".env.example not found at {root}"

    def test_backend_env_example_exists(self):
        """Backend .env.example should exist."""
        from pathlib import Path

        backend = Path(__file__).parent.parent / ".env.example"
        assert backend.exists(), f"backend/.env.example not found at {backend}"

    def test_root_env_example_documents_required_vars(self):
        """Root .env.example should document all critical env vars."""
        from pathlib import Path

        content = (
            Path(__file__).parent.parent.parent / ".env.example"
        ).read_text()
        required_vars = [
            "POSTGRES_PASSWORD",
            "POSTGRES_USER",
            "POSTGRES_DB",
            "MINIO_ROOT_USER",
            "MINIO_ROOT_PASSWORD",
            "DATABASE_URL",
            "CORS_ORIGINS",
            "API_BASE_URL",
        ]
        for var in required_vars:
            assert var in content, f"{var} not documented in .env.example"

    def test_backend_env_example_documents_required_vars(self):
        """Backend .env.example should document all backend env vars."""
        from pathlib import Path

        content = (Path(__file__).parent.parent / ".env.example").read_text()
        required_vars = [
            "DATABASE_URL",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "MINIO_ENDPOINT",
            "CORS_ORIGINS",
            "HOST",
            "PORT",
        ]
        for var in required_vars:
            assert var in content, f"{var} not documented in backend/.env.example"


class TestDockerComposeProd:
    """Test that docker-compose.prod.yml exists and uses env vars."""

    def test_prod_compose_exists(self):
        """docker-compose.prod.yml should exist."""
        from pathlib import Path

        prod = Path(__file__).parent.parent.parent / "docker-compose.prod.yml"
        assert prod.exists(), f"docker-compose.prod.yml not found at {prod}"

    def test_prod_compose_no_plaintext_passwords(self):
        """docker-compose.prod.yml should not contain plaintext passwords."""
        from pathlib import Path

        content = (
            Path(__file__).parent.parent.parent / "docker-compose.prod.yml"
        ).read_text()
        # Should not contain hardcoded dev passwords
        assert "drvision_dev" not in content
        assert "minioadmin" not in content
        # Should use variable substitution
        assert "${POSTGRES_PASSWORD}" in content
        assert "${MINIO_ROOT_USER}" in content
        assert "${MINIO_ROOT_PASSWORD}" in content

    def test_dev_compose_uses_env_vars_with_defaults(self):
        """docker-compose.yml (dev) should use env vars with defaults."""
        from pathlib import Path

        content = (
            Path(__file__).parent.parent.parent / "docker-compose.yml"
        ).read_text()
        # Dev compose uses ${VAR:-default} syntax
        assert "${POSTGRES_PASSWORD:-docintel_dev}" in content
        assert "${MINIO_ROOT_USER:-minioadmin}" in content


class TestGitignore:
    """Test that .gitignore properly excludes secret files."""

    def test_gitignore_excludes_env_prod(self):
        """Root .gitignore should exclude .env.prod."""
        from pathlib import Path

        content = (
            Path(__file__).parent.parent.parent / ".gitignore"
        ).read_text()
        assert ".env.prod" in content
