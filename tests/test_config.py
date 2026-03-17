"""
Tests for config module
"""
import os
import pytest
from pathlib import Path

from xcode.config import XCodeConfig


class TestXCodeConfig:
    """Tests for XCodeConfig."""

    def test_basic_config(self, tmp_path):
        """Test basic configuration."""
        config = XCodeConfig(
            task="test task",
            repo_path=tmp_path,
            language="python",
        )
        
        assert config.task == "test task"
        assert config.repo_path == tmp_path
        assert config.language == "python"
        assert config.project_name == tmp_path.name

    def test_project_name_defaults_to_directory(self, tmp_path):
        """Test that project_name defaults to directory name."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
        )
        
        assert config.project_name == tmp_path.name

    def test_project_name_can_be_set(self, tmp_path):
        """Test explicit project_name setting."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            project_name="custom-name",
        )
        
        assert config.project_name == "custom-name"

    def test_local_llm_flag_sets_endpoint(self, tmp_path):
        """Test that use_local_llm sets default endpoint."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            use_local_llm=True,
        )
        
        assert config.llm_endpoint == "http://localhost:11434"
        assert config.is_local_llm is True

    def test_explicit_llm_endpoint(self, tmp_path):
        """Test explicit LLM endpoint."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            llm_endpoint="http://localhost:8080",
        )
        
        assert config.llm_endpoint == "http://localhost:8080"
        assert config.is_local_llm is True

    def test_model_defaults(self, tmp_path):
        """Test model defaults based on endpoint."""
        # Cloud default
        config_cloud = XCodeConfig(
            task="test",
            repo_path=tmp_path,
        )
        assert config_cloud.model == "gpt-5"
        
        # Local default
        config_local = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            use_local_llm=True,
        )
        assert config_local.model == "llama3.2"

    def test_explicit_model(self, tmp_path):
        """Test explicit model setting."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            model="codellama",
        )
        
        assert config.model == "codellama"

    def test_get_llm_config_cloud(self, tmp_path):
        """Test LLM config for cloud."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            model="gpt-5",
        )
        
        llm_config = config.get_llm_config()
        assert llm_config["model"] == "gpt-5"
        assert "base_url" not in llm_config

    def test_get_llm_config_local(self, tmp_path):
        """Test LLM config for local."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
            use_local_llm=True,
            model="llama3.2",
        )
        
        llm_config = config.get_llm_config()
        assert llm_config["model"] == "llama3.2"
        assert llm_config["base_url"] == "http://localhost:11434"

    def test_neo4j_defaults(self, tmp_path):
        """Test Neo4j default configuration."""
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
        )
        
        assert config.neo4j_uri
        assert config.neo4j_user
        assert config.neo4j_password

    def test_environment_variables(self, tmp_path, monkeypatch):
        """Test environment variable loading."""
        monkeypatch.setenv("XCODE_MODEL", "custom-model")
        monkeypatch.setenv("XCODE_LLM_ENDPOINT", "http://custom:1234")
        
        config = XCodeConfig(
            task="test",
            repo_path=tmp_path,
        )
        
        assert config.model == "custom-model"
        assert config.llm_endpoint == "http://custom:1234"
