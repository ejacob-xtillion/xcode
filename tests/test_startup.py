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
        assert state.files_processed == 0
        assert state.total_files == 0


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

    def test_show_simple_welcome(self, orchestrator, console):
        """Test simple welcome screen without graph building."""
        orchestrator._show_simple_welcome()
        # Should not raise any exceptions

    def test_estimate_file_count_empty_directory(self, orchestrator):
        """Test file count estimation on empty directory."""
        count = orchestrator._estimate_file_count()
        assert count >= 1  # Should return at least 1

    def test_estimate_file_count_with_files(self, orchestrator, tmp_path):
        """Test file count estimation with Python files."""
        # Create some test files
        (tmp_path / "test1.py").touch()
        (tmp_path / "test2.py").touch()
        (tmp_path / "test3.py").touch()
        
        count = orchestrator._estimate_file_count()
        assert count == 3

    def test_estimate_file_count_excludes_hidden(self, orchestrator, tmp_path):
        """Test that hidden directories are excluded from count."""
        # Create files in hidden directory
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "test.py").touch()
        
        # Create normal file
        (tmp_path / "test.py").touch()
        
        count = orchestrator._estimate_file_count()
        assert count == 1  # Should only count the non-hidden file

    def test_estimate_file_count_excludes_common_dirs(self, orchestrator, tmp_path):
        """Test that common excluded directories are ignored."""
        excluded_dirs = ["__pycache__", "node_modules", "venv", ".venv"]
        
        for dir_name in excluded_dirs:
            dir_path = tmp_path / dir_name
            dir_path.mkdir()
            (dir_path / "test.py").touch()
        
        # Create normal file
        (tmp_path / "test.py").touch()
        
        count = orchestrator._estimate_file_count()
        assert count == 1  # Should only count the non-excluded file

    @patch("xcode.startup.Neo4jGraphRepository")
    def test_start_without_graph_build(self, mock_repo, orchestrator):
        """Test starting without building graph."""
        orchestrator.start_with_welcome(build_graph=False)
        
        # Should not create graph repository
        mock_repo.assert_not_called()
        
        # State should remain unchanged
        assert orchestrator.state.graph_building is False
        assert orchestrator.state.graph_complete is False

    @patch("xcode.startup.Neo4jGraphRepository")
    def test_build_graph_background_success(self, mock_repo, orchestrator):
        """Test successful background graph building."""
        mock_instance = MagicMock()
        mock_repo.return_value = mock_instance
        
        orchestrator._build_graph_background()
        
        # Should create repository and call build_graph
        mock_repo.assert_called_once()
        mock_instance.build_graph.assert_called_once_with(
            project_name="test_project",
            repo_path=orchestrator.repo_path,
            language="python",
        )
        
        # State should indicate completion
        assert orchestrator.state.graph_complete is True
        assert orchestrator.state.graph_building is False
        assert orchestrator.state.graph_error is None

    @patch("xcode.startup.Neo4jGraphRepository")
    def test_build_graph_background_error(self, mock_repo, orchestrator):
        """Test error handling during background graph building."""
        mock_instance = MagicMock()
        mock_instance.build_graph.side_effect = Exception("Test error")
        mock_repo.return_value = mock_instance
        
        orchestrator._build_graph_background()
        
        # State should indicate error
        assert orchestrator.state.graph_complete is False
        assert orchestrator.state.graph_building is False
        assert orchestrator.state.graph_error == "Test error"

    def test_csharp_file_estimation(self, console, tmp_path):
        """Test file count estimation for C# projects."""
        orchestrator = StartupOrchestrator(
            console=console,
            project_name="test_project",
            repo_path=tmp_path,
            language="csharp",
            verbose=False,
            enable_descriptions=False,
        )
        
        # Create Python and C# files
        (tmp_path / "test.py").touch()
        (tmp_path / "test.cs").touch()
        
        count = orchestrator._estimate_file_count()
        assert count == 2  # Should count both .py and .cs for csharp language
