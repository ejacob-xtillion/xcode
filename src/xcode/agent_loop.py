"""
Close the agent loop: capture logs and run verification so the agent
can confirm task success and iterate (fix, re-run) until done.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class RunResult:
    """Result of a command or verification run; pass back to agent as logs."""

    stdout: str
    stderr: str
    exit_code: int
    command: Optional[str] = None

    def success(self) -> bool:
        return self.exit_code == 0

    def to_agent_message(self) -> str:
        """Format for injection back into the agent (e.g. as user or system message)."""
        lines = [
            f"Exit code: {self.exit_code}",
            "--- stdout ---",
            self.stdout or "(none)",
            "--- stderr ---",
            self.stderr or "(none)",
        ]
        if self.command:
            lines.insert(0, f"Command: {self.command}")
        return "\n".join(lines)


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = 300,
) -> RunResult:
    """
    Run a command and return full stdout, stderr, and exit code.
    Use this so the agent sees logs and can verify or retry.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return RunResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.returncode,
            command=" ".join(cmd),
        )
    except subprocess.TimeoutExpired as e:
        return RunResult(
            stdout=e.stdout or "",
            stderr=f"Command timed out after {timeout}s. {e.stderr or ''}",
            exit_code=-1,
            command=" ".join(cmd),
        )
    except Exception as e:
        return RunResult(
            stdout="",
            stderr=str(e),
            exit_code=-1,
            command=" ".join(cmd),
        )


def run_verification(
    project_path: Path,
    language: str = "python",
    run_tests: bool = True,
    run_linter: bool = False,
) -> RunResult:
    """
    Run verification (tests and/or linter) and return combined result for the agent.
    After the agent signals done, call this and inject the output so the agent can retry.
    """
    project_path = Path(project_path)
    parts: List[str] = []
    any_failed = False

    if run_tests and language == "python":
        pytest_cmd = "pytest"
        venv_pytest = project_path / ".venv" / "bin" / "pytest"
        if venv_pytest.exists():
            pytest_cmd = str(venv_pytest)
        result = run_command([pytest_cmd, "-v", "--tb=short"], cwd=project_path)
        parts.append("=== Tests ===\n" + result.to_agent_message())
        if not result.success():
            any_failed = True

    if run_linter and language == "python":
        result = run_command(["ruff", "check", "."], cwd=project_path)
        parts.append("=== Linter (ruff) ===\n" + result.to_agent_message())
        if not result.success():
            any_failed = True

    if not parts:
        return RunResult(
            stdout="",
            stderr="No verification run (unsupported language or options)",
            exit_code=0,
        )

    return RunResult(
        stdout="\n\n".join(parts),
        stderr="",
        exit_code=0 if not any_failed else 1,
    )
