"""
La-factoria integration: spawn agent with task and context (Neo4j MCP, schema, LLM config).
When la-factoria is available, wire it here; tools should return full logs (stdout, stderr, exit_code).
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from xcode.agent_loop import run_command, run_verification
from xcode.llm_config import LLMConfig
from xcode.schema import get_neo4j_schema_text


def get_agent_context(
    task: str,
    repo_path: Path,
    project_name: str,
    llm_config: LLMConfig,
) -> Dict[str, Any]:
    """
    Build context to pass to the la-factoria agent: task, repo path, project name,
    Neo4j env (for MCP), schema doc, and LLM config (base_url, model) for local or cloud.
    """
    schema_text = get_neo4j_schema_text()
    neo4j_env = {
        "NEO4J_URI": os.environ.get("NEO4J_URI", ""),
        "NEO4J_USER": os.environ.get("NEO4J_USER", ""),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", ""),
    }
    return {
        "task": task,
        "repo_path": str(repo_path),
        "project_name": project_name,
        "llm_base_url": llm_config.base_url,
        "llm_model": llm_config.model,
        "llm_api_key": llm_config.api_key,
        "neo4j_uri": neo4j_env["NEO4J_URI"],
        "neo4j_user": neo4j_env["NEO4J_USER"],
        "neo4j_password": neo4j_env["NEO4J_PASSWORD"],
        "schema_text": schema_text,
        "run_command_fn": run_command,
        "run_verification_fn": run_verification,
    }


def spawn_agent(
    task: str,
    repo_path: Path,
    project_name: str,
    llm_config: LLMConfig,
    verbose: bool = False,
) -> None:
    """
    Spawn the la-factoria agent with the given task and context.
    Agent receives: task, repo_path, project_name, Neo4j MCP config, schema doc, LLM config.
    Tools (run_shell, run_tests) should return full stdout, stderr, exit_code to close the loop.
    """
    context = get_agent_context(task, Path(repo_path), project_name, llm_config)
    if verbose:
        print(f"Context: project={project_name}, llm_model={context['llm_model']}, local={llm_config.is_local()}")
    # Wire la-factoria here when available: e.g. lf.run_agent(context), or subprocess with env
    # For now, stream a placeholder; real implementation will call lf and stream agent output
    print(f"Task: {task}")
    print("(la-factoria agent spawn: pass context to lf when integrated)")
