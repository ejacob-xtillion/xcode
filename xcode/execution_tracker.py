"""
Execution tracking and early stopping for agent runs.

This module provides mechanisms to track agent execution progress and
implement intelligent early stopping to prevent infinite loops and
unnecessary iterations.
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class StopReason(Enum):
    """Reasons for stopping agent execution."""

    COMPLETED = "completed"  # Task completed successfully
    MAX_ITERATIONS = "max_iterations"  # Reached iteration limit
    MAX_TOOL_CALLS = "max_tool_calls"  # Reached tool call limit
    REPEATED_ERRORS = "repeated_errors"  # Same error repeated multiple times
    NO_PROGRESS = "no_progress"  # No meaningful progress detected
    TIMEOUT = "timeout"  # Execution timeout
    USER_INTERRUPT = "user_interrupt"  # User requested stop


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""

    tool_name: str
    timestamp: float
    args_hash: str  # Hash of arguments to detect duplicates
    success: bool
    error: str | None = None


@dataclass
class IterationRecord:
    """Record of a single iteration."""

    iteration: int
    timestamp: float
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    tokens_used: int = 0
    has_output: bool = False
    error: str | None = None


class ExecutionTracker:
    """
    Tracks agent execution and implements early stopping logic.

    Monitors:
    - Iteration count
    - Tool call patterns
    - Error patterns
    - Progress indicators
    - Execution time
    
    Implements the Statsable protocol via get_stats() method.
    """

    def __init__(
        self,
        max_iterations: int = 25,
        max_tool_calls: int = 100,
        max_duplicate_calls: int = 3,
        max_repeated_errors: int = 3,
        timeout_seconds: float = 300.0,
    ):
        """
        Initialize execution tracker.

        Args:
            max_iterations: Maximum number of iterations allowed
            max_tool_calls: Maximum total tool calls allowed
            max_duplicate_calls: Maximum duplicate tool calls before stopping
            max_repeated_errors: Maximum repeated errors before stopping
            timeout_seconds: Maximum execution time in seconds
        """
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self.max_duplicate_calls = max_duplicate_calls
        self.max_repeated_errors = max_repeated_errors
        self.timeout_seconds = timeout_seconds

        self.start_time = time.time()
        self.iterations: list[IterationRecord] = []
        self.current_iteration: IterationRecord | None = None
        self.tool_call_hashes: dict[str, int] = {}  # Hash -> count
        self.error_messages: list[str] = []
        self.should_stop = False
        self.stop_reason: StopReason | None = None

    def start_iteration(self, iteration_num: int) -> None:
        """Start tracking a new iteration."""
        self.current_iteration = IterationRecord(
            iteration=iteration_num,
            timestamp=time.time(),
        )

    def end_iteration(self) -> None:
        """End the current iteration."""
        if self.current_iteration:
            self.iterations.append(self.current_iteration)
            self.current_iteration = None

    def record_tool_call(
        self,
        tool_name: str,
        args_hash: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """
        Record a tool call.

        Args:
            tool_name: Name of the tool
            args_hash: Hash of the arguments
            success: Whether the call succeeded
            error: Error message if failed
        """
        if not self.current_iteration:
            return

        record = ToolCallRecord(
            tool_name=tool_name,
            timestamp=time.time(),
            args_hash=args_hash,
            success=success,
            error=error,
        )

        self.current_iteration.tool_calls.append(record)

        # Track duplicate calls
        call_key = f"{tool_name}:{args_hash}"
        self.tool_call_hashes[call_key] = self.tool_call_hashes.get(call_key, 0) + 1

        # Track errors
        if error:
            self.error_messages.append(error)

    def record_output(self, has_output: bool) -> None:
        """Record whether the iteration produced output."""
        if self.current_iteration:
            self.current_iteration.has_output = has_output

    def check_should_stop(self) -> tuple[bool, StopReason | None]:
        """
        Check if execution should stop.

        Returns:
            Tuple of (should_stop, reason)
        """
        if self.should_stop:
            return True, self.stop_reason

        # Check iteration limit
        if len(self.iterations) >= self.max_iterations:
            self.should_stop = True
            self.stop_reason = StopReason.MAX_ITERATIONS
            return True, StopReason.MAX_ITERATIONS

        # Check tool call limit
        total_tool_calls = sum(len(it.tool_calls) for it in self.iterations)
        if self.current_iteration:
            total_tool_calls += len(self.current_iteration.tool_calls)

        if total_tool_calls >= self.max_tool_calls:
            self.should_stop = True
            self.stop_reason = StopReason.MAX_TOOL_CALLS
            return True, StopReason.MAX_TOOL_CALLS

        # Check for duplicate tool calls
        for call_key, count in self.tool_call_hashes.items():
            if count >= self.max_duplicate_calls:
                self.should_stop = True
                self.stop_reason = StopReason.NO_PROGRESS
                return True, StopReason.NO_PROGRESS

        # Check for repeated errors
        if len(self.error_messages) >= self.max_repeated_errors:
            # Check if the last N errors are similar
            recent_errors = self.error_messages[-self.max_repeated_errors :]
            if len(set(recent_errors)) == 1:  # All the same error
                self.should_stop = True
                self.stop_reason = StopReason.REPEATED_ERRORS
                return True, StopReason.REPEATED_ERRORS

        # Check timeout
        elapsed = time.time() - self.start_time
        if elapsed >= self.timeout_seconds:
            self.should_stop = True
            self.stop_reason = StopReason.TIMEOUT
            return True, StopReason.TIMEOUT

        # Check for no progress (multiple iterations with no output)
        if len(self.iterations) >= 3:
            recent_iterations = self.iterations[-3:]
            if not any(it.has_output for it in recent_iterations):
                self.should_stop = True
                self.stop_reason = StopReason.NO_PROGRESS
                return True, StopReason.NO_PROGRESS

        return False, None

    def mark_completed(self) -> None:
        """Mark execution as completed successfully."""
        self.should_stop = True
        self.stop_reason = StopReason.COMPLETED

    def mark_interrupted(self) -> None:
        """Mark execution as interrupted by user."""
        self.should_stop = True
        self.stop_reason = StopReason.USER_INTERRUPT

    def get_stats(self) -> dict[str, any]:
        """Get execution statistics."""
        total_tool_calls = sum(len(it.tool_calls) for it in self.iterations)
        if self.current_iteration:
            total_tool_calls += len(self.current_iteration.tool_calls)

        successful_calls = sum(
            sum(1 for tc in it.tool_calls if tc.success) for it in self.iterations
        )
        if self.current_iteration:
            successful_calls += sum(1 for tc in self.current_iteration.tool_calls if tc.success)

        elapsed = time.time() - self.start_time

        return {
            "iterations": len(self.iterations),
            "total_tool_calls": total_tool_calls,
            "successful_calls": successful_calls,
            "failed_calls": total_tool_calls - successful_calls,
            "unique_tool_patterns": len(self.tool_call_hashes),
            "errors": len(self.error_messages),
            "elapsed_seconds": elapsed,
            "should_stop": self.should_stop,
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
        }

    def get_duplicate_calls(self) -> list[tuple[str, int]]:
        """Get list of duplicate tool calls."""
        return [(call_key, count) for call_key, count in self.tool_call_hashes.items() if count > 1]

    def reset(self) -> None:
        """Reset the tracker for a new execution."""
        self.start_time = time.time()
        self.iterations.clear()
        self.current_iteration = None
        self.tool_call_hashes.clear()
        self.error_messages.clear()
        self.should_stop = False
        self.stop_reason = None


def hash_tool_args(args: dict) -> str:
    """
    Create a hash of tool arguments for duplicate detection.

    Args:
        args: Tool arguments dictionary

    Returns:
        Hash string
    """
    import hashlib
    import json

    # Sort keys for consistent hashing
    sorted_args = json.dumps(args, sort_keys=True)
    return hashlib.md5(sorted_args.encode()).hexdigest()[:8]
