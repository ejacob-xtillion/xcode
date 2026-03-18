"""
Tests for the startup orchestrator.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from xcode.startup import StartupOrchestrator, StartupState


class TestStartupState:
    """Tests for StartupState dataclass."""

    def test_initial_state(self):
        """Test that StartupState initializes with correct defaults."""
        state = StartupState()
        assert state.graph_building is False
        assert state.graph_complete is False
        assert state.graph_error is None


class TestStartupOrchestrator:
    """Tests for StartupOrchestrator."""

    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Console(file=MagicMock())

    @pytest.fixture
    def orchestrator(self, console, tmp_path):
        """Create a StartupOrchestrator instance."""
        return StartupOrchestrator(
            console=console,
            project_name="test_project",
            repo_path=tmp_path,
            language="python",
            verbose=False,
            enable_descriptions=False,
        )

    def test_initialization(self, orchestrator, tmp_path):
        """Test that orchestrator initializes correctly."""
        assert orchestrator.project_name == "test_project"
        assert orchestrator.repo_path == tmp_path
        assert orchestrator.language == "python"
        assert orchestrator.verbose is False
        assert orchestrator.enable_descriptions is False
        assert isinstance(orchestrator.state, StartupState)

    def test_show_intro_message(self, orchestrator, console):
        """Test intro message display."""
        orchestrator._show_intro_message()
        # Should not raise any exceptions

    def test_start_without_graph_build(self, orchestrator):
        """Test starting without building graph."""
        orchestrator.start_with_welcome(build_graph=False)
        
        # State should remain unchanged
        assert orchestrator.state.graph_building is False
        assert orchestrator.state.graph_complete is False

    @patch("xcode.startup.subprocess.run")
    @patch("xcode.startup.sys")
    def test_build_graph_background_success(self, mock_sys, mock_subprocess, orchestrator):
        """Test successful background graph building."""
        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.stdout = "processed=10 nodes=100 rels=200"
        mock_subprocess.return_value = mock_result
        
        # Mock xgraph import to fail, forcing CLI path
        with patch.dict('sys.modules', {'xgraph.knowledge_graph.build_graph': None}):
            orchestrator._build_graph_background()
        
        # State should indicate completion
        assert orchestrator.state.graph_complete is True
        assert orchestrator.state.graph_building is False
        assert orchestrator.state.graph_error is None

    @patch("xcode.startup.subprocess.run")
    def test_build_graph_background_error(self, mock_subprocess, orchestrator):
        """Test error handling during background graph building."""
        # Mock subprocess to raise error
        mock_subprocess.side_effect = Exception("Test error")
        
        # Mock xgraph import to fail, forcing CLI path
        with patch.dict('sys.modules', {'xgraph.knowledge_graph.build_graph': None}):
            orchestrator._build_graph_background()
        
        # State should indicate error
        assert orchestrator.state.graph_complete is False
        assert orchestrator.state.graph_building is False
        assert orchestrator.state.graph_error == "Test error"

