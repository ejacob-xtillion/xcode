"""Bundled schema and helpers for agents."""

from importlib import resources

from xcode import schema as schema_pkg


def get_neo4j_schema_text() -> str:
    """Return the bundled Neo4j schema + example Cypher for agents."""
    try:
        return (resources.files(schema_pkg) / "neo4j_for_agents.md").read_text(encoding="utf-8")
    except Exception:
        return ""
