"""Reusable retry decorator with exponential backoff for transient API failures.

Validates: Requirements 14.1, 14.2, 14.3
- Retries on transient errors with exponential backoff
- Provides a reusable decorator for agent implementations
- Re-raises with descriptive message after all retries exhausted
"""

import functools
import logging
import time
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    retryable_exceptions: Tuple[Type[BaseException], ...] = (ConnectionError, TimeoutError),
):
    """Decorator that retries a function on transient failures with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the initial call).
        backoff_base: Base delay in seconds. Actual delay is ``backoff_base * 2^attempt``.
        retryable_exceptions: Tuple of exception types that trigger a retry.

    Returns:
        Decorated function that transparently retries on matching exceptions.

    Raises:
        The original exception (with added context) when all attempts are exhausted.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: BaseException | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_attempts - 1:
                        delay = backoff_base * (2 ** attempt)
                        logger.warning(
                            "Retry %d/%d for %s after %s: waiting %.1fs",
                            attempt + 1,
                            max_attempts,
                            func.__qualname__,
                            type(exc).__name__,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d retry attempts exhausted for %s",
                            max_attempts,
                            func.__qualname__,
                        )

            # All attempts exhausted – re-raise with context
            raise type(last_exception)(
                f"Failed after {max_attempts} retry attempts: {last_exception}"
            ) from last_exception

        return wrapper
    return decorator
