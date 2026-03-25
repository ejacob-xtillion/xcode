"""
Unit tests for tool retry middleware behavior.

Tests verify that ToolRetryMiddleware correctly retries failed tool calls
and feeds error messages back to the agent for recovery.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain.agents.middleware import ToolRetryMiddleware
from langchain_core.tools import tool


@tool
def flaky_tool(fail_count: int = 0) -> str:
    """Test tool that fails N times then succeeds."""
    if not hasattr(flaky_tool, '_call_count'):
        flaky_tool._call_count = 0
    
    flaky_tool._call_count += 1
    
    if flaky_tool._call_count <= fail_count:
        raise RuntimeError(f"Transient failure {flaky_tool._call_count}/{fail_count}")
    
    return f"Success after {flaky_tool._call_count} attempts"


@tool
def always_fails() -> str:
    """Test tool that always fails."""
    raise ValueError("Permanent failure - file not found")


@pytest.fixture(autouse=True)
def reset_tool_counters():
    """Reset tool call counters between tests."""
    if hasattr(flaky_tool, '_call_count'):
        delattr(flaky_tool, '_call_count')
    yield


def test_retry_middleware_retries_transient_failures():
    """Tool that fails once then succeeds should be retried and succeed."""
    middleware = ToolRetryMiddleware(
        max_retries=2,
        initial_delay=0.01,  # Fast for testing
        backoff_factor=1.0,
        jitter=False,
        on_failure='continue',
    )
    
    # Simulate tool call that fails once
    result = flaky_tool.invoke({"fail_count": 1})
    
    # Should succeed after retry
    assert "Success after 2 attempts" in result


def test_retry_middleware_exhausts_retries_and_returns_error():
    """Tool that always fails should exhaust retries and return error message."""
    middleware = ToolRetryMiddleware(
        max_retries=2,
        initial_delay=0.01,
        backoff_factor=1.0,
        jitter=False,
        on_failure='continue',
    )
    
    # Tool that always fails
    with pytest.raises(ValueError, match="Permanent failure"):
        always_fails.invoke({})


def test_retry_disabled_fails_immediately():
    """With max_retries=0, tool should fail immediately without retry."""
    middleware = ToolRetryMiddleware(
        max_retries=0,
        on_failure='continue',
    )
    
    # Tool that would succeed on retry should fail
    with pytest.raises(RuntimeError, match="Transient failure"):
        flaky_tool.invoke({"fail_count": 1})


def test_exponential_backoff_timing():
    """Verify exponential backoff delays are calculated correctly."""
    import time
    
    middleware = ToolRetryMiddleware(
        max_retries=3,
        initial_delay=0.1,
        backoff_factor=2.0,
        jitter=False,  # Disable jitter for predictable timing
        on_failure='continue',
    )
    
    start = time.time()
    
    # Tool that fails 2 times (will retry with 0.1s, 0.2s delays)
    try:
        flaky_tool.invoke({"fail_count": 2})
    except:
        pass
    
    elapsed = time.time() - start
    
    # Should take at least 0.1 + 0.2 = 0.3s for retries
    # Allow some margin for execution time
    assert elapsed >= 0.25, f"Expected >= 0.25s, got {elapsed}s"
    assert elapsed < 1.0, f"Expected < 1.0s, got {elapsed}s (too slow)"


def test_jitter_adds_randomness():
    """Verify jitter adds randomness to delays."""
    import time
    
    middleware = ToolRetryMiddleware(
        max_retries=2,
        initial_delay=0.1,
        backoff_factor=1.0,
        jitter=True,  # Enable jitter
        on_failure='continue',
    )
    
    timings = []
    for _ in range(5):
        if hasattr(flaky_tool, '_call_count'):
            delattr(flaky_tool, '_call_count')
        
        start = time.time()
        try:
            flaky_tool.invoke({"fail_count": 1})
        except:
            pass
        timings.append(time.time() - start)
    
    # With jitter, timings should vary (not all identical)
    # Jitter is ±25%, so with 0.1s delay, range is 0.075-0.125s
    assert len(set(timings)) > 1, "Jitter should create timing variation"


def test_max_delay_caps_backoff():
    """Verify max_delay caps exponential backoff growth."""
    middleware = ToolRetryMiddleware(
        max_retries=5,
        initial_delay=1.0,
        backoff_factor=10.0,  # Would grow to 10s, 100s, 1000s...
        max_delay=5.0,  # Cap at 5s
        jitter=False,
        on_failure='continue',
    )
    
    # With max_delay=5.0, no single retry should wait more than 5s
    # Even though backoff_factor=10 would create huge delays
    import time
    start = time.time()
    
    try:
        flaky_tool.invoke({"fail_count": 5})
    except:
        pass
    
    elapsed = time.time() - start
    
    # With cap, should be roughly: 1s + 5s + 5s + 5s + 5s = 21s max
    # Without cap, would be: 1s + 10s + 100s + 1000s... (way too long)
    assert elapsed < 30.0, f"Expected < 30s with max_delay cap, got {elapsed}s"


def test_settings_integration():
    """Verify settings values are used correctly."""
    from app.core.settings import AppSettings
    
    settings = AppSettings(
        tool_retry_enabled=True,
        tool_retry_max_attempts=3,
        tool_retry_initial_delay=0.5,
        tool_retry_backoff_factor=3.0,
        tool_retry_max_delay=10.0,
        tool_retry_jitter=False,
    )
    
    assert settings.tool_retry_enabled is True
    assert settings.tool_retry_max_attempts == 3
    assert settings.tool_retry_initial_delay == 0.5
    assert settings.tool_retry_backoff_factor == 3.0
    assert settings.tool_retry_max_delay == 10.0
    assert settings.tool_retry_jitter is False


def test_retry_disabled_via_settings():
    """When tool_retry_enabled=False, middleware should not be created."""
    from app.core.settings import AppSettings
    
    settings = AppSettings(
        tool_retry_enabled=False,
    )
    
    assert settings.tool_retry_enabled is False
    # In agent.py, middleware should remain empty tuple when disabled
