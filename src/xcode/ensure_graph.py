"""Ensure the codebase knowledge graph exists (via xgraph)."""

import os
import subprocess
import sys
from typing import Optional


def ensure_knowledge_graph(
    project_path: str,
    language: str,
    project_name: str,
    keep_existing: bool = False,
    verbose: bool = False,
) -> None:
    """
    Build or update the knowledge graph for the given repo using xgraph.
    Prefers the xgraph library when installed; falls back to the build-graph CLI.
    """
    project_path = os.path.abspath(project_path)
    if not os.path.isdir(project_path):
        raise ValueError(f"Not a directory: {project_path}")

    try:
        from xgraph.knowledge_graph.build_graph import build_knowledge_graph
    except ImportError:
        if verbose:
            print("xgraph not installed as library; using build-graph CLI", file=sys.stderr)
        _ensure_via_cli(project_path, language, project_name, keep_existing, verbose)
        return

    build_knowledge_graph(
        project_path=project_path,
        language=language,
        project_name=project_name,
        keep_existing_graph=keep_existing,
        graph_db_type="neo4j",
    )
    if verbose:
        print("Knowledge graph built successfully (library).", file=sys.stderr)


def _ensure_via_cli(
    project_path: str,
    language: str,
    project_name: str,
    keep_existing: bool,
    verbose: bool,
) -> None:
    cmd = [
        sys.executable,
        "-m",
        "xgraph.cli",
        "--project-path",
        project_path,
        "--language",
        language,
        "--project-name",
        project_name,
        "--graph-db-type",
        "neo4j",
    ]
    if keep_existing:
        cmd.append("--keep-existing-graph")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"build-graph exited with code {result.returncode}")
