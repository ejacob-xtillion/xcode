"""
Configuration for xCode CLI
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class XCodeConfig:
    """Configuration for xCode execution."""

    task: str
    repo_path: Path
    language: str = "python"
    project_name: Optional[str] = None
    build_graph: bool = True
    model: Optional[str] = None
    llm_endpoint: Optional[str] = None
    use_local_llm: bool = False
    verbose: bool = False

    # Neo4j configuration (from environment)
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password"))

    # xgraph configuration
    xgraph_enable_descriptions: bool = field(
        default_factory=lambda: os.getenv("XGRAPH_ENABLE_DESCRIPTIONS", "false").lower() == "true"
    )

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Set project name to directory name if not specified
        if not self.project_name:
            self.project_name = self.repo_path.name

        # Handle local LLM configuration
        if self.use_local_llm and not self.llm_endpoint:
            # Default to Ollama
            self.llm_endpoint = "http://localhost:11434"

        # Get model from environment if not specified
        if not self.model:
            self.model = os.getenv("XCODE_MODEL")

        # Get LLM endpoint from environment if not specified
        if not self.llm_endpoint:
            self.llm_endpoint = os.getenv("XCODE_LLM_ENDPOINT")

        # Set default model based on endpoint type
        if not self.model:
            if self.llm_endpoint:
                # Local LLM default
                self.model = "llama3.2"
            else:
                # Cloud LLM default
                self.model = "gpt-4"

    @property
    def is_local_llm(self) -> bool:
        """Check if using a local LLM."""
        return bool(self.llm_endpoint)

    def get_llm_config(self) -> dict:
        """Get LLM configuration for agent."""
        config = {
            "model": self.model,
        }
        if self.llm_endpoint:
            config["base_url"] = self.llm_endpoint
        return config
