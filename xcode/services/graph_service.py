"""
Graph service for knowledge graph operations.
"""

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from xcode.domain.interfaces import GraphRepository


class GraphService:
    """Service for knowledge graph operations."""

    def __init__(self, graph_repo: GraphRepository, console: Console):
        self.graph_repo = graph_repo
        self.console = console

    def ensure_graph_exists(
        self,
        project_name: str,
        repo_path: Path,
        language: str,
        verbose: bool = False,
    ) -> None:
        """
        Ensure knowledge graph exists for a repository.

        Args:
            project_name: Name of the project
            repo_path: Path to repository
            language: Programming language
            verbose: Whether to print verbose output
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"Building knowledge graph for {project_name}...",
                total=None,
            )

            self.graph_repo.build_graph(project_name, repo_path, language)

            progress.update(task, completed=True)

        if verbose:
            self.console.print(
                f"[green]✓[/green] Knowledge graph built for project: {project_name}"
            )

    def query_graph(self, cypher: str, params: dict | None = None) -> list[dict]:
        """
        Execute a Cypher query against the knowledge graph.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        return self.graph_repo.query(cypher, params)

    def close(self) -> None:
        """Close connection to graph database."""
        self.graph_repo.close()
