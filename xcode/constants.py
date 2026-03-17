"""
Shared constants for xCode.

This module contains constants used across multiple modules to avoid duplication.
"""

# Default patterns to skip when scanning file trees
DEFAULT_SKIP_PATTERNS = [
    "venv",
    ".venv",
    "env",
    ".env",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".egg-info",
]
