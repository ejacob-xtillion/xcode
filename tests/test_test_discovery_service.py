"""
Tests for TestDiscoveryService
"""

from unittest.mock import Mock, patch

import pytest

from xcode.models.test_info import CallableInfo, TestInfo
from xcode.services.test_discovery_service import TestDiscoveryService


@pytest.fixture
def mock_graph_repo():
    """Create a mock graph repository."""
    return Mock()


@pytest.fixture
def mock_console():
    """Create a mock console."""
    return Mock()


@pytest.fixture
def test_discovery_service(mock_graph_repo, mock_console):
    """Create a TestDiscoveryService instance."""
    return TestDiscoveryService(mock_graph_repo, mock_console)


class TestFindTestsForFiles:
    """Tests for find_tests_for_files method."""

    def test_empty_file_list(self, test_discovery_service):
        """Test with empty file list."""
        result = test_discovery_service.find_tests_for_files([], "test_project")
        assert result == {}

    def test_finds_tests_for_callables(self, test_discovery_service, mock_graph_repo):
        """Test finding tests that cover callables in modified files."""
        mock_graph_repo.query.return_value = [
            {
                "name": "test_calculate_total",
                "path": "tests/test_calculator.py",
                "line_number": 10,
                "tests_callable": "calculate_total",
            }
        ]

        result = test_discovery_service.find_tests_for_files(
            ["src/calculator.py"], "test_project"
        )

        assert "src/calculator.py" in result
        assert len(result["src/calculator.py"]) == 1
        test_info = result["src/calculator.py"][0]
        assert test_info.name == "test_calculate_total"
        assert test_info.path == "tests/test_calculator.py"
        assert test_info.tests_callable == "calculate_total"

    def test_handles_query_errors_gracefully(
        self, test_discovery_service, mock_graph_repo, mock_console
    ):
        """Test graceful handling of Neo4j query errors."""
        mock_graph_repo.query.side_effect = Exception("Neo4j connection error")

        result = test_discovery_service.find_tests_for_files(
            ["src/calculator.py"], "test_project"
        )

        assert "src/calculator.py" in result
        assert result["src/calculator.py"] == []
        mock_console.print.assert_called()


class TestFindUntestedCallables:
    """Tests for find_untested_callables method."""

    def test_empty_file_list(self, test_discovery_service):
        """Test with empty file list."""
        result = test_discovery_service.find_untested_callables([], "test_project")
        assert result == []

    def test_finds_untested_callables(self, test_discovery_service, mock_graph_repo):
        """Test finding callables without test coverage."""
        mock_graph_repo.query.return_value = [
            {
                "name": "helper_function",
                "signature": "helper_function(x: int) -> str",
                "file_path": "src/utils.py",
                "line_number": 42,
            },
            {
                "name": "another_helper",
                "signature": "another_helper()",
                "file_path": "src/utils.py",
                "line_number": 55,
            },
        ]

        result = test_discovery_service.find_untested_callables(
            ["src/utils.py"], "test_project"
        )

        assert len(result) == 2
        assert result[0].name == "helper_function"
        assert result[0].signature == "helper_function(x: int) -> str"
        assert result[0].is_tested is False

    def test_handles_query_errors(
        self, test_discovery_service, mock_graph_repo, mock_console
    ):
        """Test error handling for Neo4j query failures."""
        mock_graph_repo.query.side_effect = Exception("Query failed")

        result = test_discovery_service.find_untested_callables(
            ["src/utils.py"], "test_project"
        )

        assert result == []
        mock_console.print.assert_called()


class TestGetTestSummary:
    """Tests for get_test_summary method."""

    def test_summary_with_mixed_coverage(self, test_discovery_service, mock_graph_repo):
        """Test summary with some files having tests and some not."""
        # Mock find_tests_for_files results
        with patch.object(
            test_discovery_service, "find_tests_for_files"
        ) as mock_find_tests:
            mock_find_tests.return_value = {
                "src/calculator.py": [
                    TestInfo("test_add", "tests/test_calculator.py", 10, "add")
                ],
                "src/utils.py": [],
            }

            # Mock find_untested_callables results
            with patch.object(
                test_discovery_service, "find_untested_callables"
            ) as mock_untested:
                mock_untested.return_value = [
                    CallableInfo("helper", "helper()", "src/utils.py", 20, False)
                ]

                result = test_discovery_service.get_test_summary(
                    ["src/calculator.py", "src/utils.py"], "test_project"
                )

                assert result["total_modified_files"] == 2
                assert result["files_with_tests"] == 1
                assert result["files_without_tests"] == 1
                assert result["total_related_tests"] == 1
                assert result["untested_callables"] == 1


class TestShouldGenerateTests:
    """Tests for should_generate_tests method."""

    def test_skip_test_files(self, test_discovery_service):
        """Test that test files are skipped."""
        should_gen, reason = test_discovery_service.should_generate_tests(
            "tests/test_calculator.py", "test_project"
        )
        assert should_gen is False
        assert "test file" in reason.lower()

    def test_skip_init_files(self, test_discovery_service):
        """Test that __init__.py files are skipped."""
        should_gen, reason = test_discovery_service.should_generate_tests(
            "src/__init__.py", "test_project"
        )
        assert should_gen is False

    def test_skip_files_without_callables(
        self, test_discovery_service, mock_graph_repo
    ):
        """Test skipping files with no callables."""
        mock_graph_repo.query.return_value = [{"callable_count": 0}]

        should_gen, reason = test_discovery_service.should_generate_tests(
            "src/constants.py", "test_project"
        )
        assert should_gen is False
        assert "no callables" in reason.lower()

    def test_generate_for_files_with_callables(
        self, test_discovery_service, mock_graph_repo
    ):
        """Test that files with callables should generate tests."""
        mock_graph_repo.query.return_value = [{"callable_count": 5}]

        should_gen, reason = test_discovery_service.should_generate_tests(
            "src/calculator.py", "test_project"
        )
        assert should_gen is True
        assert reason is None
