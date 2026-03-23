"""
Stdlib-only shell sandbox helpers (no LangChain). Imported by shell_tool and tests.
"""

from __future__ import annotations

import os
import shlex
import signal
import subprocess


class ShellCommandError(Exception):
    """Invalid cwd or command execution failure."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def resolve_working_directory(working_directory: str, allowed_roots: list[str]) -> str:
    """
    Return realpath of working_directory if it lies under one of allowed_roots.

    Raises ShellCommandError if paths are missing, roots empty, or cwd escapes allowlist.
    """
    if not allowed_roots:
        raise ShellCommandError("Shell tool is not configured with any allowed roots.")
    if not working_directory or not str(working_directory).strip():
        raise ShellCommandError("working_directory is required and must be non-empty.")

    try:
        real_cwd = os.path.realpath(os.path.abspath(str(working_directory).strip()))
    except OSError as e:
        raise ShellCommandError(f"Invalid working_directory: {e}") from e

    if not os.path.isdir(real_cwd):
        raise ShellCommandError(f"working_directory is not a directory: {real_cwd}")

    real_roots = []
    for root in allowed_roots:
        try:
            real_roots.append(os.path.realpath(os.path.abspath(root.strip())))
        except OSError:
            continue

    if not real_roots:
        raise ShellCommandError("No valid allowed roots after resolving paths.")

    for root in real_roots:
        if real_cwd == root or real_cwd.startswith(root + os.sep):
            return real_cwd

    raise ShellCommandError(
        f"Access denied: cwd {real_cwd!r} is not under allowed roots {real_roots!r}"
    )


def truncate_output(text: str, max_bytes: int) -> str:
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return text
    cut = data[: max_bytes - 40].decode("utf-8", errors="replace")
    return cut + "\n... [output truncated] ...\n"


def run_shell_command_impl(
    command: str,
    working_directory: str,
    *,
    allowed_roots: list[str],
    timeout: int,
    max_output_bytes: int,
) -> str:
    """
    Parse command with shlex (POSIX), run without shell, enforce cwd and timeout.

    Returns a human-readable result including exit code and truncated stdout/stderr.
    """
    if not command or not str(command).strip():
        raise ShellCommandError("command is required and must be non-empty.")

    cwd = resolve_working_directory(working_directory, allowed_roots)

    try:
        argv = shlex.split(command.strip(), posix=True)
    except ValueError as e:
        raise ShellCommandError(f"Could not parse command: {e}") from e

    if not argv:
        raise ShellCommandError("Parsed command is empty.")

    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=True,
        )
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            proc.communicate(timeout=5)
            raise ShellCommandError(
                f"Command timed out after {timeout}s (process group killed)."
            ) from None
    except ShellCommandError:
        raise
    except OSError as e:
        raise ShellCommandError(f"Failed to start process: {e}") from e

    exit_code = proc.returncode if proc.returncode is not None else -1
    combined = ""
    if out:
        combined += f"stdout:\n{out}"
    if err:
        combined += ("\n" if combined else "") + f"stderr:\n{err}"
    if not combined:
        combined = "(no stdout/stderr)"

    combined = truncate_output(combined, max_output_bytes)
    return f"exit_code={exit_code}\n{cwd}\n$ {command}\n\n{combined}"
