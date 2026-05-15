"""Tests for the circuit breaker module."""

import time
import pytest

from routewatch.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def breaker() -> CircuitBreaker:
    return CircuitBreaker(failure_threshold=3, recovery_timeout_s=30.0)


def test_initial_state_is_closed(breaker: CircuitBreaker) -> None:
    assert breaker.state_of("GET /api") == CircuitState.CLOSED
    assert not breaker.is_open("GET /api")


def test_failure_count_increments(breaker: CircuitBreaker) -> None:
    breaker.record_failure("GET /api", "timeout")
    breaker.record_failure("GET /api", "timeout")
    assert breaker.failure_count("GET /api") == 2
    assert breaker.state_of("GET /api") == CircuitState.CLOSED


def test_circuit_opens_at_threshold(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("GET /api", "500")
    assert breaker.state_of("GET /api") == CircuitState.OPEN
    assert breaker.is_open("GET /api")


def test_success_resets_closed_circuit(breaker: CircuitBreaker) -> None:
    breaker.record_failure("GET /api", "err")
    breaker.record_success("GET /api")
    assert breaker.state_of("GET /api") == CircuitState.CLOSED
    assert breaker.failure_count("GET /api") == 0


def test_circuit_stays_open_within_recovery_window(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("GET /api", "err")
    assert breaker.is_open("GET /api")


def test_circuit_moves_to_half_open_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_s=10.0)
    for _ in range(3):
        breaker.record_failure("GET /api", "err")

    # Simulate time passing beyond recovery timeout
    start = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: start + 11.0)

    assert not breaker.is_open("GET /api")
    assert breaker.state_of("GET /api") == CircuitState.HALF_OPEN


def test_success_after_half_open_closes_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_s=10.0)
    for _ in range(3):
        breaker.record_failure("GET /api", "err")

    start = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: start + 11.0)
    breaker.is_open("GET /api")  # triggers half-open
    breaker.record_success("GET /api")

    assert breaker.state_of("GET /api") == CircuitState.CLOSED


def test_routes_are_tracked_independently(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("GET /slow", "timeout")
    assert breaker.is_open("GET /slow")
    assert not breaker.is_open("GET /fast")


def test_extra_failures_do_not_reopen_already_open(breaker: CircuitBreaker) -> None:
    for _ in range(5):
        breaker.record_failure("GET /api", "err")
    assert breaker.state_of("GET /api") == CircuitState.OPEN
    assert breaker.failure_count("GET /api") == 5
