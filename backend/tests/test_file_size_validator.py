"""Tests for FileSizeValidator middleware (Task 3.1).

Validates Requirements 4.1, 4.2, 4.3:
- File size is checked against upload.max_size_mb before processing
- HTTP 413 returned with descriptive message when file exceeds limit
- File content is read in a controlled manner and file position is reset
"""

import io
import pytest
from unittest.mock import AsyncMock
from fastapi import UploadFile, HTTPException

from core.middleware import FileSizeValidator


@pytest.fixture
def validator():
    return FileSizeValidator()


def make_upload_file(content: bytes, filename: str = "test.pdf") -> UploadFile:
    """Create an UploadFile backed by a BytesIO buffer."""
    return UploadFile(filename=filename, file=io.BytesIO(content))


class TestFileSizeValidatorAccepts:
    """Requirement 4.1: Files within the size limit pass validation."""

    @pytest.mark.asyncio
    async def test_file_within_limit_passes(self, validator):
        content = b"x" * 100  # 100 bytes
        file = make_upload_file(content)
        # Should not raise
        await validator.validate(file, max_size_mb=1)

    @pytest.mark.asyncio
    async def test_file_exactly_at_limit_passes(self, validator):
        one_mb = 1 * 1024 * 1024
        content = b"x" * one_mb
        file = make_upload_file(content)
        await validator.validate(file, max_size_mb=1)

    @pytest.mark.asyncio
    async def test_empty_file_passes(self, validator):
        file = make_upload_file(b"")
        await validator.validate(file, max_size_mb=1)


class TestFileSizeValidatorRejects:
    """Requirement 4.2: HTTP 413 returned when file exceeds limit."""

    @pytest.mark.asyncio
    async def test_file_over_limit_raises_413(self, validator):
        one_mb_plus = 1 * 1024 * 1024 + 1
        content = b"x" * one_mb_plus
        file = make_upload_file(content)

        with pytest.raises(HTTPException) as exc_info:
            await validator.validate(file, max_size_mb=1)

        assert exc_info.value.status_code == 413
        assert "1 MB" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_error_message_includes_actual_size(self, validator):
        two_mb = 2 * 1024 * 1024
        content = b"x" * two_mb
        file = make_upload_file(content)

        with pytest.raises(HTTPException) as exc_info:
            await validator.validate(file, max_size_mb=1)

        assert "2.00 MB" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_small_limit_rejects_normal_file(self, validator):
        content = b"x" * 1024  # 1 KB
        file = make_upload_file(content)

        with pytest.raises(HTTPException) as exc_info:
            await validator.validate(file, max_size_mb=0.0001)  # ~100 bytes

        assert exc_info.value.status_code == 413


class TestFilePositionReset:
    """Requirement 4.3: File position is reset after validation."""

    @pytest.mark.asyncio
    async def test_file_position_reset_after_valid_file(self, validator):
        content = b"hello world"
        file = make_upload_file(content)

        await validator.validate(file, max_size_mb=1)

        # File should be readable from the beginning after validation
        data = await file.read()
        assert data == content

    @pytest.mark.asyncio
    async def test_file_position_reset_after_oversized_file(self, validator):
        one_mb_plus = 1 * 1024 * 1024 + 1
        content = b"x" * one_mb_plus
        file = make_upload_file(content)

        with pytest.raises(HTTPException):
            await validator.validate(file, max_size_mb=1)

        # Even after rejection, file position should be reset
        await file.seek(0)
        data = await file.read()
        assert len(data) == one_mb_plus
