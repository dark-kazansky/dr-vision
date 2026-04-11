"""Tests for validate_file_path utility (Task 3.2).

Validates Requirements 5.1, 5.2, 5.3:
- Resolve full path and verify it remains within expected data directory
- Return HTTP 400 with "Invalid filename" when path escapes base directory
- Reject path traversal sequences (..) and absolute paths
"""

import os
import pytest
from fastapi import HTTPException

from core.utils import validate_file_path


@pytest.fixture
def base_dir(tmp_path):
    """Create a temporary base directory for testing."""
    return str(tmp_path)


class TestValidFilenames:
    """Requirement 5.1: Normal filenames resolve within base directory."""

    def test_simple_filename(self, base_dir):
        result = validate_file_path("document.txt", base_dir)
        assert result == os.path.join(os.path.realpath(base_dir), "document.txt")

    def test_filename_with_spaces(self, base_dir):
        result = validate_file_path("my document.txt", base_dir)
        assert result == os.path.join(os.path.realpath(base_dir), "my document.txt")

    def test_filename_with_extension(self, base_dir):
        result = validate_file_path("report.docx", base_dir)
        assert result.endswith("report.docx")
        assert result.startswith(os.path.realpath(base_dir))


class TestPathTraversalRejection:
    """Requirement 5.3: Reject path traversal sequences and absolute paths."""

    def test_double_dot_rejected(self, base_dir):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("../etc/passwd", base_dir)
        assert exc_info.value.status_code == 400
        assert "Invalid filename" in exc_info.value.detail

    def test_embedded_double_dot_rejected(self, base_dir):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("subdir/../../secret.txt", base_dir)
        assert exc_info.value.status_code == 400
        assert "Invalid filename" in exc_info.value.detail

    def test_absolute_path_rejected(self, base_dir):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("/etc/passwd", base_dir)
        assert exc_info.value.status_code == 400
        assert "Invalid filename" in exc_info.value.detail

    def test_dot_dot_only_rejected(self, base_dir):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("..", base_dir)
        assert exc_info.value.status_code == 400


class TestOutsideBaseDirectory:
    """Requirement 5.2: HTTP 400 when resolved path falls outside base directory."""

    def test_traversal_escaping_base(self, base_dir):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("../outside.txt", base_dir)
        assert exc_info.value.status_code == 400
        assert "Invalid filename" in exc_info.value.detail
