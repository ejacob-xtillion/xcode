"""
Tests for file caching system.
"""

import json
import time

from xcode.models import FileInfo, FileTreeCache
from xcode.file_cache import FileCacheManager, get_cache_manager


class TestFileInfo:
    """Test FileInfo dataclass."""

    def test_from_path(self, tmp_path):
        """Test creating FileInfo from a Path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        file_info = FileInfo.from_path(test_file)

        assert file_info.name == "test.py"
        assert file_info.extension == ".py"
        assert file_info.size > 0
        assert file_info.modified_time > 0
        assert str(test_file) in file_info.path


class TestFileTreeCache:
    """Test FileTreeCache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_files = []

    def create_test_structure(self, tmp_path):
        """Create a test directory structure."""
        # Create some Python files
        (tmp_path / "main.py").write_text("# Main file")
        (tmp_path / "utils.py").write_text("# Utils")

        # Create a subdirectory with files
        sub_dir = tmp_path / "src"
        sub_dir.mkdir()
        (sub_dir / "app.py").write_text("# App")
        (sub_dir / "config.py").write_text("# Config")

        # Create files to skip
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (venv_dir / "lib.py").write_text("# Should be skipped")

        return tmp_path

    def test_build_cache(self, tmp_path):
        """Test building the file cache."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build(skip_patterns=["venv"])  # Only skip venv

        # Should have found 4 Python files (excluding venv)
        assert len(cache.files) == 4
        assert cache.cache_time > 0

    def test_skip_patterns(self, tmp_path):
        """Test that skip patterns work."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build(skip_patterns=["venv"])

        # Should not include files in venv
        venv_files = [f for f in cache.files.values() if "venv" in f.path]
        assert len(venv_files) == 0

    def test_get_files_by_extension(self, tmp_path):
        """Test getting files by extension."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        py_files = cache.get_files_by_extension(".py")
        assert len(py_files) == 4
        assert all(f.extension == ".py" for f in py_files)

    def test_get_files_by_extension_without_dot(self, tmp_path):
        """Test getting files by extension without leading dot."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        py_files = cache.get_files_by_extension("py")
        assert len(py_files) == 4

    def test_get_files_by_pattern(self, tmp_path):
        """Test getting files by pattern."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        # Find files with 'config' in the name
        config_files = cache.get_files_by_pattern("config")
        assert len(config_files) == 1
        assert "config.py" in config_files[0].name

    def test_get_file(self, tmp_path):
        """Test getting a specific file."""
        test_dir = self.create_test_structure(tmp_path)
        main_file = test_dir / "main.py"

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        file_info = cache.get_file(str(main_file))
        assert file_info is not None
        assert file_info.name == "main.py"

    def test_list_all_files(self, tmp_path):
        """Test listing all files."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        all_files = cache.list_all_files()
        assert len(all_files) == 4

    def test_get_directory_files(self, tmp_path):
        """Test getting files in a directory."""
        test_dir = self.create_test_structure(tmp_path)
        src_dir = test_dir / "src"

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        src_files = cache.get_directory_files(str(src_dir))
        assert len(src_files) == 2
        assert all("src" in f.path for f in src_files)

    def test_cache_expiration(self, tmp_path):
        """Test cache expiration."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
            ttl=0.1,  # 100ms TTL
        )
        cache.build()

        # Should not be expired immediately
        assert not cache.is_expired()

        # Wait for expiration
        time.sleep(0.15)
        assert cache.is_expired()

    def test_refresh_if_needed(self, tmp_path):
        """Test automatic refresh."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
            ttl=0.1,
        )
        cache.build()

        original_time = cache.cache_time

        # Wait for expiration
        time.sleep(0.15)

        # Refresh should rebuild
        cache.refresh_if_needed()
        assert cache.cache_time > original_time

    def test_export_to_json(self, tmp_path):
        """Test exporting cache to JSON."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        output_file = tmp_path / "cache.json"
        cache.export_to_json(output_file)

        assert output_file.exists()

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert data["project_name"] == "test"
        assert len(data["files"]) == 4
        assert "directories" in data

    def test_load_from_json(self, tmp_path):
        """Test loading cache from JSON."""
        test_dir = self.create_test_structure(tmp_path)

        # Create and export cache
        cache1 = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache1.build()

        output_file = tmp_path / "cache.json"
        cache1.export_to_json(output_file)

        # Load from JSON
        cache2 = FileTreeCache.load_from_json(output_file)

        assert cache2.project_name == cache1.project_name
        assert len(cache2.files) == len(cache1.files)
        assert cache2.directories == cache1.directories

    def test_get_stats(self, tmp_path):
        """Test getting cache statistics."""
        test_dir = self.create_test_structure(tmp_path)

        cache = FileTreeCache(
            project_name="test",
            repo_path=test_dir,
        )
        cache.build()

        stats = cache.get_stats()

        assert stats["total_files"] == 4
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] >= 0
        assert ".py" in stats["extensions"]
        assert stats["extensions"][".py"] == 4
        assert not stats["is_expired"]


class TestFileCacheManager:
    """Test FileCacheManager."""

    def test_get_or_create_cache(self, tmp_path):
        """Test getting or creating a cache."""
        manager = FileCacheManager()

        # Create test file
        (tmp_path / "test.py").write_text("# Test")

        cache1 = manager.get_or_create_cache("test", tmp_path)
        assert len(cache1.files) > 0

        # Getting again should return the same cache
        cache2 = manager.get_or_create_cache("test", tmp_path)
        assert cache1 is cache2

    def test_clear_cache(self, tmp_path):
        """Test clearing a specific cache."""
        manager = FileCacheManager()

        (tmp_path / "test.py").write_text("# Test")

        manager.get_or_create_cache("test", tmp_path)
        assert "test" in manager.caches

        manager.clear_cache("test")
        assert "test" not in manager.caches

    def test_clear_all_caches(self, tmp_path):
        """Test clearing all caches."""
        manager = FileCacheManager()

        (tmp_path / "test1.py").write_text("# Test 1")
        (tmp_path / "test2.py").write_text("# Test 2")

        manager.get_or_create_cache("test1", tmp_path)
        manager.get_or_create_cache("test2", tmp_path)

        assert len(manager.caches) == 2

        manager.clear_all_caches()
        assert len(manager.caches) == 0

    def test_cache_refresh(self, tmp_path):
        """Test that cache refreshes when expired."""
        manager = FileCacheManager()

        (tmp_path / "test.py").write_text("# Test")

        cache = manager.get_or_create_cache("test", tmp_path)
        cache.ttl = 0.1  # Set short TTL

        original_time = cache.cache_time

        # Wait for expiration
        time.sleep(0.15)

        # Get cache again should trigger refresh
        cache2 = manager.get_or_create_cache("test", tmp_path)
        assert cache2.cache_time > original_time


class TestGlobalCacheManager:
    """Test global cache manager."""

    def test_get_cache_manager(self):
        """Test getting the global cache manager."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        # Should be the same instance
        assert manager1 is manager2
