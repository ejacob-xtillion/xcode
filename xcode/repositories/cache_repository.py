"""
Cache repository for file tree caching.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from xcode.models import FileTreeCache


class CacheRepository(ABC):
    """Abstract interface for cache operations."""

    @abstractmethod
    def get_or_create_cache(
        self,
        project_name: str,
        repo_path: Path,
        skip_patterns: Optional[list[str]] = None,
    ) -> FileTreeCache:
        """
        Get or create cache for a project.
        
        Args:
            project_name: Name of the project
            repo_path: Path to the repository
            skip_patterns: Optional patterns to skip when building cache
            
        Returns:
            FileTreeCache instance
        """
        pass

    @abstractmethod
    def get_cache(self, project_name: str) -> Optional[FileTreeCache]:
        """
        Get cache for a project if it exists.
        
        Args:
            project_name: Name of the project
            
        Returns:
            FileTreeCache if exists, None otherwise
        """
        pass

    @abstractmethod
    def set_cache(self, project_name: str, cache: FileTreeCache) -> None:
        """
        Set cache for a project.
        
        Args:
            project_name: Name of the project
            cache: FileTreeCache to store
        """
        pass

    @abstractmethod
    def clear_cache(self, project_name: str) -> None:
        """
        Clear cache for a specific project.
        
        Args:
            project_name: Name of the project
        """
        pass

    @abstractmethod
    def clear_all_caches(self) -> None:
        """Clear all caches."""
        pass


class InMemoryCacheRepository(CacheRepository):
    """
    In-memory implementation of CacheRepository.
    
    Maintains caches for multiple projects in memory.
    """

    def __init__(self):
        """Initialize the in-memory cache repository."""
        self.caches: dict[str, FileTreeCache] = {}

    def get_or_create_cache(
        self,
        project_name: str,
        repo_path: Path,
        skip_patterns: Optional[list[str]] = None,
    ) -> FileTreeCache:
        """
        Get or create cache for a project.
        
        Args:
            project_name: Name of the project
            repo_path: Path to the repository
            skip_patterns: Optional patterns to skip when building cache
            
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

    def get_cache(self, project_name: str) -> Optional[FileTreeCache]:
        """
        Get cache for a project if it exists.
        
        Args:
            project_name: Name of the project
            
        Returns:
            FileTreeCache if exists, None otherwise
        """
        return self.caches.get(project_name)

    def set_cache(self, project_name: str, cache: FileTreeCache) -> None:
        """
        Set cache for a project.
        
        Args:
            project_name: Name of the project
            cache: FileTreeCache to store
        """
        self.caches[project_name] = cache

    def clear_cache(self, project_name: str) -> None:
        """
        Clear cache for a specific project.
        
        Args:
            project_name: Name of the project
        """
        if project_name in self.caches:
            del self.caches[project_name]

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.caches.clear()
