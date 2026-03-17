"""
Main orchestrator for xCode - coordinates graph building and agent execution
"""

from dataclasses import dataclass

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from xcode.agent_runner import AgentRunner
from xcode.config import XCodeConfig
from xcode.graph_builder import GraphBuilder
from xcode.result import XCodeResult
from xcode.task_classifier import TaskClassifier


@dataclass
class XCodeOrchestrator:
    """Orchestrates the complete xCode workflow."""

    config: XCodeConfig
    console: Console

    def run(self) -> XCodeResult:
        """
        Execute the complete xCode workflow:
        1. Classify task to determine if graph is needed
        2. Ensure knowledge graph exists (if needed)
        3. Spawn and run agent with task
        4. Return result
        """
        try:
            # Step 1: Classify task to determine if graph is needed
            task_classification = TaskClassifier().classify(self.config.task)

            # Step 2: Ensure knowledge graph exists (only if needed)
            if self.config.build_graph:
                if task_classification.needs_neo4j:
                    self._ensure_knowledge_graph()
                else:
                    if self.config.verbose:
                        self.console.print(
                            f"[dim]Skipping graph build for "
                            f"{task_classification.task_type.value} task "
                            f"(does not require Neo4j)[/dim]"
                        )
            elif self.config.verbose:
                self.console.print("[dim]Skipping graph build (--no-build-graph)[/dim]")

            # Step 3: Run agent with task
            result = self._run_agent()

            return result

        except Exception as e:
            return XCodeResult(
                success=False,
                error=str(e),
                task=self.config.task,
                iterations=0,
            )

    def _ensure_knowledge_graph(self) -> None:
        """Ensure the knowledge graph exists for the repository."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"Building knowledge graph for {self.config.project_name}...",
                total=None,
            )

            graph_builder = GraphBuilder(self.config, self.console)
            graph_builder.build()

            progress.update(task, completed=True)

        if self.config.verbose:
            self.console.print(
                f"[green]✓[/green] Knowledge graph built for project: {self.config.project_name}"
            )

    def _run_agent(self) -> XCodeResult:
        """Run the agent with the given task."""
        self.console.print(f"\n[bold]Starting agent for task:[/bold] {self.config.task}\n")

        agent_runner = AgentRunner(self.config, self.console)
        result = agent_runner.run()

        return result
