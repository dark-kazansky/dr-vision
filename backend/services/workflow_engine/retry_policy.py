"""
Retry Policy — Configurable retry strategies for workflow activities.

Provides:
- Exponential backoff with optional jitter
- Maximum attempt limits
- Non-retryable error classification
- Predefined policies for common use cases

The retry logic lives at the engine level (not application level),
ensuring consistent retry behavior regardless of the activity implementation.
"""

import random
from typing import List, Optional

from services.workflow_engine.models import RetryPolicy


# =============================================================================
# Predefined Policies
# =============================================================================


def default_policy() -> RetryPolicy:
    """
    Default retry policy: 3 attempts, exponential backoff starting at 1s.

    Suitable for most transient failures (network errors, temporary unavailability).
    """
    return RetryPolicy(
        max_attempts=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=30.0,
        backoff_multiplier=2.0,
        non_retryable_errors=[],
    )


def aggressive_policy() -> RetryPolicy:
    """
    Aggressive retry policy: 5 attempts, longer backoff.

    Suitable for unreliable external services (payment gateways, third-party APIs).
    """
    return RetryPolicy(
        max_attempts=5,
        initial_delay_seconds=2.0,
        max_delay_seconds=120.0,
        backoff_multiplier=3.0,
        non_retryable_errors=[
            "ValidationError",
            "InvalidInput",
            "PermissionDenied",
            "AuthenticationFailed",
        ],
    )


def conservative_policy() -> RetryPolicy:
    """
    Conservative retry policy: 2 attempts, short backoff.

    Suitable for operations that should not be retried aggressively
    (database writes, state mutations that might not be idempotent).
    """
    return RetryPolicy(
        max_attempts=2,
        initial_delay_seconds=0.5,
        max_delay_seconds=5.0,
        backoff_multiplier=2.0,
        non_retryable_errors=[
            "ValidationError",
            "InvalidInput",
            "DuplicateEntry",
            "ConflictError",
        ],
    )


def no_retry_policy() -> RetryPolicy:
    """
    No retry — fail immediately on first error.

    Suitable for non-idempotent operations or when retry is handled elsewhere.
    """
    return RetryPolicy(
        max_attempts=1,
        initial_delay_seconds=0.1,
        max_delay_seconds=1.0,
        backoff_multiplier=1.0,
        non_retryable_errors=[],
    )


def ocr_policy() -> RetryPolicy:
    """
    OCR-specific retry policy: 3 attempts, moderate backoff.

    OCR operations are inherently idempotent (same file → same output).
    Non-retryable: validation errors, unsupported file types.
    """
    return RetryPolicy(
        max_attempts=3,
        initial_delay_seconds=2.0,
        max_delay_seconds=60.0,
        backoff_multiplier=2.0,
        non_retryable_errors=[
            "UnsupportedFileType",
            "InvalidFileFormat",
            "FileTooLarge",
            "EmptyFile",
            "ValidationError",
        ],
    )


def long_running_policy() -> RetryPolicy:
    """
    Long-running task retry policy: 4 attempts, long delays.

    Suitable for operations that take a long time and where the underlying
    service may need time to recover (model loading, heavy computation).
    """
    return RetryPolicy(
        max_attempts=4,
        initial_delay_seconds=5.0,
        max_delay_seconds=300.0,
        backoff_multiplier=3.0,
        non_retryable_errors=[
            "OutOfMemory",
            "ModelNotFound",
            "ConfigurationError",
        ],
    )


# =============================================================================
# Retry Decision Engine
# =============================================================================


class RetryDecision:
    """Result of evaluating whether to retry."""

    __slots__ = ("should_retry", "delay_seconds", "reason")

    def __init__(
        self,
        should_retry: bool,
        delay_seconds: float = 0,
        reason: str = "",
    ) -> None:
        self.should_retry = should_retry
        self.delay_seconds = delay_seconds
        self.reason = reason

    def __repr__(self) -> str:
        if self.should_retry:
            return f"RetryDecision(retry=True, delay={self.delay_seconds:.1f}s)"
        return f"RetryDecision(retry=False, reason='{self.reason}')"


def evaluate_retry(
    policy: RetryPolicy,
    attempt: int,
    error: str,
    add_jitter: bool = True,
) -> RetryDecision:
    """
    Evaluate whether an activity should be retried.

    Args:
        policy: The retry policy configuration.
        attempt: Current attempt number (0-indexed, so first failure is attempt=0).
        error: The error message from the failed attempt.
        add_jitter: Whether to add random jitter to the delay (prevents thundering herd).

    Returns:
        RetryDecision with should_retry flag and computed delay.
    """
    # Check max attempts
    if attempt >= policy.max_attempts - 1:
        return RetryDecision(
            should_retry=False,
            reason=f"Max attempts reached ({policy.max_attempts})",
        )

    # Check non-retryable errors
    if not policy.is_retryable(error):
        matched = _find_matching_error(error, policy.non_retryable_errors)
        return RetryDecision(
            should_retry=False,
            reason=f"Non-retryable error pattern matched: {matched}",
        )

    # Calculate delay with exponential backoff
    delay = policy.get_delay(attempt)

    # Add jitter (±25%) to prevent thundering herd
    if add_jitter and delay > 0:
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Ensure minimum delay

    return RetryDecision(
        should_retry=True,
        delay_seconds=delay,
        reason=f"Attempt {attempt + 1}/{policy.max_attempts}, retrying after {delay:.1f}s",
    )


# =============================================================================
# Policy Factory
# =============================================================================

_POLICY_REGISTRY = {
    "default": default_policy,
    "aggressive": aggressive_policy,
    "conservative": conservative_policy,
    "no_retry": no_retry_policy,
    "ocr": ocr_policy,
    "long_running": long_running_policy,
}


def get_policy(name: str) -> RetryPolicy:
    """
    Get a predefined retry policy by name.

    Available policies: default, aggressive, conservative, no_retry, ocr, long_running.

    Raises:
        ValueError: If policy name is not recognized.
    """
    factory = _POLICY_REGISTRY.get(name)
    if factory is None:
        available = ", ".join(_POLICY_REGISTRY.keys())
        raise ValueError(f"Unknown retry policy '{name}'. Available: {available}")
    return factory()


def register_policy(name: str, policy_factory) -> None:
    """Register a custom retry policy factory."""
    _POLICY_REGISTRY[name] = policy_factory


def list_policies() -> List[str]:
    """List available policy names."""
    return list(_POLICY_REGISTRY.keys())


# =============================================================================
# Helpers
# =============================================================================


def _find_matching_error(error: str, patterns: List[str]) -> Optional[str]:
    """Find which non-retryable pattern matched the error."""
    error_lower = error.lower()
    for pattern in patterns:
        if pattern.lower() in error_lower:
            return pattern
    return None
