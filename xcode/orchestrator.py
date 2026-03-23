"""
Main orchestrator for xCode - coordinates graph building and agent execution.

Refactored to use clean architecture with service layer.
"""

import asyncio
from dataclasses import dataclass

from rich.console import Console

from xcode.domain.models import AgentResult, Task, XCodeConfig
from xcode.repositories.agent_repository import LaFactoriaRepository
from xcode.repositories.graph_repository import XGraphRepository
from xcode.schema import get_schema
from xcode.services.agent_service import AgentService
from xcode.services.graph_service import GraphService
from xcode.services.task_service import TaskService


@dataclass
class XCodeOrchestrator:
    """Orchestrates the complete xCode workflow using clean architecture."""

    config: XCodeConfig
    console: Console

    def __post_init__(self):
        """Initialize services and repositories."""
        self.task_service = TaskService()

        _llm = self.config.get_llm_config()
        graph_repo = XGraphRepository(
            console=self.console,
            verbose=self.config.verbose,
            enable_descriptions=self.config.xgraph_enable_descriptions,
            openai_base_url=_llm.get("base_url"),
        )
        self.graph_service = GraphService(graph_repo, self.console)

        agent_repo = LaFactoriaRepository(
            base_url="http://localhost:8000",
            console=self.console,
            agent_name="xcode_coding_agent",
            verbose=self.config.verbose,
        )
        self.agent_service = AgentService(agent_repo, self.console)

    def run(self) -> AgentResult:
        """
        Execute the complete xCode workflow:
        1. Classify task to determine if graph is needed
        2. Ensure knowledge graph exists (if needed)
        3. Execute task with agent
        4. Return result
        """
        try:
            task_classification = self.task_service.classify_task(self.config.task)

            if self.config.build_graph and task_classification.needs_neo4j:
                self.graph_service.ensure_graph_exists(
                    project_name=self.config.project_name,
                    repo_path=self.config.repo_path,
                    language=self.config.language,
                    verbose=self.config.verbose,
                )
            elif self.config.verbose:
                if not self.config.build_graph:
                    self.console.print("[dim]Skipping graph build (--no-build-graph)[/dim]")
                else:
                    self.console.print(
                        f"[dim]Skipping graph build for "
                        f"{task_classification.task_type.value} task "
                        f"(does not require Neo4j)[/dim]"
                    )

            task = self.task_service.create_task(self.config.task)
            schema = get_schema()

            result = asyncio.run(
                self.agent_service.execute_task(
                    task=task,
                    config=self.config,
                    schema=schema,
                )
            )

            return result

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                task=self.config.task,
                iterations=0,
            )
        finally:
            self.graph_service.close()
