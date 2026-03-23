"""
Graph repository for knowledge graph building.
"""
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from xcode.domain.interfaces import GraphRepository
from xcode.llm_compat import xgraph_openai_environ


class XGraphRepository(GraphRepository):
    """
    xgraph implementation of graph repository.
    
    Builds knowledge graphs using the xgraph library.
    """
    
    def __init__(
        self,
        console: Console,
        verbose: bool = False,
        enable_descriptions: bool = False,
        openai_base_url: Optional[str] = None,
    ):
        self.console = console
        self.verbose = verbose
        self.enable_descriptions = enable_descriptions
        self._openai_base_url = openai_base_url
        self._driver = None
    
    def build_graph(self, project_name: str, repo_path: Path, language: str) -> None:
        """
        Build the knowledge graph using xgraph.
        
        Args:
            project_name: Name of the project
            repo_path: Path to the repository
            language: Programming language
        """
        try:
            self._build_via_library(repo_path, language, project_name, self.enable_descriptions)
        except ImportError:
            if self.verbose:
                self.console.print(
                    "[yellow]xgraph not installed as library, using CLI fallback[/yellow]"
                )
            self._build_via_subprocess(repo_path, language, project_name, self.enable_descriptions)

    def _build_via_library(
        self,
        project_path: Path,
        language: str,
        project_name: str,
        enable_descriptions: bool,
    ) -> None:
        """Build graph using xgraph as a Python library."""
        try:
            from xgraph.knowledge_graph.build_graph import build_knowledge_graph

            if self.verbose:
                self.console.print("[dim]Building graph via xgraph library[/dim]")

            with xgraph_openai_environ(self._openai_base_url):
                build_knowledge_graph(
                    project_path=str(project_path),
                    language=language,
                    project_name=project_name,
                    enable_descriptions=enable_descriptions,
                    keep_existing_graph=True,  # Don't wipe other projects
                    graph_db_type="neo4j",
                )

        except Exception as e:
            raise RuntimeError(f"Failed to build knowledge graph via library: {e}")
    
    def _build_via_subprocess(
        self,
        project_path: Path,
        language: str,
        project_name: str,
        enable_descriptions: bool,
    ) -> None:
        """Build graph using xgraph CLI as subprocess."""
        try:
            cmd = [
                "build-graph",
                "--project-path",
                str(project_path),
                "--language",
                language,
                "--project-name",
                project_name,
                "--keep-existing-graph",
            ]

            if enable_descriptions:
                cmd.append("--enable-descriptions")

            if self.verbose:
                self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            with xgraph_openai_environ(self._openai_base_url):
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
        """
        Execute a Cypher query and return results.
        
        Args:
            cypher: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                import os
                
                uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                user = os.getenv("NEO4J_USER", "neo4j")
                password = os.getenv("NEO4J_PASSWORD", "password")
                
                self._driver = GraphDatabase.driver(uri, auth=(user, password))
            except ImportError:
                raise RuntimeError("neo4j driver not installed. Install with: pip install neo4j")
        
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [dict(record) for record in result]
    
    def close(self) -> None:
        """Close connection to graph database."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
