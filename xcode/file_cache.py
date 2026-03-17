"""
File tree caching system to avoid redundant Neo4j queries.

This module provides a simple in-memory cache of the file tree structure
to reduce the need for repeated Neo4j queries when discovering files.
"""

import json
import time
from pathlib import Path

from xcode.domain.models import FileInfo, FileTreeCache

    def build(self, skip_patterns: list[str] | None = None) -> None:
        """
        Build the file tree cache by scanning the filesystem.

        Args:
            skip_patterns: List of patterns to skip (e.g., ['venv', 'node_modules'])
        """
        if skip_patterns is None:
            skip_patterns = [
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

        self.files.clear()
        self.directories.clear()

        # Scan the repository
        for item in self.repo_path.rglob("*"):
            # Skip if matches any skip pattern
            if any(pattern in str(item) for pattern in skip_patterns):
                continue

            if item.is_file():
                # Add file to cache
                file_info = FileInfo.from_path(item)
                self.files[str(item)] = file_info
            elif item.is_dir():
                # Add directory to cache
                self.directories.add(str(item))

        self.cache_time = time.time()

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

        return [file_info for file_info in self.files.values() if file_info.extension == extension]

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
            file_info for file_info in self.files.values() if file_info.path.startswith(directory)
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

        # Load files
        for file_data in data["files"]:
            file_info = FileInfo(**file_data)
            cache.files[file_info.path] = file_info

        # Load directories
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


class FileCacheManager:
    """
    Manager for file tree caches.

    Maintains caches for multiple projects.
    """

    def __init__(self):
        self.caches: dict[str, FileTreeCache] = {}

    def get_or_create_cache(
        self,
        project_name: str,
        repo_path: Path,
        skip_patterns: list[str] | None = None,
    ) -> FileTreeCache:
        """
        Get an existing cache or create a new one.

        Args:
            project_name: Name of the project
            repo_path: Path to the repository
            skip_patterns: Patterns to skip when building cache

        Returns:
            FileTreeCache instance
        """
        if project_name not in self.caches:
            cache = FileTreeCache(project_name=project_name, repo_path=repo_path)
            cache.build(skip_patterns)
            self.caches[project_name] = cache
        else:
            cache = self.caches[project_name]
            cache.refresh_if_needed(skip_patterns)

        return cache

    def clear_cache(self, project_name: str) -> None:
        """Clear the cache for a specific project."""
        if project_name in self.caches:
            del self.caches[project_name]

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.caches.clear()


# Global cache manager instance
_cache_manager = FileCacheManager()


def get_cache_manager() -> FileCacheManager:
    """Get the global cache manager instance."""
    return _cache_manager
