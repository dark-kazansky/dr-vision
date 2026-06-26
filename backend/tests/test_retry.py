"""Tests for the reusable retry decorator (Task 7.1).

Validates: Requirements 14.1, 14.2, 14.3
- Retries on transient errors with exponential backoff
- Provides a reusable decorator
- Re-raises with descriptive message after all retries exhausted
"""

from unittest.mock import patch

import pytest

from core.retry import with_retry


class TestRetrySuccess:
    """Requirement 14.1: Retry on transient errors and succeed on recovery."""

    def test_succeeds_on_first_attempt(self):
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0.0)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_retries_then_succeeds(self):
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0.0)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "recovered"

        assert flaky() == "recovered"
        assert call_count == 3

    def test_retries_on_timeout_error(self):
        call_count = 0

        @with_retry(max_attempts=2, backoff_base=0.0)
        def timeout_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timed out")
            return "done"

        assert timeout_then_ok() == "done"
        assert call_count == 2


class TestRetryExhaustion:
    """Requirement 14.3: Re-raise with descriptive message after all retries."""

    def test_raises_after_max_attempts(self):
        @with_retry(max_attempts=3, backoff_base=0.0)
        def always_fail():
            raise ConnectionError("down")

        with pytest.raises(ConnectionError, match="Failed after 3 retry attempts"):
            always_fail()

    def test_preserves_exception_chain(self):
        @with_retry(max_attempts=2, backoff_base=0.0)
        def always_timeout():
            raise TimeoutError("network")

        with pytest.raises(TimeoutError) as exc_info:
            always_timeout()

        assert exc_info.value.__cause__ is not None
        assert "network" in str(exc_info.value.__cause__)

    def test_does_not_retry_non_retryable_exceptions(self):
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0.0)
        def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            value_error()

        assert call_count == 1


class TestExponentialBackoff:
    """Requirement 14.1: Exponential backoff between retries."""

    @patch("core.retry.time.sleep")
    def test_backoff_delays(self, mock_sleep):
        call_count = 0

        @with_retry(max_attempts=4, backoff_base=1.0)
        def fail_three_times():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ConnectionError("retry me")
            return "ok"

        fail_three_times()

        # Expected delays: 1*2^0=1, 1*2^1=2, 1*2^2=4
        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0, 4.0]

    @patch("core.retry.time.sleep")
    def test_custom_backoff_base(self, mock_sleep):
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0.5)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("slow")
            return "ok"

        fail_twice()

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [0.5, 1.0]


class TestCustomRetryableExceptions:
    """Requirement 14.2: Reusable decorator with configurable exceptions."""

    def test_custom_exception_types(self):
        call_count = 0

        @with_retry(
            max_attempts=3,
            backoff_base=0.0,
            retryable_exceptions=(RuntimeError,),
        )
        def runtime_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("transient runtime")
            return "ok"

        assert runtime_flaky() == "ok"
        assert call_count == 2

    def test_default_retryable_exceptions(self):
        """Default retryable exceptions are ConnectionError and TimeoutError."""
        call_count = 0

        @with_retry(max_attempts=2, backoff_base=0.0)
        def conn_error():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            conn_error()

        assert call_count == 2


class TestDecoratorPreservesMetadata:
    """The decorator should preserve the wrapped function's metadata."""

    def test_preserves_function_name(self):
        @with_retry(max_attempts=2, backoff_base=0.0)
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
