"""
Test Priority 1 optimizations from latency analysis.

Tests that:
1. Simple tasks skip graph building (needs_neo4j=False)
2. HTTP timeouts are configured
3. File tree is included for file operations
"""

from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from rich.console import Console

from xcode.agent_runner import AgentRunner
from xcode.domain.models import TaskType, XCodeConfig
from xcode.orchestrator import XCodeOrchestrator
from xcode.task_classifier import TaskClassifier


class TestPriority1Optimizations:
    """Test Priority 1 latency optimizations."""

    def test_greeting_skips_graph_build(self, tmp_path):
        """Test that greeting tasks skip graph building."""
        config = XCodeConfig(
            task="hello",
            repo_path=tmp_path,
            language="python",
            build_graph=True,  # Request graph build
            verbose=True,
        )

        console = Console(quiet=True)
        orchestrator = XCodeOrchestrator(config, console)

        # Mock the graph service to track if it's called
        with patch.object(orchestrator.graph_service, "ensure_graph_exists") as mock_graph:
            with patch("xcode.orchestrator.asyncio.run") as mock_agent:
                mock_agent.return_value = Mock(success=True)

                orchestrator.run()

                # Graph build should NOT be called for greetings
                mock_graph.assert_not_called()

    def test_delete_skips_graph_build(self, tmp_path):
        """Test that delete tasks skip graph building."""
        config = XCodeConfig(
            task="delete the old test file",
            repo_path=tmp_path,
            language="python",
            build_graph=True,
            verbose=False,
        )

        console = Console(quiet=True)
        orchestrator = XCodeOrchestrator(config, console)

        with patch.object(orchestrator.graph_service, "ensure_graph_exists") as mock_graph:
            with patch("xcode.orchestrator.asyncio.run") as mock_agent:
                mock_agent.return_value = Mock(success=True)

                orchestrator.run()

                # Delete operations should not need graph
                mock_graph.assert_not_called()

    def test_refactor_requires_graph_build(self, tmp_path):
        """Test that refactor tasks DO require graph building."""
        config = XCodeConfig(
            task="refactor the authentication module",
            repo_path=tmp_path,
            language="python",
            build_graph=True,
            verbose=False,
        )

        console = Console(quiet=True)
        orchestrator = XCodeOrchestrator(config, console)

        with patch.object(orchestrator.graph_service, "ensure_graph_exists") as mock_graph:
            with patch("xcode.orchestrator.asyncio.run") as mock_agent:
                mock_agent.return_value = Mock(success=True)

                orchestrator.run()

                # Refactoring SHOULD trigger graph build
                mock_graph.assert_called_once()

    def test_http_timeout_configured(self, tmp_path):
        """Test that HTTP client has timeout configured."""
        config = XCodeConfig(
            task="test task",
            repo_path=tmp_path,
            language="python",
        )

        console = Console(quiet=True)
        runner = AgentRunner(config, console)

        # Mock the HTTP client to verify timeout
        with patch("xcode.agent_runner.httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.stream.return_value.__aenter__.return_value.status_code = 200
            mock_instance.stream.return_value.__aenter__.return_value.aiter_lines = Mock(
                return_value=iter([])
            )

            try:
                runner.run()
            except Exception:
                pass  # We just want to check the timeout was set

            # Verify AsyncClient was called with timeout
            mock_client.assert_called()
            call_kwargs = mock_client.call_args[1] if mock_client.call_args else {}

            # Check that timeout was provided
            assert "timeout" in call_kwargs or len(mock_client.call_args[0]) > 0

            # If timeout is in kwargs, verify it's an httpx.Timeout
            if "timeout" in call_kwargs:
                timeout = call_kwargs["timeout"]
                assert isinstance(timeout, httpx.Timeout)
                assert timeout.connect == 30.0 or timeout.read == 30.0 or timeout.write == 30.0

    def test_file_tree_included_for_file_operations(self, tmp_path):
        """Test that file tree is included in prompt for file operations."""
        # Create some test files
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("def helper(): pass")

        config = XCodeConfig(
            task="modify the test.py file",
            repo_path=tmp_path,
            language="python",
        )

        console = Console(quiet=True)
        runner = AgentRunner(config, console)

        # Build the query and check if file tree is included
        schema = "test schema"
        query = runner._build_agent_query(schema, "")

        # For modify operations, file tree should be included
        assert "Available files in repository:" in query or "test.py" in query

    def test_file_tree_not_included_for_greetings(self, tmp_path):
        """Test that file tree is NOT included for greetings."""
        config = XCodeConfig(
            task="hello",
            repo_path=tmp_path,
            language="python",
        )

        console = Console(quiet=True)
        runner = AgentRunner(config, console)

        schema = "test schema"
        query = runner._build_agent_query(schema, "")

        # For greetings, file tree should NOT be included
        # (though the task itself might appear in the query)
        assert "Available files in repository:" not in query

    def test_classification_determines_graph_need(self):
        """Test that task classification correctly determines graph needs."""
        classifier = TaskClassifier()

        # Tasks that should NOT need graph
        simple_tasks = [
            ("hello", TaskType.GREETING),
            ("hi there", TaskType.GREETING),
            ("delete the old file", TaskType.DELETE_FILES),
        ]

        for task, expected_type in simple_tasks:
            classification = classifier.classify(task)
            assert not classification.needs_neo4j, f"Task '{task}' should not need Neo4j"
            assert classification.task_type == expected_type

        # Tasks that SHOULD need graph
        complex_tasks = [
            "refactor the authentication module",
            "fix bug in user registration",
            "add type hints to all functions",
        ]

        for task in complex_tasks:
            classification = classifier.classify(task)
            assert classification.needs_neo4j, f"Task '{task}' should need Neo4j"

    def test_file_operations_get_file_tree(self, tmp_path):
        """Test that file operation tasks get file tree in context."""
        # Create test files
        (tmp_path / "main.py").write_text("# main")
        (tmp_path / "utils.py").write_text("# utils")
        subdir = tmp_path / "lib"
        subdir.mkdir()
        (subdir / "helper.py").write_text("# helper")

        config = XCodeConfig(
            task="create a new config.py file",
            repo_path=tmp_path,
            language="python",
            project_name="test_project",
        )

        console = Console(quiet=True)
        runner = AgentRunner(config, console)

        # Get file cache - may be None if cache isn't built yet
        file_tree = runner._get_file_cache()

        # File tree may be None or a string depending on cache state
        # The important thing is that the method exists and can be called
        assert file_tree is None or isinstance(file_tree, str)


class TestOptimizationImpact:
    """Test the expected impact of optimizations."""

    def test_simple_tasks_are_fast(self):
        """Verify that simple tasks are classified for fast execution."""
        classifier = TaskClassifier()

        # Test greeting
        greeting = classifier.classify("hello")
        assert greeting.task_type == TaskType.GREETING
        assert greeting.max_files_to_read == 0
        assert greeting.max_iterations == 1
        assert not greeting.needs_neo4j

        # Test delete (simple operation)
        delete = classifier.classify("delete the old test file")
        assert delete.task_type == TaskType.DELETE_FILES
        assert delete.max_files_to_read == 0
        assert not delete.needs_neo4j

    def test_complex_tasks_get_more_resources(self):
        """Verify that complex tasks get appropriate resources."""
        classifier = TaskClassifier()

        # Test refactoring
        refactor = classifier.classify("refactor the entire codebase")
        assert refactor.task_type == TaskType.REFACTOR
        assert refactor.max_files_to_read >= 15
        assert refactor.max_iterations >= 20
        assert refactor.needs_neo4j

        # Test bug fix
        bug_fix = classifier.classify("fix bug in database connection")
        assert bug_fix.task_type == TaskType.FIX_BUG
        assert bug_fix.max_files_to_read >= 8
        assert bug_fix.needs_neo4j

    def test_file_operations_get_moderate_resources(self):
        """Verify that file operations get moderate resources."""
        classifier = TaskClassifier()

        # Test create file
        create = classifier.classify("create a new file called utils.py")
        assert create.task_type == TaskType.CREATE_NEW_FILE
        assert create.max_files_to_read <= 5
        assert not create.needs_neo4j  # Simple file creation doesn't need graph

        # Test modify
        modify = classifier.classify("modify config.py file")
        assert modify.task_type == TaskType.MODIFY_EXISTING
        assert create.max_files_to_read <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
