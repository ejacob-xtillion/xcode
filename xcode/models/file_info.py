"""
File information models.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a file in the codebase."""

    path: str
    name: str
    extension: str
    size: int
    modified_time: float

    @classmethod
    def from_path(cls, file_path: Path) -> "FileInfo":
        """Create FileInfo from a Path object."""
        stat = file_path.stat()
        return cls(
            path=str(file_path),
            name=file_path.name,
            extension=file_path.suffix,
            size=stat.st_size,
            modified_time=stat.st_mtime,
        )


@dataclass
class FileTreeCache:
    """
    Cache for file tree structure.

    Provides fast access to file listings without querying Neo4j.
    """

    project_name: str
    repo_path: Path
    files: dict[str, FileInfo] = field(default_factory=dict)
    directories: set[str] = field(default_factory=set)
    cache_time: float = 0.0
    ttl: float = 300.0
