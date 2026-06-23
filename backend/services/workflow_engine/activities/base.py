"""
Activity Base — Shared utilities and base classes for activities.
"""

from typing import Any, Dict, Optional


class ActivityError(Exception):
    """
    Base exception for activity failures.

    Attributes:
        message: Human-readable error description.
        retryable: Whether this error should be retried.
        details: Additional error context.
    """

    def __init__(
        self,
        message: str,
        retryable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class NonRetryableError(ActivityError):
    """Error that should NOT be retried (validation, bad input, etc.)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, retryable=False, details=details)


class ActivityContext:
    """
    Context object passed to activity handlers for accessing shared data.

    Provides convenient access to:
    - Workflow input data
    - Upstream activity outputs
    - Activity configuration
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    @property
    def workflow_run_id(self) -> str:
        return self._payload.get("workflow_run_id", "")

    @property
    def activity_id(self) -> str:
        return self._payload.get("activity_id", "")

    @property
    def activity_type(self) -> str:
        return self._payload.get("activity_type", "")

    @property
    def config(self) -> Dict[str, Any]:
        """Activity-specific configuration."""
        return self._payload.get("config", {})

    @property
    def workflow_input(self) -> Dict[str, Any]:
        """The original workflow input data."""
        return self._payload.get("workflow_input", {})

    @property
    def upstream_outputs(self) -> Dict[str, Any]:
        """Outputs from dependency activities (activity_id → output)."""
        return self._payload.get("upstream_outputs", {})

    @property
    def previous_output(self) -> Optional[Any]:
        """Output from the immediately preceding activity (for sequential workflows)."""
        return self._payload.get("previous_output")

    @property
    def file_path(self) -> str:
        """File path from workflow input."""
        return self.workflow_input.get("file_path", "")

    @property
    def tier(self) -> str:
        """Processing tier (Normal, Premium, etc.)."""
        return self.config.get("tier", "Normal")

    def get(self, key: str, default: Any = None) -> Any:
        """Get arbitrary payload data."""
        return self._payload.get(key, default)
