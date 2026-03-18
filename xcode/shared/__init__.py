"""
Shared utilities for xCode.

Cross-cutting concerns.
"""
from xcode.shared.schema import get_schema, get_example_queries, NEO4J_SCHEMA

__all__ = [
    "get_schema",
    "get_example_queries",
    "NEO4J_SCHEMA",
]
