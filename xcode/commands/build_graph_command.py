"""
Build graph command.
"""
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from xcode.services import GraphService


@dataclass
class BuildGraphCommand:
    """
    Command to build a knowledge graph.
    
    Wraps graph service with command pattern.
    """
    
    project_name: str
    repo_path: Path
    language: str
    graph_service: GraphService
    console: Console
    enable_descriptions: bool = False
    verbose: bool = False
    
    def execute(self) -> None:
        """Execute the graph building command."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"Building knowledge graph for {self.project_name}...",
                total=None,
            )
            
            self.graph_service.build_graph(
                project_name=self.project_name,
                repo_path=self.repo_path,
                language=self.language,
                enable_descriptions=self.enable_descriptions,
            )
            
            progress.update(task, completed=True)
        
        if self.verbose:
            self.console.print(
                f"[green]✓[/green] Knowledge graph built for project: {self.project_name}"
            )
