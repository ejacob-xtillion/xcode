"""
xCode: CLI tool for running AI agents with codebase knowledge graphs.

A Claude Code-like experience that integrates xgraph (codebase knowledge graphs)
with la-factoria (on-the-fly agents) and Neo4j MCP for intelligent code assistance.
"""

__version__ = "0.1.0"

# Re-export utilities for convenience
from .utils import (  # noqa: F401
    add,
    subtract,
    multiply,
    divide,
    reverse_upper,
    calculate,
    hello_world,
)

# Export validation utilities
from .validation import (  # noqa: F401
    ValidationError,
    AggregateValidationError,
    FieldSpec,
    sanitize_string,
    sanitize_numeric,
    sanitize_collection,
    validate_type,
    validate_schema,
    matches_regex,
    in_range,
    length_between,
    one_of,
    non_empty,
    validate_args,
    coerce_bool,
)
