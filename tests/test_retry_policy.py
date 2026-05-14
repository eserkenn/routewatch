"""Tests for routewatch.retry_policy."""

from __future__ import annotations

import pytest

from routewatch.retry_policy import RetryPolicy, with_retry


# ---------------------------------------------------------------------------
# RetryPolicy.delay_for
# ---------------------------------------------------------------------------


def test_first_attempt_has_no_delay():
    policy = RetryPolicy(base_delay_s=1.0, backoff_factor=2.0)
    assert policy.delay_for(0) == 0.0


def test_second_attempt_uses_base_delay():
    policy = RetryPolicy(base_delay_s=0.5, backoff_factor=2.0)
    assert policy.delay_for(1) == pytest.approx(0.5)


def test_backoff_multiplies_delay():
    policy = RetryPolicy(base_delay_s=1.0, backoff_factor=3.0)
    assert policy.delay_for(2) == pytest.approx(3.0)


def test_delay_capped_at_max():
    policy = RetryPolicy(base_delay_s=1.0, backoff_factor=10.0, max_delay_s=5.0)
    assert policy.delay_for(3) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------


def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    """Drop-in replacement that skips actual sleeping."""


def test_success_on_first_attempt():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    result = with_retry(fn, RetryPolicy(max_retries=2), _sleep=_no_sleep)
    assert result == "ok"
    assert len(calls) == 1


def test_retries_on_failure_then_succeeds():
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("transient")
        return "recovered"

    result = with_retry(
        fn, RetryPolicy(max_retries=3), route_url="http://x", _sleep=_no_sleep
    )
    assert result == "recovered"
    assert len(attempts) == 3


def test_raises_after_all_attempts_exhausted():
    def fn():
        raise TimeoutError("always fails")

    with pytest.raises(TimeoutError, match="always fails"):
        with_retry(fn, RetryPolicy(max_retries=2), _sleep=_no_sleep)


def test_total_call_count_equals_max_retries_plus_one():
    calls = []

    def fn():
        calls.append(1)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        with_retry(fn, RetryPolicy(max_retries=4), _sleep=_no_sleep)

    assert len(calls) == 5


def test_sleep_called_with_correct_delays():
    slept: list[float] = []
    policy = RetryPolicy(max_retries=2, base_delay_s=1.0, backoff_factor=2.0)

    def fn():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        with_retry(fn, policy, _sleep=slept.append)

    # First attempt: no sleep; 2nd attempt: 1.0 s; 3rd attempt: 2.0 s
    assert slept == pytest.approx([1.0, 2.0])
