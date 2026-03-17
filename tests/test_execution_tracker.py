"""
Tests for execution tracking and early stopping.
"""

import time

from xcode.execution_tracker import (
    ExecutionTracker,
    IterationRecord,
    StopReason,
    ToolCallRecord,
    hash_tool_args,
)


class TestExecutionTracker:
    """Test ExecutionTracker."""

    def test_init(self):
        """Test tracker initialization."""
        tracker = ExecutionTracker(
            max_iterations=10,
            max_tool_calls=50,
        )

        assert tracker.max_iterations == 10
        assert tracker.max_tool_calls == 50
        assert len(tracker.iterations) == 0
        assert not tracker.should_stop

    def test_start_end_iteration(self):
        """Test iteration tracking."""
        tracker = ExecutionTracker()

        tracker.start_iteration(1)
        assert tracker.current_iteration is not None
        assert tracker.current_iteration.iteration == 1

        tracker.end_iteration()
        assert tracker.current_iteration is None
        assert len(tracker.iterations) == 1

    def test_record_tool_call(self):
        """Test recording tool calls."""
        tracker = ExecutionTracker()
        tracker.start_iteration(1)

        tracker.record_tool_call(
            tool_name="read_file",
            args_hash="abc123",
            success=True,
        )

        assert len(tracker.current_iteration.tool_calls) == 1
        assert tracker.current_iteration.tool_calls[0].tool_name == "read_file"
        assert tracker.current_iteration.tool_calls[0].success

    def test_max_iterations_stop(self):
        """Test stopping at max iterations."""
        tracker = ExecutionTracker(max_iterations=3)

        for i in range(3):
            tracker.start_iteration(i + 1)
            tracker.end_iteration()

        should_stop, reason = tracker.check_should_stop()
        assert should_stop
        assert reason == StopReason.MAX_ITERATIONS

    def test_max_tool_calls_stop(self):
        """Test stopping at max tool calls."""
        tracker = ExecutionTracker(max_tool_calls=5)

        tracker.start_iteration(1)
        for i in range(5):
            tracker.record_tool_call(
                tool_name="read_file",
                args_hash=f"hash{i}",
                success=True,
            )

        should_stop, reason = tracker.check_should_stop()
        assert should_stop
        assert reason == StopReason.MAX_TOOL_CALLS

    def test_duplicate_calls_stop(self):
        """Test stopping on duplicate tool calls."""
        tracker = ExecutionTracker(max_duplicate_calls=3)

        tracker.start_iteration(1)
        # Make the same call 3 times
        for i in range(3):
            tracker.record_tool_call(
                tool_name="read_file",
                args_hash="same_hash",
                success=True,
            )

        should_stop, reason = tracker.check_should_stop()
        assert should_stop
        assert reason == StopReason.NO_PROGRESS

    def test_repeated_errors_stop(self):
        """Test stopping on repeated errors."""
        tracker = ExecutionTracker(max_repeated_errors=3)

        tracker.start_iteration(1)
        # Record the same error 3 times
        for i in range(3):
            tracker.record_tool_call(
                tool_name="read_file",
                args_hash=f"hash{i}",
                success=False,
                error="File not found",
            )

        should_stop, reason = tracker.check_should_stop()
        assert should_stop
        assert reason == StopReason.REPEATED_ERRORS

    def test_timeout_stop(self):
        """Test stopping on timeout."""
        tracker = ExecutionTracker(timeout_seconds=0.1)

        tracker.start_iteration(1)
        time.sleep(0.15)

        should_stop, reason = tracker.check_should_stop()
        assert should_stop
        assert reason == StopReason.TIMEOUT

    def test_no_progress_stop(self):
        """Test stopping when no progress is made."""
        tracker = ExecutionTracker()

        # Create 3 iterations with no output
        for i in range(3):
            tracker.start_iteration(i + 1)
            tracker.record_output(False)
            tracker.end_iteration()

        should_stop, reason = tracker.check_should_stop()
        assert should_stop
        assert reason == StopReason.NO_PROGRESS

    def test_progress_continues(self):
        """Test that execution continues when making progress."""
        tracker = ExecutionTracker()

        # Create 3 iterations with output
        for i in range(3):
            tracker.start_iteration(i + 1)
            tracker.record_output(True)
            tracker.end_iteration()

        should_stop, reason = tracker.check_should_stop()
        assert not should_stop
        assert reason is None

    def test_mark_completed(self):
        """Test marking execution as completed."""
        tracker = ExecutionTracker()

        tracker.mark_completed()

        assert tracker.should_stop
        assert tracker.stop_reason == StopReason.COMPLETED

    def test_mark_interrupted(self):
        """Test marking execution as interrupted."""
        tracker = ExecutionTracker()

        tracker.mark_interrupted()

        assert tracker.should_stop
        assert tracker.stop_reason == StopReason.USER_INTERRUPT

    def test_get_stats(self):
        """Test getting execution statistics."""
        tracker = ExecutionTracker()

        tracker.start_iteration(1)
        tracker.record_tool_call("read_file", "hash1", True)
        tracker.record_tool_call("write_file", "hash2", False, "Error")
        tracker.end_iteration()

        stats = tracker.get_stats()

        assert stats["iterations"] == 1
        assert stats["total_tool_calls"] == 2
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 1
        assert stats["errors"] == 1
        assert not stats["should_stop"]

    def test_get_duplicate_calls(self):
        """Test getting duplicate calls."""
        tracker = ExecutionTracker()

        tracker.start_iteration(1)
        tracker.record_tool_call("read_file", "hash1", True)
        tracker.record_tool_call("read_file", "hash1", True)
        tracker.record_tool_call("write_file", "hash2", True)

        duplicates = tracker.get_duplicate_calls()

        assert len(duplicates) == 1
        assert duplicates[0][0] == "read_file:hash1"
        assert duplicates[0][1] == 2

    def test_reset(self):
        """Test resetting the tracker."""
        tracker = ExecutionTracker()

        tracker.start_iteration(1)
        tracker.record_tool_call("read_file", "hash1", True)
        tracker.end_iteration()
        tracker.mark_completed()

        tracker.reset()

        assert len(tracker.iterations) == 0
        assert tracker.current_iteration is None
        assert not tracker.should_stop
        assert tracker.stop_reason is None
        assert len(tracker.tool_call_hashes) == 0
        assert len(tracker.error_messages) == 0

    def test_different_errors_dont_stop(self):
        """Test that different errors don't trigger early stop."""
        tracker = ExecutionTracker(max_repeated_errors=3)

        tracker.start_iteration(1)
        tracker.record_tool_call("read_file", "hash1", False, "Error 1")
        tracker.record_tool_call("read_file", "hash2", False, "Error 2")
        tracker.record_tool_call("read_file", "hash3", False, "Error 3")

        should_stop, reason = tracker.check_should_stop()
        assert not should_stop


class TestToolCallRecord:
    """Test ToolCallRecord dataclass."""

    def test_creation(self):
        """Test creating a tool call record."""
        record = ToolCallRecord(
            tool_name="read_file",
            timestamp=time.time(),
            args_hash="abc123",
            success=True,
        )

        assert record.tool_name == "read_file"
        assert record.success
        assert record.error is None

    def test_with_error(self):
        """Test creating a record with an error."""
        record = ToolCallRecord(
            tool_name="read_file",
            timestamp=time.time(),
            args_hash="abc123",
            success=False,
            error="File not found",
        )

        assert not record.success
        assert record.error == "File not found"


class TestIterationRecord:
    """Test IterationRecord dataclass."""

    def test_creation(self):
        """Test creating an iteration record."""
        record = IterationRecord(
            iteration=1,
            timestamp=time.time(),
        )

        assert record.iteration == 1
        assert len(record.tool_calls) == 0
        assert not record.has_output

    def test_with_tool_calls(self):
        """Test iteration with tool calls."""
        tool_call = ToolCallRecord(
            tool_name="read_file",
            timestamp=time.time(),
            args_hash="abc123",
            success=True,
        )

        record = IterationRecord(
            iteration=1,
            timestamp=time.time(),
            tool_calls=[tool_call],
            has_output=True,
        )

        assert len(record.tool_calls) == 1
        assert record.has_output


class TestHashToolArgs:
    """Test hash_tool_args function."""

    def test_same_args_same_hash(self):
        """Test that same arguments produce same hash."""
        args1 = {"file": "test.py", "mode": "r"}
        args2 = {"file": "test.py", "mode": "r"}

        hash1 = hash_tool_args(args1)
        hash2 = hash_tool_args(args2)

        assert hash1 == hash2

    def test_different_args_different_hash(self):
        """Test that different arguments produce different hash."""
        args1 = {"file": "test.py", "mode": "r"}
        args2 = {"file": "other.py", "mode": "r"}

        hash1 = hash_tool_args(args1)
        hash2 = hash_tool_args(args2)

        assert hash1 != hash2

    def test_order_independent(self):
        """Test that argument order doesn't affect hash."""
        args1 = {"file": "test.py", "mode": "r"}
        args2 = {"mode": "r", "file": "test.py"}

        hash1 = hash_tool_args(args1)
        hash2 = hash_tool_args(args2)

        assert hash1 == hash2

    def test_empty_args(self):
        """Test hashing empty arguments."""
        hash1 = hash_tool_args({})
        hash2 = hash_tool_args({})

        assert hash1 == hash2
        assert isinstance(hash1, str)
