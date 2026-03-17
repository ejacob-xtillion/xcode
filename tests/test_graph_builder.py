"""
Tests for graph_builder module
"""

from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from xcode.config import XCodeConfig
from xcode.graph_builder import GraphBuilder


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
        build_graph=True,
        verbose=False,
    )


class TestGraphBuilder:
    """Tests for GraphBuilder."""

    def test_init(self, test_config, mock_console):
        """Test GraphBuilder initialization."""
        builder = GraphBuilder(test_config, mock_console)
        assert builder.config == test_config
        assert builder.console == mock_console

    @patch("xcode.graph_builder.GraphBuilder._build_via_library")
    def test_build_via_library_success(self, mock_build_method, test_config, mock_console):
        """Test successful graph building via library."""
        builder = GraphBuilder(test_config, mock_console)
        builder.build()

        mock_build_method.assert_called_once()

    @patch("xcode.graph_builder.subprocess.run")
    def test_build_via_subprocess_success(self, mock_run, test_config, mock_console):
        """Test successful graph building via subprocess."""
        mock_run.return_value = Mock(stdout="Success", stderr="", returncode=0)

        builder = GraphBuilder(test_config, mock_console)
        builder._build_via_subprocess()

        # Verify subprocess was called with correct arguments
        call_args = mock_run.call_args[0][0]
        assert "build-graph" in call_args
        assert "--project-path" in call_args
        assert str(test_config.repo_path) in call_args
        assert "--language" in call_args
        assert test_config.language in call_args

    @patch("xcode.graph_builder.subprocess.run")
    def test_build_via_subprocess_failure(self, mock_run, test_config, mock_console):
        """Test subprocess failure handling."""
        mock_run.side_effect = FileNotFoundError()

        builder = GraphBuilder(test_config, mock_console)

        with pytest.raises(RuntimeError, match="xgraph CLI not found"):
            builder._build_via_subprocess()

    @patch("xcode.graph_builder.GraphBuilder._build_via_library")
    def test_build_tries_library_first(self, mock_lib_build, test_config, mock_console):
        """Test that build() tries library first."""
        builder = GraphBuilder(test_config, mock_console)
        builder.build()

        mock_lib_build.assert_called_once()

    @patch("xcode.graph_builder.GraphBuilder._build_via_library")
    @patch("xcode.graph_builder.GraphBuilder._build_via_subprocess")
    def test_build_falls_back_to_subprocess(
        self, mock_subprocess_build, mock_lib_build, test_config, mock_console
    ):
        """Test fallback to subprocess when library import fails."""
        mock_lib_build.side_effect = ImportError("xgraph not installed")

        builder = GraphBuilder(test_config, mock_console)
        builder.build()

        mock_lib_build.assert_called_once()
        mock_subprocess_build.assert_called_once()
