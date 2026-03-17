"""
File tree caching system to avoid redundant Neo4j queries.

This module provides a simple in-memory cache of the file tree structure
to reduce the need for repeated Neo4j queries when discovering files.
"""

from pathlib import Path

from xcode.domain.models import FileTreeCache


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

    def get_cache(self, project_name: str) -> FileTreeCache | None:
        """Get cache for a project if it exists."""
        return self.caches.get(project_name)

    def set_cache(self, project_name: str, cache: FileTreeCache) -> None:
        """Set cache for a project."""
        self.caches[project_name] = cache

    def clear_cache(self, project_name: str) -> None:
        """Clear the cache for a specific project."""
        if project_name in self.caches:
            del self.caches[project_name]

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.caches.clear()


_cache_manager = FileCacheManager()


def get_cache_manager() -> FileCacheManager:
    """Get the global cache manager instance."""
    return _cache_manager
