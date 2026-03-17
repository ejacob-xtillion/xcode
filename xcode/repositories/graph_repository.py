"""
Neo4j graph repository implementation.
"""

import subprocess
from pathlib import Path

from rich.console import Console

from xcode.domain.interfaces import GraphRepository


class Neo4jGraphRepository(GraphRepository):
    """Neo4j implementation of GraphRepository."""

    def __init__(
        self,
        console: Console,
        verbose: bool = False,
        enable_descriptions: bool = False,
    ):
        self.console = console
        self.verbose = verbose
        self.enable_descriptions = enable_descriptions

    def build_graph(self, project_name: str, repo_path: Path, language: str) -> None:
        """Build knowledge graph using xgraph."""
        try:
            self._build_via_library(project_name, repo_path, language)
        except ImportError:
            if self.verbose:
                self.console.print(
                    "[yellow]xgraph not installed as library, using CLI fallback[/yellow]"
                )
            self._build_via_subprocess(project_name, repo_path, language)

    def _build_via_library(
        self, project_name: str, repo_path: Path, language: str
    ) -> None:
        """Build graph using xgraph as a Python library."""
        try:
            from xgraph.knowledge_graph.build_graph import build_knowledge_graph

            if self.verbose:
                self.console.print("[dim]Building graph via xgraph library[/dim]")

            build_knowledge_graph(
                project_path=str(repo_path),
                language=language,
                project_name=project_name,
                enable_descriptions=self.enable_descriptions,
                keep_existing_graph=True,
                graph_db_type="neo4j",
            )

        except Exception as e:
            raise RuntimeError(f"Failed to build knowledge graph via library: {e}")

    def _build_via_subprocess(
        self, project_name: str, repo_path: Path, language: str
    ) -> None:
        """Build graph using xgraph CLI as subprocess."""
        try:
            cmd = [
                "build-graph",
                "--project-path",
                str(repo_path),
                "--language",
                language,
                "--project-name",
                project_name,
                "--keep-existing-graph",
            ]

            if self.enable_descriptions:
                cmd.append("--enable-descriptions")

            if self.verbose:
                self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if self.verbose and result.stdout:
                self.console.print(result.stdout)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to build knowledge graph via CLI: {e.stderr or e.stdout}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "xgraph CLI not found. Please install xgraph: pip install xgraph"
            )

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Execute a Cypher query and return results."""
        raise NotImplementedError("Direct Neo4j queries not yet implemented")

    def close(self) -> None:
        """Close connection to graph database."""
        pass
