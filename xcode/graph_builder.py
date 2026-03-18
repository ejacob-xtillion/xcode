"""
Graph builder module - DEPRECATED: Use Neo4jGraphRepository instead.

This module is kept for backward compatibility only.
"""

import warnings

from rich.console import Console

from xcode.domain.models import XCodeConfig
from xcode.repositories.graph_repository import XGraphRepository


class GraphBuilder:
    """
    DEPRECATED: Use XGraphRepository instead.
    
    This class is kept for backward compatibility and delegates to XGraphRepository.
    """

    def __init__(self, config: XCodeConfig, console: Console):
        warnings.warn(
            "GraphBuilder is deprecated. Use XGraphRepository instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = config
        self.console = console
        self._repository = XGraphRepository(
            console=console,
            verbose=config.verbose,
            enable_descriptions=config.xgraph_enable_descriptions,
        )

    def build(self) -> None:
        """Build the knowledge graph for the repository."""
        self._repository.build_graph(
            project_name=self.config.project_name,
            repo_path=self.config.repo_path,
            language=self.config.language,
        )

    def _build_via_library(self) -> None:
        """DEPRECATED: Use repository directly."""
        warnings.warn(
            "This method is deprecated. Use XGraphRepository._build_via_library instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._repository._build_via_library(
            self.config.repo_path,
            self.config.language,
            self.config.project_name,
            self.config.xgraph_enable_descriptions,
        )

    def _build_via_subprocess(self) -> None:
        """DEPRECATED: Use repository directly."""
        warnings.warn(
            "This method is deprecated. Use XGraphRepository._build_via_subprocess instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._repository._build_via_subprocess(
            self.config.repo_path,
            self.config.language,
            self.config.project_name,
            self.config.xgraph_enable_descriptions,
        )
