"""
Main orchestrator for xCode - coordinates graph building and agent execution.

Refactored to use clean architecture with service layer.
"""

import asyncio
import os
from dataclasses import dataclass

from rich.console import Console

from xcode.domain.models import AgentResult, Task, VerificationResult, XCodeConfig
from xcode.formatting import VerificationFormatter
from xcode.repositories.agent_repository import AgentHttpRepository
from xcode.repositories.graph_repository import XGraphRepository
from xcode.schema import get_schema
from xcode.services.agent_service import AgentService
from xcode.services.graph_service import GraphService
from xcode.services.task_service import TaskService
from xcode.services.test_discovery_service import TestDiscoveryService
from xcode.services.test_generation_service import TestGenerationService
from xcode.services.verification_service import VerificationService


@dataclass
class XCodeOrchestrator:
    """Orchestrates the complete xCode workflow using clean architecture."""

    config: XCodeConfig
    console: Console

    def __post_init__(self):
        """Initialize services and repositories."""
        self.task_service = TaskService()
        self.formatter = VerificationFormatter(self.console)

        _llm = self.config.get_llm_config()
        graph_repo = XGraphRepository(
            console=self.console,
            verbose=self.config.verbose,
            enable_descriptions=self.config.xgraph_enable_descriptions,
            openai_base_url=_llm.get("base_url"),
        )
        self.graph_service = GraphService(graph_repo, self.console)

        agent_url = os.getenv("XCODE_AGENT_URL", "http://localhost:8000")
        agent_repo = AgentHttpRepository(
            base_url=agent_url,
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

            task = self.task_service.create_task(
                description=self.config.task,
                repo_path=self.config.repo_path,
                project_name=self.config.project_name,
                language=self.config.language,
            )
            schema = get_schema()

            result = asyncio.run(
                self.agent_service.execute_task(
                    task=task,
                    config=self.config,
                    schema=schema,
                )
            )

            # Run verification loop if enabled and task succeeded
            if result.success and self.config.verify_changes:
                verification_result = self._run_verification_loop(task, result, schema)

                # Update result based on verification
                if not verification_result.success:
                    result.success = False
                    error_msg = verification_result.error or verification_result.output
                    result.error = f"Verification failed: {error_msg}"

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

    def _run_verification_loop(
        self, task: Task, agent_result: AgentResult, schema: str
    ) -> VerificationResult:
        """
        Run verification loop with test discovery and generation.

        Args:
            task: Original task
            agent_result: Result from agent execution
            schema: Neo4j schema documentation

        Returns:
            VerificationResult with verification outcome
        """
        self.formatter.print_verification_start()

        # Step 1: Check if any files were modified
        if not agent_result.modified_files:
            self.console.print("[dim]No file modifications detected, skipping verification[/dim]")
            return VerificationResult(
                success=True,
                checks_run=[],
                output="No changes to verify",
            )

        # Step 2: Discover related tests via Neo4j
        test_discovery = TestDiscoveryService(
            self.graph_service.graph_repo, self.console
        )

        test_summary = test_discovery.get_test_summary(
            agent_result.modified_files, self.config.project_name
        )

        self.formatter.print_test_discovery(
            related_tests=test_summary["total_related_tests"],
            untested_callables=test_summary["untested_callables"],
            modified_files=agent_result.modified_files,
        )

        # Step 3: Generate tests for untested code if enabled
        if self.config.generate_missing_tests and test_summary["untested_callables"] > 0:
            self.formatter.print_test_generation(test_summary["untested_callables"])

            test_gen_service = TestGenerationService(self.agent_service, self.console)
            test_gen_result = asyncio.run(
                test_gen_service.generate_tests_for_callables(
                    test_summary["untested_callables_list"],
                    task,
                    self.config,
                    schema,
                )
            )

            if not test_gen_result.success:
                self.console.print(
                    f"[yellow]Warning: Test generation failed: {test_gen_result.error}[/yellow]"
                )

        # Step 4: Run tests and linters
        self.console.print("[cyan]Running tests and linters...[/cyan]")
        verification_service = VerificationService(
            self.config.repo_path, self.config.language, self.console
        )

        verification_result = verification_service.verify(
            run_tests=True, run_linter=True
        )

        # Step 5: If verification fails, give agent chance to fix
        fix_attempts = 0
        while (
            not verification_result.success
            and fix_attempts < self.config.max_fix_attempts
        ):
            fix_attempts += 1
            max_attempts = self.config.max_fix_attempts
            self.console.print(
                f"[yellow]Verification failed, "
                f"attempting fix {fix_attempts}/{max_attempts}...[/yellow]"
            )

            # Create fix task with verification output
            fix_task = Task(
                description=f"""Fix the following test/linter failures:

{verification_result.output}

Analyze the errors, make necessary corrections, and re-run the tests to verify the fixes.""",
                repo_path=task.repo_path,
                project_name=task.project_name,
                language=task.language,
            )

            fix_result = asyncio.run(
                self.agent_service.execute_task(
                    task=fix_task,
                    config=self.config,
                    schema=schema,
                )
            )

            if not fix_result.success:
                self.console.print(
                    f"[red]Fix attempt {fix_attempts} failed: {fix_result.error}[/red]"
                )
                break

            # Re-run verification
            self.console.print("[cyan]Re-running verification...[/cyan]")
            verification_result = verification_service.verify(
                run_tests=True, run_linter=True
            )

        # Display final verification status
        self.formatter.print_verification_result(
            success=verification_result.success,
            checks_run=verification_result.checks_run,
            output=verification_result.output if self.config.verbose else None,
            fix_attempts=fix_attempts,
        )

        return verification_result
