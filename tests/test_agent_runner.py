"""
Tests for agent_runner module
"""
import pytest
from pathlib import Path
from unittest.mock import Mock
from rich.console import Console

from xcode.config import XCodeConfig
from xcode.agent_runner import AgentRunner
from xcode.result import XCodeResult


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
        assert runner.max_iterations == 10
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

