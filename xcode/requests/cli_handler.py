"""
CLI request handler.
"""
from pathlib import Path

from rich.console import Console

from xcode.formatting import ErrorFormatter, TaskFormatter
from xcode.models import AgentResult, TaskValidationError, XCodeConfig
from xcode.orchestrator import XCodeOrchestrator


class CLIRequestHandler:
    """
    Handler for CLI requests.

    Uses XCodeOrchestrator to execute tasks.
    """

    def __init__(self, container):
        """
        Initialize the CLI request handler.

        Args:
            container: Dependency injection container (unused, kept for compatibility)
        """
        self.container = container
        self.console = Console()
        self.task_formatter = TaskFormatter(self.console)
        self.error_formatter = ErrorFormatter(self.console)

    def handle(
        self,
        task_description: str,
        repo_path: Path,
        language: str = "python",
        project_name: str = None,
        build_graph: bool = True,
        verbose: bool = False,
    ) -> AgentResult:
        """
        Handle a CLI request to execute a task.

        Args:
            task_description: Description of the task
            repo_path: Path to the repository
            language: Programming language
            project_name: Optional project name
            build_graph: Whether to build the knowledge graph
            verbose: Whether to show verbose output

        Returns:
            AgentResult with execution status
        """
        try:
            if not project_name:
                project_name = repo_path.name

            # Create config for orchestrator
            config = XCodeConfig(
                task=task_description,
                repo_path=repo_path,
                language=language,
                project_name=project_name,
                build_graph=build_graph,
                verbose=verbose,
            )

            # Use orchestrator to execute task
            orchestrator = XCodeOrchestrator(config=config, console=self.console)
            result = orchestrator.run()

            # Display result
            self._display_result(result)

            return result

        except TaskValidationError as e:
            self.error_formatter.print_error(
                error=str(e),
                context="Invalid task description",
                suggestions=["Example: 'Add a function to calculate fibonacci numbers'"],
            )
            return AgentResult(
                success=False,
                task=task_description,
                iterations=0,
                error=str(e),
            )
        except Exception as e:
            self.error_formatter.print_error(
                error=e,
                verbose=verbose,
            )
            return AgentResult(
                success=False,
                task=task_description,
                iterations=0,
                error=str(e),
            )

    def _display_result(self, result: AgentResult) -> None:
        """Display the execution result."""
        self.task_formatter.print_task_complete(
            success=result.success,
            duration=None,  # TODO: Add duration tracking
            iterations=result.iterations,
            modified_files=result.modified_files if hasattr(result, 'modified_files') else None,
        )

        if not result.success and result.error:
            self.console.print(f"[red]Error: {result.error}[/red]")
