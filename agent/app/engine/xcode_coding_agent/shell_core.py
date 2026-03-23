"""
Stdlib-only shell sandbox helpers (no LangChain). Imported by shell_tool and tests.

Security / behavior notes (SWE contract):
- Commands are parsed with ``shlex`` and executed with ``shell=False`` (no shell injection).
- ``cwd`` is resolved and must stay under configured allowed roots.
- Auto-install only reads ``requirements.txt`` in that cwd (bounded size); it does not execute it.
- Subprocess output is capped to limit memory and log size.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
from typing import Final

# Guardrail: avoid loading huge files into memory for fingerprinting.
_MAX_REQUIREMENTS_TXT_BYTES: Final[int] = 512 * 1024

# (resolved cwd, sha256 of requirements.txt, python executable path)
RequirementsInstallFingerprint = tuple[str, str, str]


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


# Successful requirements.txt installs keyed by (cwd, requirements sha256, python path).
# Avoids re-running uv/pip on every pytest tool call in the same agent process.
_install_lock = threading.Lock()
_installed_requirements_fingerprints: set[RequirementsInstallFingerprint] = set()


def clear_requirements_install_cache() -> None:
    """Reset in-process install dedupe state (intended for tests)."""
    with _install_lock:
        _installed_requirements_fingerprints.clear()


def _requirements_file_sha256(req_path: str) -> str:
    """Stream-hash requirements.txt with a hard size cap."""
    digest = hashlib.sha256()
    total = 0
    try:
        with open(req_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_REQUIREMENTS_TXT_BYTES:
                    raise ShellCommandError(
                        f"requirements.txt is larger than {_MAX_REQUIREMENTS_TXT_BYTES} bytes; "
                        "auto-install disabled for this file (install deps manually)."
                    )
                digest.update(chunk)
    except OSError as e:
        raise ShellCommandError(f"Could not read requirements.txt: {e}") from e
    return digest.hexdigest()


def _requirements_fingerprint(
    cwd: str, req_path: str, python_executable: str
) -> RequirementsInstallFingerprint:
    return (cwd, _requirements_file_sha256(req_path), python_executable)


def _command_suggests_test_run(command: str) -> bool:
    """Heuristic: user/agent is trying to run tests (needs project deps from requirements.txt)."""
    lower = command.lower()
    if "pytest" in lower:
        return True
    if lower.startswith("tox ") or " tox " in lower:
        return True
    if "nose2" in lower or "nosetests" in lower:
        return True
    if "unittest" in lower and "discover" in lower:
        return True
    return False


def _run_requirements_txt_install(
    cwd: str,
    *,
    python_executable: str,
    pip_timeout: int,
) -> tuple[int, str, str, str]:
    """
    Install project dependencies from requirements.txt into the same interpreter
    the agent uses for subprocess commands.

    Prefer ``uv pip install`` when the ``uv`` binary is on PATH (Docker agent image);
    uv-sync'd venvs often lack a working ``python -m pip``.
    Uses quiet flags to reduce log volume and speed up no-op resolves.
    """
    uv_bin = shutil.which("uv")
    if uv_bin:
        proc = subprocess.run(
            [
                uv_bin,
                "pip",
                "install",
                "-q",
                "-r",
                "requirements.txt",
                "--python",
                python_executable,
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=pip_timeout,
            start_new_session=True,
        )
        out = proc.stdout or ""
        err = proc.stderr or ""
        code = proc.returncode if proc.returncode is not None else -1
        return code, out, err, "uv pip install -q -r requirements.txt"

    proc = subprocess.run(
        [
            python_executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-r",
            "requirements.txt",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=pip_timeout,
        start_new_session=True,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""
    code = proc.returncode if proc.returncode is not None else -1
    return code, out, err, "python -m pip install -q -r requirements.txt"


def run_shell_command_impl(
    command: str,
    working_directory: str,
    *,
    allowed_roots: list[str],
    timeout: int,
    max_output_bytes: int,
    auto_install_requirements: bool = False,
    skip_redundant_requirements_install: bool = True,
    pip_install_timeout: int = 300,
    python_executable: str | None = None,
) -> str:
    """
    Parse command with shlex (POSIX), run without shell, enforce cwd and timeout.

    Args:
        command: Full command line (no shell); split with POSIX rules.
        working_directory: Intended cwd; resolved and checked against ``allowed_roots``.
        allowed_roots: Each path resolved; cwd must be equal to or under one root.
        timeout: Seconds for the main command (install uses ``pip_install_timeout``).
        max_output_bytes: Truncate combined stdout/stderr beyond this size.
        auto_install_requirements: When True and command looks like a test run, if
            ``requirements.txt`` exists under cwd, install deps into ``python_executable``'s env first.
        skip_redundant_requirements_install: When True, skip install if the same cwd +
            requirements content + Python already succeeded in this process.
        pip_install_timeout: Timeout for the automatic requirements install step.
        python_executable: Interpreter for installs and implied default for ``python`` in PATH;
            defaults to ``sys.executable``.

    Returns:
        Human-readable block with exit code, cwd, command echo, and truncated output.

    Raises:
        ShellCommandError: Invalid cwd, parse error, timeout, or install failure.
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

    py_exe = python_executable or sys.executable
    preamble = ""

    if auto_install_requirements and _command_suggests_test_run(command):
        req_path = os.path.join(cwd, "requirements.txt")
        if os.path.isfile(req_path):
            fp = _requirements_fingerprint(cwd, req_path, py_exe)

            with _install_lock:
                cached = (
                    skip_redundant_requirements_install
                    and fp in _installed_requirements_fingerprints
                )
            if cached:
                preamble = (
                    "auto: skipped requirements.txt install (unchanged since last success in this process)\n"
                    "---\n"
                )
            else:
                try:
                    pip_code, pip_out, pip_err, via = _run_requirements_txt_install(
                        cwd,
                        python_executable=py_exe,
                        pip_timeout=pip_install_timeout,
                    )
                except subprocess.TimeoutExpired:
                    raise ShellCommandError(
                        f"requirements.txt install timed out after {pip_install_timeout}s"
                    ) from None
                except OSError as e:
                    raise ShellCommandError(
                        f"requirements.txt install failed to start: {e}"
                    ) from e

                pip_blob = ""
                if pip_out:
                    pip_blob += f"stdout:\n{pip_out}"
                if pip_err:
                    pip_blob += ("\n" if pip_blob else "") + f"stderr:\n{pip_err}"
                if not pip_blob:
                    pip_blob = "(no install output)"

                preamble = (
                    f"auto: {via}\n"
                    f"{truncate_output(pip_blob, max_output_bytes)}\n"
                    f"---\n"
                )
                if pip_code != 0:
                    raise ShellCommandError(
                        f"requirements.txt install failed (exit {pip_code}) via {via}.\n{preamble}"
                    )
                with _install_lock:
                    _installed_requirements_fingerprints.add(fp)

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
    # Omit exit_code when 0 to reduce noise; always show on failure.
    if exit_code != 0:
        head = f"exit_code={exit_code}\n{cwd}\n$ {command}\n\n"
    else:
        head = f"{cwd}\n$ {command}\n\n"
    body = head + combined
    return preamble + body if preamble else body
