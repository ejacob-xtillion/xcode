"""
Tests for agent_runner module
"""

from unittest.mock import Mock

import pytest
from rich.console import Console

from xcode.agent_runner import AgentRunner
from xcode.models import AgentResult as XCodeResult
from xcode.models import XCodeConfig


@pytest.fixture
def mock_console():
    """Create a mock console."""
    return Mock(spec=Console)


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration."""
    return XCodeConfig(
        task="test task",
        repo_path=tmp_path,
        language="python",
        project_name="test-project",
        verbose=False,
    )


class TestAgentRunner:
    """Tests for AgentRunner."""

    def test_init(self, test_config, mock_console):
        """Test AgentRunner initialization."""
        runner = AgentRunner(test_config, mock_console)
        assert runner.config == test_config
        assert runner.console == mock_console
        assert runner.current_iteration == 0

    def test_run_returns_result(self, test_config, mock_console):
        """Test that run() returns an XCodeResult."""
        runner = AgentRunner(test_config, mock_console)
        result = runner.run()

        assert isinstance(result, XCodeResult)
        assert result.task == test_config.task

    def test_get_agent_context(self, test_config, mock_console):
        """Test agent context generation."""
        runner = AgentRunner(test_config, mock_console)
        context = runner._get_agent_context()

        assert "schema" in context
        assert "project_name" in context
        assert context["project_name"] == test_config.project_name
        assert "repo_path" in context
        assert context["repo_path"] == str(test_config.repo_path)
        assert "language" in context
        assert context["language"] == test_config.language
        assert "neo4j_uri" in context
        assert "tools" in context
        assert isinstance(context["tools"], list)
        assert len(context["tools"]) > 0

    def test_context_includes_required_tools(self, test_config, mock_console):
        """Test that context includes all required tools."""
        runner = AgentRunner(test_config, mock_console)
        context = runner._get_agent_context()

        required_tools = [
            "neo4j_query",
            "read_file",
            "write_file",
            "run_shell",
            "run_tests",
            "run_linter",
        ]

        for tool in required_tools:
            assert tool in context["tools"]

    def test_verify_result(self, test_config, mock_console):
        """Test result verification."""
        runner = AgentRunner(test_config, mock_console)

        success, error = runner._verify_result(["log1", "log2"])

        # Stub always returns success
        assert success is True
        assert error is None

    # Note: These tests are disabled as they test the old stub implementation
    # The agent now uses la-factoria API which requires a running server
    # TODO: Add integration tests with mock la-factoria server

    # def test_run_stub_returns_success(self, test_config, mock_console):
    #     """Test that stub implementation returns success."""
    #     runner = AgentRunner(test_config, mock_console)
    #     result = runner._run_agent_stub()
    #
    #     assert result.success is True
    #     assert result.task == test_config.task
    #     assert result.iterations > 0
    #     assert isinstance(result.logs, list)
    #     assert len(result.logs) > 0

    # def test_run_handles_exceptions(self, test_config, mock_console):
    #     """Test that run() handles exceptions gracefully."""
    #     runner = AgentRunner(test_config, mock_console)
    #
    #     # Mock _run_agent_stub to raise an exception
    #     def raise_error():
    #         raise ValueError("Test error")
    #
    #     runner._run_agent_stub = raise_error
    #     result = runner.run()
    #
    #     assert result.success is False
    #     assert "Test error" in result.error
    #     assert result.task == test_config.task
