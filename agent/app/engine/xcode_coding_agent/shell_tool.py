"""
LangChain tool wrapper for sandboxed shell execution. Core logic is in shell_core.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.tools import tool

from app.core.logger import get_logger
from app.engine.xcode_coding_agent.shell_core import ShellCommandError, run_shell_command_impl

if TYPE_CHECKING:
    from app.core.settings import AppSettings

logger = get_logger()


@tool
def run_shell_command(command: str, working_directory: str) -> str:
    """
    Run a non-interactive shell command for tasks like tests and linters.

    Use the repository root or a subdirectory as working_directory (absolute path from
    the task context — same roots as filesystem access). Pass the full command as a
    single string; it is parsed safely (no shell interpolation). Examples:
    - pytest -q
    - ruff check .
    - python -m compileall .

    Do not use for destructive operations unless the user explicitly asked. Prefer
    read_file/edit_file when only file content is needed.
    """
    from app.core.settings import get_settings

    settings = get_settings()
    if not settings.shell_tool_enabled:
        return "Shell tool is disabled on this server."

    allowed = settings.get_shell_allowed_roots()
    try:
        result = run_shell_command_impl(
            command,
            working_directory,
            allowed_roots=allowed,
            timeout=settings.shell_command_timeout_seconds,
            max_output_bytes=settings.shell_max_output_bytes,
        )
        logger.info("shell_command_finished", cwd=working_directory)
        return result
    except ShellCommandError as e:
        return f"Error: {e.message}"


def get_shell_tools_for_agent(settings: AppSettings) -> list:
    """Tools to merge into the agent when shell is enabled."""
    if not settings.shell_tool_enabled:
        return []
    return [run_shell_command]
