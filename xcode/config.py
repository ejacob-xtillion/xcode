"""
Configuration for xCode CLI
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class XCodeConfig:
    """Configuration for xCode execution."""

    task: str
    repo_path: Path
    language: str = "python"
    project_name: str | None = None
    build_graph: bool = True
    model: str | None = None
    llm_endpoint: str | None = None
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
        """
        Finalize configuration after dataclass initialization.

        Resolves any missing values using repository context and environment
        variables:
        - Sets project_name to the name of repo_path if not provided.
        - If use_local_llm is True and llm_endpoint is unset, defaults to
          http://localhost:11434 (Ollama).
        - If model is unset, reads XCODE_MODEL from the environment.
        - If llm_endpoint is unset, reads XCODE_LLM_ENDPOINT from the environment.
        - If model remains unset after the above, chooses a default:
          - 'llama3.2' if an LLM endpoint is configured (commonly local).
          - 'gpt-5' if no endpoint is configured (assumed cloud).

        Returns:
            None
        """
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
                self.model = "gpt-5"

    @property
    def is_local_llm(self) -> bool:
        """
        Whether an LLM HTTP endpoint is configured.

        Note:
            This returns True if any llm_endpoint is set (local or remote).
            When use_local_llm is True and no endpoint is provided, the default
            is http://localhost:11434.

        Returns:
            bool: True if an LLM endpoint URL is configured; otherwise False.
        """
        return bool(self.llm_endpoint)

    def get_llm_config(self) -> dict:
        """
        Build the LLM configuration dictionary for the agent.

        Includes the selected model and, when available, the base_url to reach
        the LLM server.

        Returns:
            dict: Configuration compatible with the agent's LLM client. Keys:
                - 'model' (str): The model identifier.
                - 'base_url' (str, optional): LLM server URL when using an HTTP endpoint.
        """
        config = {
            "model": self.model,
        }
        if self.llm_endpoint:
            config["base_url"] = self.llm_endpoint
        return config
