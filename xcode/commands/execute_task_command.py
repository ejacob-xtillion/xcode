"""
Execute task command.
"""
from dataclasses import dataclass

from rich.console import Console

from xcode.models import Task, AgentResult
from xcode.services import AgentService, GraphService


@dataclass
class ExecuteTaskCommand:
    """
    Command to execute a coding task.
    
    Coordinates agent service and graph service to fulfill user intent.
    """
    
    task: Task
    agent_service: AgentService
    graph_service: GraphService
    console: Console
    build_graph: bool = True
    verbose: bool = False
    
    def execute(self) -> AgentResult:
        """
        Execute the task.
        
        Returns:
            AgentResult with execution status
        """
        try:
            # Step 1: Classify task to determine if graph is needed
            classification = self.agent_service.classify_task(self.task)
            
            # Show classification if verbose
            if self.verbose:
                self.agent_service.show_classification(classification)
            
            # Step 2: Ensure knowledge graph exists (if needed)
            if self.build_graph and classification.needs_neo4j:
                self._ensure_knowledge_graph()
            elif not self.build_graph and self.verbose:
                self.console.print("[dim]Skipping graph build (--no-build-graph)[/dim]")
            elif not classification.needs_neo4j and self.verbose:
                self.console.print(
                    f"[dim]Skipping graph build for {classification.task_type.value} task "
                    f"(does not require Neo4j)[/dim]"
                )
            
            # Step 3: Execute agent with task
            result = self.agent_service.execute_agent(self.task, classification)
            
            return result
        
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                task=self.task.description,
                iterations=0,
            )
    
    def _ensure_knowledge_graph(self) -> None:
        """Ensure the knowledge graph exists for the repository."""
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"Building knowledge graph for {self.task.project_name}...",
                total=None,
            )
            
            self.graph_service.build_graph(
                project_name=self.task.project_name,
                repo_path=self.task.repo_path,
                language=self.task.language,
            )
            
            progress.update(task, completed=True)
        
        if self.verbose:
            self.console.print(
                f"[green]✓[/green] Knowledge graph built for project: {self.task.project_name}"
            )
