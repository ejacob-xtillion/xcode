"""
CLI request handler.
"""
from pathlib import Path

from rich.console import Console

from xcode.commands import ExecuteTaskCommand
from xcode.models import Task, TaskValidationError, AgentResult


class CLIRequestHandler:
    """
    Handler for CLI requests.
    
    Parses CLI arguments, creates commands, and executes them.
    """
    
    def __init__(self, container):
        """
        Initialize the CLI request handler.
        
        Args:
            container: Dependency injection container
        """
        self.container = container
        self.console = Console()
    
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
            # Create task model
            if not project_name:
                project_name = repo_path.name
            
            task = Task(
                description=task_description,
                repo_path=repo_path,
                project_name=project_name,
                language=language,
            )
            
            # Create and execute command
            command = ExecuteTaskCommand(
                task=task,
                agent_service=self.container.agent_service,
                graph_service=self.container.graph_service,
                console=self.console,
                build_graph=build_graph,
                verbose=verbose,
            )
            
            result = command.execute()
            
            # Display result
            self._display_result(result)
            
            return result
        
        except TaskValidationError as e:
            self.console.print(f"[yellow]⚠[/yellow] Invalid task: {str(e)}")
            self.console.print(
                "[dim]Example: 'Add a function to calculate fibonacci numbers'[/dim]"
            )
            return AgentResult(
                success=False,
                task=task_description,
                iterations=0,
                error=str(e),
            )
        except Exception as e:
            self.console.print(f"[red]✗[/red] Error: {str(e)}")
            return AgentResult(
                success=False,
                task=task_description,
                iterations=0,
                error=str(e),
            )
    
    def _display_result(self, result: AgentResult) -> None:
        """Display the execution result."""
        if result.success:
            self.console.print("\n[bold green]✓ Task completed successfully![/bold green]")
        else:
            self.console.print("\n[bold red]✗ Task failed[/bold red]")
            if result.error:
                self.console.print(f"[red]Error: {result.error}[/red]")
