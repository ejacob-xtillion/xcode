"""
Graph builder module - interfaces with xgraph to build knowledge graphs
"""

import subprocess

from rich.console import Console

from xcode.domain.models import XCodeConfig


class GraphBuilder:
    """Builds knowledge graphs using xgraph."""

    def __init__(self, config: XCodeConfig, console: Console):
        self.config = config
        self.console = console

    def build(self) -> None:
        """Build the knowledge graph for the repository."""
        try:
            # Try to import xgraph as a library first
            self._build_via_library()
        except ImportError:
            if self.config.verbose:
                self.console.print(
                    "[yellow]xgraph not installed as library, using CLI fallback[/yellow]"
                )
            # Fall back to subprocess
            self._build_via_subprocess()

    def _build_via_library(self) -> None:
        """Build graph using xgraph as a Python library."""
        try:
            from xgraph.knowledge_graph.build_graph import build_knowledge_graph

            if self.config.verbose:
                self.console.print("[dim]Building graph via xgraph library[/dim]")

            build_knowledge_graph(
                project_path=str(self.config.repo_path),
                language=self.config.language,
                project_name=self.config.project_name,
                enable_descriptions=self.config.xgraph_enable_descriptions,
                keep_existing_graph=True,  # Don't wipe other projects
                graph_db_type="neo4j",
            )

        except Exception as e:
            raise RuntimeError(f"Failed to build knowledge graph via library: {e}")

    def _build_via_subprocess(self) -> None:
        """Build graph using xgraph CLI as subprocess."""
        try:
            cmd = [
                "build-graph",
                "--project-path",
                str(self.config.repo_path),
                "--language",
                self.config.language,
                "--project-name",
                self.config.project_name,
                "--keep-existing-graph",
            ]

            if self.config.xgraph_enable_descriptions:
                cmd.append("--enable-descriptions")

            if self.config.verbose:
                self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if self.config.verbose and result.stdout:
                self.console.print(result.stdout)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build knowledge graph via CLI: {e.stderr or e.stdout}")
        except FileNotFoundError:
            raise RuntimeError("xgraph CLI not found. Please install xgraph: pip install xgraph")
