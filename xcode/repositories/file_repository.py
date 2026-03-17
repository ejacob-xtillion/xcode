"""
Local file system repository implementation.
"""

from pathlib import Path

from xcode.domain.interfaces import FileRepository
from xcode.domain.models import FileInfo, FileTreeCache
from xcode.file_cache import get_cache_manager


class LocalFileRepository(FileRepository):
    """Local file system implementation of FileRepository."""

    def __init__(self):
        self.cache_manager = get_cache_manager()

    def get_file_tree(self, repo_path: Path) -> FileTreeCache:
        """Get cached file tree for a repository."""
        project_name = repo_path.name
        cache = self.cache_manager.get_cache(project_name)

        if cache is None:
            cache = FileTreeCache(
                project_name=project_name,
                repo_path=repo_path,
            )
            cache.refresh()
            self.cache_manager.set_cache(project_name, cache)

        return cache

    def read_file(self, file_path: Path) -> str:
        """Read contents of a file."""
        return file_path.read_text()

    def write_file(self, file_path: Path, content: str) -> None:
        """Write contents to a file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    def file_exists(self, file_path: Path) -> bool:
        """Check if a file exists."""
        return file_path.exists()

    def list_files(self, directory: Path, pattern: str = "*") -> list[FileInfo]:
        """List files in a directory matching a pattern."""
        files = []
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                files.append(FileInfo.from_path(file_path))
        return files
