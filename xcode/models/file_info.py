"""
File information models.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from xcode.constants import DEFAULT_SKIP_PATTERNS


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
    
    Implements the Statsable protocol via get_stats() method.
    """

    project_name: str
    repo_path: Path
    files: dict[str, FileInfo] = field(default_factory=dict)
    directories: set[str] = field(default_factory=set)
    cache_time: float = 0.0
    ttl: float = 300.0

    def build(self, skip_patterns: list[str] | None = None) -> None:
        """
        Build the file tree cache by scanning the filesystem.

        Args:
            skip_patterns: List of patterns to skip (e.g., ['venv', 'node_modules'])
        """
        if skip_patterns is None:
            skip_patterns = DEFAULT_SKIP_PATTERNS

        self.files.clear()
        self.directories.clear()

        for item in self.repo_path.rglob("*"):
            if any(pattern in str(item) for pattern in skip_patterns):
                continue

            if item.is_file():
                file_info = FileInfo.from_path(item)
                self.files[str(item)] = file_info
            elif item.is_dir():
                self.directories.add(str(item))

        self.cache_time = time.time()

    def refresh(self, skip_patterns: list[str] | None = None) -> None:
        """Refresh the cache by rebuilding it."""
        self.build(skip_patterns)

    def is_expired(self) -> bool:
        """Check if the cache has expired."""
        if self.cache_time == 0.0:
            return True
        return (time.time() - self.cache_time) > self.ttl

    def refresh_if_needed(self, skip_patterns: list[str] | None = None) -> None:
        """Refresh the cache if it has expired."""
        if self.is_expired():
            self.build(skip_patterns)

    def get_files_by_extension(self, extension: str) -> list[FileInfo]:
        """
        Get all files with a specific extension.

        Args:
            extension: File extension (e.g., '.py', '.js')

        Returns:
            List of FileInfo objects
        """
        if not extension.startswith("."):
            extension = f".{extension}"

        return [
            file_info
            for file_info in self.files.values()
            if file_info.extension == extension
        ]

    def get_files_by_pattern(self, pattern: str) -> list[FileInfo]:
        """
        Get all files matching a pattern.

        Args:
            pattern: Pattern to match (simple substring match)

        Returns:
            List of FileInfo objects
        """
        pattern_lower = pattern.lower()
        return [
            file_info
            for file_info in self.files.values()
            if pattern_lower in file_info.path.lower()
        ]

    def get_file(self, path: str) -> FileInfo | None:
        """
        Get file info for a specific path.

        Args:
            path: File path

        Returns:
            FileInfo if found, None otherwise
        """
        return self.files.get(path)

    def list_all_files(self) -> list[FileInfo]:
        """Get all files in the cache."""
        return list(self.files.values())

    def get_directory_files(self, directory: str) -> list[FileInfo]:
        """
        Get all files in a specific directory.

        Args:
            directory: Directory path

        Returns:
            List of FileInfo objects
        """
        return [
            file_info
            for file_info in self.files.values()
            if file_info.path.startswith(directory)
        ]

    def export_to_json(self, output_path: Path) -> None:
        """
        Export the cache to a JSON file.

        Args:
            output_path: Path to save the JSON file
        """
        data = {
            "project_name": self.project_name,
            "repo_path": str(self.repo_path),
            "cache_time": self.cache_time,
            "files": [
                {
                    "path": file_info.path,
                    "name": file_info.name,
                    "extension": file_info.extension,
                    "size": file_info.size,
                    "modified_time": file_info.modified_time,
                }
                for file_info in self.files.values()
            ],
            "directories": list(self.directories),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_json(cls, input_path: Path) -> "FileTreeCache":
        """
        Load a cache from a JSON file.

        Args:
            input_path: Path to the JSON file

        Returns:
            FileTreeCache instance
        """
        with open(input_path) as f:
            data = json.load(f)

        cache = cls(
            project_name=data["project_name"],
            repo_path=Path(data["repo_path"]),
            cache_time=data["cache_time"],
        )

        for file_data in data["files"]:
            file_info = FileInfo(**file_data)
            cache.files[file_info.path] = file_info

        cache.directories = set(data["directories"])

        return cache

    def get_stats(self) -> dict[str, any]:
        """Get cache statistics."""
        extensions = {}
        total_size = 0

        for file_info in self.files.values():
            ext = file_info.extension or "(no extension)"
            extensions[ext] = extensions.get(ext, 0) + 1
            total_size += file_info.size

        return {
            "total_files": len(self.files),
            "total_directories": len(self.directories),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "extensions": extensions,
            "cache_age_seconds": time.time() - self.cache_time if self.cache_time > 0 else 0,
            "is_expired": self.is_expired(),
        }
