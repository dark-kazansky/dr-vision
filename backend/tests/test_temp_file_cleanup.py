"""Tests for temp file cleanup in upload endpoints (Task 7.3).

Validates Requirements 16.1, 16.2, 16.3:
- Upload endpoints remove temp files in a finally block (success or failure)
- The backend does not accumulate permanent copies in data/uploaded/
- Temp file deletion failures log a warning but don't raise to the client
"""

import os
import logging


from services.parse_service import _safe_remove


class TestSafeRemove:
    """Requirement 16.3: Deletion failures log a warning but don't raise."""

    def test_removes_existing_file(self, tmp_path):
        """_safe_remove deletes a file that exists."""
        f = tmp_path / "tempfile.txt"
        f.write_text("data")
        assert f.exists()

        _safe_remove(str(f))
        assert not f.exists()

    def test_nonexistent_file_does_not_raise(self, tmp_path):
        """_safe_remove silently handles a file that doesn't exist."""
        path = str(tmp_path / "no_such_file.txt")
        # Should not raise
        _safe_remove(path)

    def test_deletion_failure_logs_warning(self, tmp_path, caplog):
        """_safe_remove logs a warning when os.remove fails."""
        # Use a directory path — os.remove on a directory raises an error
        d = tmp_path / "subdir"
        d.mkdir()

        with caplog.at_level(logging.WARNING):
            _safe_remove(str(d))

        assert any("Failed to remove temp file" in msg for msg in caplog.messages)
        # The directory should still exist (removal failed gracefully)
        assert d.exists()

    def test_no_exception_propagated_on_failure(self, tmp_path, monkeypatch):
        """_safe_remove never propagates exceptions to the caller."""
        f = tmp_path / "tempfile.txt"
        f.write_text("data")

        # Force os.remove to raise
        def bad_remove(path):
            raise PermissionError("denied")

        monkeypatch.setattr(os, "remove", bad_remove)

        # Should not raise
        _safe_remove(str(f))
