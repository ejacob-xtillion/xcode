"""
Main orchestrator for xCode - coordinates graph building and agent execution
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from xcode.config import XCodeConfig
from xcode.graph_builder import GraphBuilder
from xcode.agent_runner import AgentRunner
from xcode.result import XCodeResult


@dataclass
class XCodeOrchestrator:
    """Orchestrates the complete xCode workflow."""

    config: XCodeConfig
    console: Console

    def run(self) -> XCodeResult:
        """
        Execute the complete xCode workflow:
        1. Ensure knowledge graph exists
        2. Spawn and run agent with task
        3. Return result
        """
        try:
            # Step 1: Ensure knowledge graph exists
            if self.config.build_graph:
                self._ensure_knowledge_graph()
            elif self.config.verbose:
                self.console.print("[dim]Skipping graph build (--no-build-graph)[/dim]")

            # Step 2: Run agent with task
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
