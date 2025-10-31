"""
Unit Tests for Error Recovery Modules

Tests circuit breaker pattern and retry manager including:
- Circuit breaker state transitions
- Failure threshold management
- Retry strategies (exponential, linear, fixed, fibonacci)
- Exception filtering
- Statistics tracking

Author: Validation Engineer Team 2
Date: 2025-10-30
Sprint: 3, Stream A
"""

import time

import pytest

from workspace.features.error_recovery.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from workspace.features.error_recovery.retry_manager import (
    RetryManager,
    RetryStrategy,
    retry,
)


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


@pytest.fixture
def circuit_breaker():
    """Circuit breaker with default settings"""
    return CircuitBreaker(
        name="test_circuit",
        failure_threshold=3,
        recovery_timeout_seconds=5,
        half_open_max_calls=2,
    )


# --- Initialization Tests ---


def test_circuit_breaker_initialization(circuit_breaker):
    """Test circuit breaker initializes correctly"""
    assert circuit_breaker.name == "test_circuit"
    assert circuit_breaker.failure_threshold == 3
    assert circuit_breaker.recovery_timeout_seconds == 5
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.is_closed is True


def test_circuit_breaker_custom_exception():
    """Test circuit breaker with custom exception type"""
    cb = CircuitBreaker(
        name="custom",
        expected_exception=ValueError,
    )

    assert cb.expected_exception is ValueError


# --- State Property Tests ---


def test_circuit_breaker_is_closed(circuit_breaker):
    """Test is_closed property"""
    assert circuit_breaker.is_closed is True
    assert circuit_breaker.is_open is False
    assert circuit_breaker.is_half_open is False


def test_circuit_breaker_is_open(circuit_breaker):
    """Test is_open property after failures"""
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._opened_at = time.time()

    assert circuit_breaker.is_open is True
    assert circuit_breaker.is_closed is False


def test_circuit_breaker_is_half_open(circuit_breaker):
    """Test is_half_open property"""
    circuit_breaker._state = CircuitState.HALF_OPEN

    assert circuit_breaker.is_half_open is True
    assert circuit_breaker.is_closed is False


# --- State Transition Tests ---


@pytest.mark.asyncio
async def test_circuit_transitions_to_open_on_failures(circuit_breaker):
    """Test circuit opens after threshold failures"""

    async def failing_func():
        raise Exception("Failure")

    # First 2 failures - should remain closed
    for _ in range(2):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitState.CLOSED

    # 3rd failure - should open
    with pytest.raises(Exception):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.stats["state_changes"] == 1


@pytest.mark.asyncio
async def test_circuit_blocks_calls_when_open(circuit_breaker):
    """Test circuit blocks calls when open"""

    async def failing_func():
        raise Exception("Failure")

    # Trigger 3 failures to open circuit
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    # Next call should be rejected
    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.stats["rejected_calls"] == 1


@pytest.mark.asyncio
async def test_circuit_transitions_to_half_open_after_timeout(circuit_breaker):
    """Test circuit transitions to half-open after timeout"""
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._opened_at = time.time() - 10  # 10 seconds ago

    # Check should trigger transition to half-open
    _ = circuit_breaker.is_open

    assert circuit_breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_transitions_to_closed_on_success(circuit_breaker):
    """Test half-open transitions to closed after successful calls"""
    circuit_breaker._state = CircuitState.HALF_OPEN
    circuit_breaker.half_open_max_calls = 2

    async def success_func():
        return "success"

    # First success
    result = await circuit_breaker.call(success_func)
    assert result == "success"
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    # Second success - should close circuit
    result = await circuit_breaker.call(success_func)
    assert circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_reopens_on_failure(circuit_breaker):
    """Test half-open reopens on any failure"""
    circuit_breaker._state = CircuitState.HALF_OPEN

    async def failing_func():
        raise Exception("Failure")

    with pytest.raises(Exception):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.state == CircuitState.OPEN


# --- Success/Failure Recording Tests ---


@pytest.mark.asyncio
async def test_record_success_resets_failure_count(circuit_breaker):
    """Test success resets failure count in closed state"""

    async def failing_func():
        raise Exception("Failure")

    async def success_func():
        return "success"

    # 2 failures
    for _ in range(2):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker._failure_count == 2

    # 1 success - should reset
    await circuit_breaker.call(success_func)
    assert circuit_breaker._failure_count == 0


@pytest.mark.asyncio
async def test_only_expected_exceptions_trigger_circuit(circuit_breaker):
    """Test only expected exception types trigger circuit"""
    circuit_breaker.expected_exception = ValueError

    async def value_error_func():
        raise ValueError("Expected")

    async def type_error_func():
        raise TypeError("Not expected")

    # ValueError should count
    with pytest.raises(ValueError):
        await circuit_breaker.call(value_error_func)
    assert circuit_breaker._failure_count == 1

    # TypeError should not count
    with pytest.raises(TypeError):
        await circuit_breaker.call(type_error_func)
    assert circuit_breaker._failure_count == 1  # Still 1


# --- Sync Function Support Tests ---


@pytest.mark.asyncio
async def test_circuit_supports_sync_functions(circuit_breaker):
    """Test circuit breaker works with sync functions"""

    def sync_func():
        return "sync_result"

    result = await circuit_breaker.call(sync_func)
    assert result == "sync_result"


# --- Manual Reset Tests ---


def test_manual_reset(circuit_breaker):
    """Test manual circuit reset"""
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._failure_count = 5

    circuit_breaker.reset()

    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker._failure_count == 0


# --- Statistics Tests ---


def test_get_stats(circuit_breaker):
    """Test getting circuit breaker statistics"""
    stats = circuit_breaker.get_stats()

    assert stats["name"] == "test_circuit"
    assert stats["state"] == "closed"
    assert stats["failure_threshold"] == 3
    assert stats["total_calls"] == 0


@pytest.mark.asyncio
async def test_stats_tracking(circuit_breaker):
    """Test statistics are tracked correctly"""

    async def success_func():
        return "success"

    async def failing_func():
        raise Exception("Failure")

    # 2 successes
    await circuit_breaker.call(success_func)
    await circuit_breaker.call(success_func)

    # 1 failure
    with pytest.raises(Exception):
        await circuit_breaker.call(failing_func)

    stats = circuit_breaker.get_stats()
    assert stats["total_calls"] == 3
    assert stats["successful_calls"] == 2
    assert stats["failed_calls"] == 1


# ============================================================================
# Retry Manager Tests
# ============================================================================


@pytest.fixture
def retry_manager():
    """Retry manager with default settings"""
    return RetryManager(
        max_retries=3,
        base_delay_seconds=0.1,  # Fast for testing
        max_delay_seconds=1.0,
        strategy=RetryStrategy.EXPONENTIAL,
    )


# --- Initialization Tests ---


def test_retry_manager_initialization(retry_manager):
    """Test retry manager initializes correctly"""
    assert retry_manager.max_retries == 3
    assert retry_manager.base_delay_seconds == 0.1
    assert retry_manager.strategy == RetryStrategy.EXPONENTIAL


# --- Delay Calculation Tests ---


def test_exponential_backoff_calculation(retry_manager):
    """Test exponential backoff calculation"""
    retry_manager.strategy = RetryStrategy.EXPONENTIAL
    retry_manager.jitter = False

    delays = [retry_manager._calculate_delay(i) for i in range(4)]

    # Should be: 0.1, 0.2, 0.4, 0.8
    assert delays[0] == 0.1
    assert delays[1] == 0.2
    assert delays[2] == 0.4
    assert delays[3] == 0.8


def test_linear_backoff_calculation(retry_manager):
    """Test linear backoff calculation"""
    retry_manager.strategy = RetryStrategy.LINEAR
    retry_manager.jitter = False

    delays = [retry_manager._calculate_delay(i) for i in range(4)]

    # Should be: 0.1, 0.2, 0.3, 0.4
    assert abs(delays[0] - 0.1) < 1e-9
    assert abs(delays[1] - 0.2) < 1e-9
    assert abs(delays[2] - 0.3) < 1e-9
    assert abs(delays[3] - 0.4) < 1e-9


def test_fixed_backoff_calculation(retry_manager):
    """Test fixed backoff calculation"""
    retry_manager.strategy = RetryStrategy.FIXED
    retry_manager.jitter = False

    delays = [retry_manager._calculate_delay(i) for i in range(4)]

    # All should be 0.1
    assert all(d == 0.1 for d in delays)


def test_fibonacci_backoff_calculation(retry_manager):
    """Test Fibonacci backoff calculation"""
    retry_manager.strategy = RetryStrategy.FIBONACCI
    retry_manager.jitter = False

    delays = [retry_manager._calculate_delay(i) for i in range(5)]

    # Should be: 0.1*1, 0.1*1, 0.1*2, 0.1*3, 0.1*5
    assert abs(delays[0] - 0.1) < 1e-9
    assert abs(delays[1] - 0.1) < 1e-9
    assert abs(delays[2] - 0.2) < 1e-9
    assert abs(delays[3] - 0.3) < 1e-9
    assert abs(delays[4] - 0.5) < 1e-9


def test_max_delay_cap(retry_manager):
    """Test delay is capped at max_delay"""
    retry_manager.strategy = RetryStrategy.EXPONENTIAL
    retry_manager.jitter = False
    retry_manager.max_delay_seconds = 0.5

    # At attempt 10, exponential would be 0.1 * 2^10 = 102.4
    # But should be capped at 0.5
    delay = retry_manager._calculate_delay(10)
    assert delay == 0.5


def test_jitter_adds_randomness(retry_manager):
    """Test jitter adds randomness to delays"""
    retry_manager.jitter = True

    delays = [retry_manager._calculate_delay(1) for _ in range(10)]

    # All should be different due to jitter
    assert len(set(delays)) > 1


# --- Fibonacci Helper Tests ---


def test_fibonacci_sequence():
    """Test Fibonacci number calculation"""
    fib = RetryManager._fibonacci

    assert fib(0) == 0
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(3) == 2
    assert fib(4) == 3
    assert fib(5) == 5
    assert fib(6) == 8


# --- Retry Execution Tests ---


@pytest.mark.asyncio
async def test_execute_success_first_attempt(retry_manager):
    """Test successful execution on first attempt"""
    call_count = 0

    async def success_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_manager.execute(success_func)

    assert result == "success"
    assert call_count == 1
    assert retry_manager.stats["successful_calls"] == 1
    assert retry_manager.stats["total_retries"] == 0


@pytest.mark.asyncio
async def test_execute_success_after_retries(retry_manager):
    """Test successful execution after retries"""
    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    result = await retry_manager.execute(flaky_func)

    assert result == "success"
    assert call_count == 3
    assert retry_manager.stats["total_retries"] == 2


@pytest.mark.asyncio
async def test_execute_all_retries_exhausted(retry_manager):
    """Test failure when all retries exhausted"""
    call_count = 0

    async def failing_func():
        nonlocal call_count
        call_count += 1
        raise Exception("Persistent failure")

    with pytest.raises(Exception, match="Persistent failure"):
        await retry_manager.execute(failing_func)

    # Should try: initial + 3 retries = 4 times
    assert call_count == 4
    assert retry_manager.stats["failed_calls"] == 1


@pytest.mark.asyncio
async def test_execute_non_retryable_exception(retry_manager):
    """Test non-retryable exception fails immediately"""
    retry_manager.retryable_exceptions = (ValueError,)
    call_count = 0

    async def type_error_func():
        nonlocal call_count
        call_count += 1
        raise TypeError("Not retryable")

    with pytest.raises(TypeError):
        await retry_manager.execute(type_error_func)

    # Should only try once
    assert call_count == 1


@pytest.mark.asyncio
async def test_execute_sync_function(retry_manager):
    """Test retry manager works with sync functions"""

    def sync_func():
        return "sync_result"

    result = await retry_manager.execute(sync_func)
    assert result == "sync_result"


# --- Statistics Tests ---


def test_get_retry_stats(retry_manager):
    """Test getting retry statistics"""
    stats = retry_manager.get_stats()

    assert "total_calls" in stats
    assert "successful_calls" in stats
    assert "success_rate" in stats
    assert "average_retries_per_success" in stats


@pytest.mark.asyncio
async def test_retry_stats_tracking(retry_manager):
    """Test retry statistics tracking"""
    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("First fail")
        return "success"

    # Execute twice
    await retry_manager.execute(flaky_func)
    call_count = 0
    await retry_manager.execute(flaky_func)

    stats = retry_manager.get_stats()
    assert stats["total_calls"] == 2
    assert stats["successful_calls"] == 2
    assert stats["total_retries"] == 2  # 1 retry per call


# --- Decorator Tests ---


@pytest.mark.asyncio
async def test_retry_decorator():
    """Test retry decorator"""
    call_count = 0

    @retry(max_retries=2, base_delay=0.01, strategy=RetryStrategy.FIXED)
    async def decorated_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Fail once")
        return "success"

    result = await decorated_func()

    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_decorator_with_custom_exceptions():
    """Test retry decorator with custom exception filtering"""

    @retry(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
    async def decorated_func():
        raise TypeError("Not retryable")

    with pytest.raises(TypeError):
        await decorated_func()


# ============================================================================
# Additional Circuit Breaker Coverage Tests
# ============================================================================


@pytest.mark.asyncio
async def test_circuit_breaker_concurrent_requests(circuit_breaker):
    """Test circuit breaker handles concurrent requests"""
    import asyncio

    call_count = 0

    async def concurrent_func():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # Simulate async work
        return f"result_{call_count}"

    # Execute multiple concurrent requests
    tasks = [circuit_breaker.call(concurrent_func) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert circuit_breaker.stats["successful_calls"] == 5


@pytest.mark.asyncio
async def test_circuit_breaker_rapid_failures(circuit_breaker):
    """Test circuit breaker handles rapid consecutive failures"""

    async def rapid_fail():
        raise Exception("Rapid failure")

    # Trigger failures rapidly
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(rapid_fail)

    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker._failure_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_multiple_successes(circuit_breaker):
    """Test half-open requires multiple successes to close"""
    circuit_breaker._state = CircuitState.HALF_OPEN
    circuit_breaker.half_open_max_calls = 3

    async def success_func():
        return "success"

    # First two successes - should remain half-open
    await circuit_breaker.call(success_func)
    await circuit_breaker.call(success_func)
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    # Third success - should close
    await circuit_breaker.call(success_func)
    assert circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_immediate_reopen(circuit_breaker):
    """Test half-open immediately reopens on first failure"""
    circuit_breaker._state = CircuitState.HALF_OPEN

    async def failing_func():
        raise Exception("Test failure")

    # First failure in half-open should reopen
    with pytest.raises(Exception):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.state == CircuitState.OPEN


def test_circuit_breaker_state_property(circuit_breaker):
    """Test state property returns correct state"""
    assert circuit_breaker.state == CircuitState.CLOSED

    circuit_breaker._state = CircuitState.OPEN
    assert circuit_breaker.state == CircuitState.OPEN

    circuit_breaker._state = CircuitState.HALF_OPEN
    assert circuit_breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_is_properties_exclusive(circuit_breaker):
    """Test is_closed, is_open, is_half_open are mutually exclusive"""
    # CLOSED state
    circuit_breaker._state = CircuitState.CLOSED
    assert circuit_breaker.is_closed is True
    assert circuit_breaker.is_open is False
    assert circuit_breaker.is_half_open is False

    # OPEN state
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._opened_at = time.time()
    assert circuit_breaker.is_closed is False
    assert circuit_breaker.is_open is True
    assert circuit_breaker.is_half_open is False

    # HALF_OPEN state
    circuit_breaker._state = CircuitState.HALF_OPEN
    assert circuit_breaker.is_closed is False
    assert circuit_breaker.is_open is False
    assert circuit_breaker.is_half_open is True


@pytest.mark.asyncio
async def test_circuit_breaker_success_resets_failure_count_in_closed(circuit_breaker):
    """Test success resets failure count in closed state"""

    async def failing_func():
        raise Exception("Failure")

    async def success_func():
        return "success"

    # 1 failure
    with pytest.raises(Exception):
        await circuit_breaker.call(failing_func)
    assert circuit_breaker._failure_count == 1

    # Success should reset
    await circuit_breaker.call(success_func)
    assert circuit_breaker._failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_stats_rejected_calls(circuit_breaker):
    """Test rejected calls are counted in statistics"""

    async def failing_func():
        raise Exception("Failure")

    # Open the circuit
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    # Try to call while open - should reject
    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_func)

    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.stats["rejected_calls"] == 2


def test_circuit_breaker_get_stats_includes_timestamps(circuit_breaker):
    """Test get_stats includes timestamp information"""
    circuit_breaker._last_failure_time = time.time()

    stats = circuit_breaker.get_stats()

    assert "last_failure_time" in stats
    assert stats["last_failure_time"] is not None


def test_circuit_breaker_get_stats_opened_at(circuit_breaker):
    """Test get_stats includes opened_at when circuit is open"""
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._opened_at = time.time()

    stats = circuit_breaker.get_stats()

    assert "opened_at" in stats
    assert stats["opened_at"] is not None


def test_circuit_breaker_reset_clears_all_state(circuit_breaker):
    """Test manual reset clears all state"""
    # Set various state
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._failure_count = 5
    circuit_breaker._success_count = 2
    circuit_breaker._opened_at = time.time()

    # Reset
    circuit_breaker.reset()

    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker._failure_count == 0
    assert circuit_breaker._success_count == 0
    assert circuit_breaker._opened_at is None


@pytest.mark.asyncio
async def test_circuit_breaker_sync_function_returning_coroutine(circuit_breaker):
    """Test circuit breaker handles sync function returning coroutine"""

    async def async_inner():
        return "async_result"

    def sync_returns_coroutine():
        return async_inner()

    result = await circuit_breaker.call(sync_returns_coroutine)
    assert result == "async_result"


@pytest.mark.asyncio
async def test_circuit_breaker_exception_propagation(circuit_breaker):
    """Test circuit breaker propagates original exception"""

    class CustomError(Exception):
        pass

    async def custom_error_func():
        raise CustomError("Custom message")

    with pytest.raises(CustomError, match="Custom message"):
        await circuit_breaker.call(custom_error_func)


@pytest.mark.asyncio
async def test_circuit_breaker_auto_transition_to_half_open(circuit_breaker):
    """Test automatic transition from OPEN to HALF_OPEN after timeout"""
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._opened_at = time.time() - 10  # 10 seconds ago
    circuit_breaker.recovery_timeout_seconds = 5

    # Checking is_open should trigger transition
    is_open = circuit_breaker.is_open

    assert is_open is False  # Not open anymore
    assert circuit_breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_no_auto_transition_before_timeout(circuit_breaker):
    """Test no auto transition before timeout expires"""
    circuit_breaker._state = CircuitState.OPEN
    circuit_breaker._opened_at = time.time() - 2  # 2 seconds ago
    circuit_breaker.recovery_timeout_seconds = 5

    # Check is_open - should not transition yet
    is_open = circuit_breaker.is_open

    assert is_open is True
    assert circuit_breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_failure_count_increments_correctly(circuit_breaker):
    """Test failure count increments correctly"""

    async def failing_func():
        raise Exception("Failure")

    # Track failure count
    for i in range(1, 4):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)
        # After opening, failure count stays at threshold
        expected_count = min(i, circuit_breaker.failure_threshold)
        assert circuit_breaker._failure_count == expected_count


@pytest.mark.asyncio
async def test_circuit_breaker_last_failure_time_updated(circuit_breaker):
    """Test last_failure_time is updated on each failure"""

    async def failing_func():
        raise Exception("Failure")

    before = time.time()
    with pytest.raises(Exception):
        await circuit_breaker.call(failing_func)
    after = time.time()

    assert circuit_breaker._last_failure_time is not None
    assert before <= circuit_breaker._last_failure_time <= after


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_circuit_breaker_with_retry_manager():
    """Test circuit breaker and retry manager together"""
    cb = CircuitBreaker(name="integration", failure_threshold=2)
    rm = RetryManager(max_retries=1, base_delay_seconds=0.01)

    failure_count = 0

    async def flaky_service():
        nonlocal failure_count
        failure_count += 1
        if failure_count <= 2:
            raise Exception("Service unavailable")
        return "success"

    async def call_with_circuit():
        return await cb.call(flaky_service)

    # First call with retry - should fail twice and open circuit
    with pytest.raises(Exception):
        await rm.execute(call_with_circuit)

    assert cb.state == CircuitState.OPEN

    # Second call should be rejected by circuit breaker
    with pytest.raises(CircuitBreakerOpenError):
        await rm.execute(call_with_circuit)


@pytest.mark.asyncio
async def test_multiple_circuit_breakers_independent():
    """Test multiple circuit breakers operate independently"""
    cb1 = CircuitBreaker(name="service1", failure_threshold=2)
    cb2 = CircuitBreaker(name="service2", failure_threshold=2)

    async def failing_func():
        raise Exception("Failure")

    # Open cb1
    for _ in range(2):
        with pytest.raises(Exception):
            await cb1.call(failing_func)

    # cb1 should be open, cb2 should be closed
    assert cb1.state == CircuitState.OPEN
    assert cb2.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=workspace/features/error_recovery"])
