"""
Test generation service - generates tests for untested code using the agent.
"""

from rich.console import Console

from xcode.domain.models import AgentResult, Task, XCodeConfig
from xcode.models.test_info import CallableInfo
from xcode.services.agent_service import AgentService


class TestGenerationService:
    """Generates tests for untested code using the AI agent."""

    def __init__(self, agent_service: AgentService, console: Console):
        self.agent_service = agent_service
        self.console = console

    async def generate_tests_for_callables(
        self,
        callables: list[CallableInfo],
        original_task: Task,
        config: XCodeConfig,
        schema: str,
    ) -> AgentResult:
        """
        Generate tests for untested callables.

        Creates a focused agent task to write comprehensive tests for
        the provided callables.

        Args:
            callables: List of untested callables to generate tests for
            original_task: The original task that modified the code
            config: Configuration for agent execution
            schema: Neo4j schema documentation

        Returns:
            AgentResult from test generation task
        """
        if not callables:
            return AgentResult(
                success=True,
                task="No tests to generate",
                iterations=0,
                logs=["No untested callables found"],
            )

        # Group callables by file
        callables_by_file = {}
        for callable_info in callables:
            file_path = callable_info.file_path
            if file_path not in callables_by_file:
                callables_by_file[file_path] = []
            callables_by_file[file_path].append(callable_info)

        # Build test generation prompt
        task_description = self._build_test_generation_prompt(callables_by_file)

        # Create test generation task
        test_task = Task(
            description=task_description,
            repo_path=original_task.repo_path,
            project_name=original_task.project_name,
            language=original_task.language,
        )

        self.console.print(
            f"[cyan]Generating tests for {len(callables)} untested callables...[/cyan]"
        )

        # Execute test generation via agent
        result = await self.agent_service.execute_task(
            task=test_task,
            config=config,
            schema=schema,
            conversation_context="",
        )

        if result.success:
            self.console.print("[green]✓[/green] Tests generated successfully")
        else:
            self.console.print(
                f"[yellow]Warning: Test generation failed: {result.error}[/yellow]"
            )

        return result

    def _build_test_generation_prompt(
        self, callables_by_file: dict[str, list[CallableInfo]]
    ) -> str:
        """
        Build a detailed prompt for test generation.

        Args:
            callables_by_file: Dict mapping file paths to untested callables

        Returns:
            Formatted task description for the agent
        """
        prompt_parts = [
            "Generate comprehensive pytest tests for the following untested functions/methods:",
            "",
        ]

        for file_path, callables in callables_by_file.items():
            prompt_parts.append(f"**File: {file_path}**")
            for callable_info in callables:
                prompt_parts.append(
                    f"  - `{callable_info.name}` (line {callable_info.line_number})"
                )
                if callable_info.signature != callable_info.name:
                    prompt_parts.append(f"    Signature: `{callable_info.signature}`")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "**Requirements:**",
                "1. Read the source code to understand what each function does",
                "2. Create test file(s) in the `tests/` directory following pytest conventions",
                "3. Test file naming: `tests/test_{module_name}.py`",
                "4. Test function naming: `test_{function_name}_{scenario}`",
                "5. Cover these scenarios for each function:",
                "   - Happy path (normal/expected usage)",
                "   - Edge cases (empty inputs, boundary values, etc.)",
                "   - Error conditions (invalid inputs, exceptions)",
                "6. Use pytest fixtures for setup/teardown if needed",
                "7. Mock external dependencies (API calls, database, file I/O)",
                "8. Add docstrings to test functions explaining what they test",
                "",
                "**Example test structure:**",
                "```python",
                'def test_function_name_happy_path():',
                '    """Test function_name with valid inputs."""',
                "    result = function_name(valid_input)",
                "    assert result == expected_output",
                "",
                'def test_function_name_edge_case():',
                '    """Test function_name with edge case inputs."""',
                "    result = function_name(edge_case_input)",
                "    assert result == expected_edge_output",
                "",
                'def test_function_name_error_handling():',
                '    """Test function_name raises appropriate errors."""',
                "    with pytest.raises(ExpectedException):",
                "        function_name(invalid_input)",
                "```",
                "",
                "After writing tests, run them to ensure they pass:",
                "`run_shell_command('python -m pytest -v tests/', working_directory='{repo_path}')`",
            ]
        )

        return "\n".join(prompt_parts)

    def should_generate_tests(
        self, file_path: str, project_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if tests should be generated for a file.

        Args:
            file_path: Relative path to the file
            project_name: Project name in Neo4j

        Returns:
            Tuple of (should_generate, reason)
        """
        # Skip test files themselves
        if "test" in file_path.lower():
            return False, "File is a test file"

        # Skip common non-code files
        skip_patterns = [
            "__init__.py",
            "setup.py",
            "conftest.py",
            ".py.bak",
            "migrations/",
        ]
        if any(pattern in file_path for pattern in skip_patterns):
            return False, f"File matches skip pattern"

        # Check if file has any callables
        try:
            cypher = """
            MATCH (p:Project {name: $project_name})
            MATCH (p)<-[:INCLUDED_IN*]-(f:File {path: $file_path})
            MATCH (f)<-[:DECLARED_IN]-(c:Callable)
            WHERE NOT (c:Test)
            RETURN count(c) as callable_count
            """
            results = self.graph_repo.query(
                cypher, {"project_name": project_name, "file_path": file_path}
            )

            if not results or results[0]["callable_count"] == 0:
                return False, "No callables found in file"

        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Failed to check callables for {file_path}: {e}[/yellow]"
            )
            return False, f"Query error: {e}"

        return True, None
