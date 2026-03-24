"""
Tests for TestGenerationService
"""

from unittest.mock import AsyncMock, Mock

import pytest

from xcode.models import AgentResult, Task, XCodeConfig
from xcode.models.test_info import CallableInfo
from xcode.services.test_generation_service import TestGenerationService


@pytest.fixture
def mock_agent_service():
    """Create a mock agent service."""
    service = Mock()
    service.execute_task = AsyncMock()
    return service


@pytest.fixture
def mock_console():
    """Create a mock console."""
    return Mock()


@pytest.fixture
def test_generation_service(mock_agent_service, mock_console):
    """Create a TestGenerationService instance."""
    return TestGenerationService(mock_agent_service, mock_console)


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        description="Add new feature",
        repo_path="/Users/test/repo",
        project_name="test_project",
        language="python",
    )


@pytest.fixture
def sample_config():
    """Create a sample config."""
    return XCodeConfig(
        task="test task",
        repo_path="/Users/test/repo",
        language="python",
        project_name="test_project",
    )


class TestGenerateTestsForCallables:
    """Tests for generate_tests_for_callables method."""

    @pytest.mark.asyncio
    async def test_empty_callables_list(
        self, test_generation_service, sample_task, sample_config
    ):
        """Test with empty callables list."""
        result = await test_generation_service.generate_tests_for_callables(
            [], sample_task, sample_config, "schema"
        )

        assert result.success is True
        assert result.task == "No tests to generate"

    @pytest.mark.asyncio
    async def test_generates_tests_for_callables(
        self, test_generation_service, mock_agent_service, sample_task, sample_config
    ):
        """Test successful test generation."""
        callables = [
            CallableInfo(
                name="calculate_total",
                signature="calculate_total(items: list) -> float",
                file_path="src/calculator.py",
                line_number=10,
            ),
            CallableInfo(
                name="format_output",
                signature="format_output(value: float) -> str",
                file_path="src/calculator.py",
                line_number=25,
            ),
        ]

        mock_agent_service.execute_task.return_value = AgentResult(
            success=True, task="Generate tests", iterations=1
        )

        result = await test_generation_service.generate_tests_for_callables(
            callables, sample_task, sample_config, "schema"
        )

        assert result.success is True
        mock_agent_service.execute_task.assert_called_once()

        # Verify the task description includes the callables
        call_args = mock_agent_service.execute_task.call_args
        task_arg = call_args.kwargs["task"]
        assert "calculate_total" in task_arg.description
        assert "format_output" in task_arg.description

    @pytest.mark.asyncio
    async def test_handles_generation_failure(
        self, test_generation_service, mock_agent_service, sample_task, sample_config
    ):
        """Test handling of test generation failure."""
        callables = [
            CallableInfo(
                name="helper",
                signature="helper()",
                file_path="src/utils.py",
                line_number=5,
            )
        ]

        mock_agent_service.execute_task.return_value = AgentResult(
            success=False, task="Generate tests", iterations=1, error="Agent failed"
        )

        result = await test_generation_service.generate_tests_for_callables(
            callables, sample_task, sample_config, "schema"
        )

        assert result.success is False
        assert result.error == "Agent failed"


class TestBuildTestGenerationPrompt:
    """Tests for _build_test_generation_prompt method."""

    def test_prompt_includes_all_callables(self, test_generation_service):
        """Test that prompt includes all callables grouped by file."""
        callables_by_file = {
            "src/calculator.py": [
                CallableInfo("add", "add(a, b)", "src/calculator.py", 10),
                CallableInfo("subtract", "subtract(a, b)", "src/calculator.py", 20),
            ],
            "src/utils.py": [
                CallableInfo("helper", "helper()", "src/utils.py", 5),
            ],
        }

        prompt = test_generation_service._build_test_generation_prompt(
            callables_by_file
        )

        assert "src/calculator.py" in prompt
        assert "add" in prompt
        assert "subtract" in prompt
        assert "src/utils.py" in prompt
        assert "helper" in prompt
        assert "pytest" in prompt
        assert "Happy path" in prompt
        assert "Edge cases" in prompt

    def test_prompt_includes_requirements(self, test_generation_service):
        """Test that prompt includes testing requirements."""
        callables_by_file = {
            "src/test.py": [CallableInfo("func", "func()", "src/test.py", 1)]
        }

        prompt = test_generation_service._build_test_generation_prompt(
            callables_by_file
        )

        assert "Requirements:" in prompt
        assert "tests/" in prompt
        assert "pytest" in prompt
        assert "Mock external dependencies" in prompt
