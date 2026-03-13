"""
Tests for schema module
"""
import pytest

from xcode.schema import get_schema, get_example_queries


class TestSchema:
    """Tests for schema module."""

    def test_get_schema_returns_string(self):
        """Test that get_schema returns a non-empty string."""
        schema = get_schema()
        assert isinstance(schema, str)
        assert len(schema) > 0

    def test_schema_contains_node_labels(self):
        """Test that schema contains expected node labels."""
        schema = get_schema()
        
        # Core node types
        assert "Project" in schema
        assert "File" in schema
        assert "Class" in schema
        assert "Callable" in schema
        assert "Test" in schema
        assert "Module" in schema
        assert "Variable" in schema

    def test_schema_contains_relationships(self):
        """Test that schema contains expected relationships."""
        schema = get_schema()
        
        assert "DECLARED_IN" in schema
        assert "IMPORTS" in schema
        assert "INHERITS_FROM" in schema
        assert "USES" in schema
        assert "TESTS" in schema
        assert "INCLUDED_IN" in schema

    def test_schema_contains_example_queries(self):
        """Test that schema contains example queries."""
        schema = get_schema()
        
        assert "MATCH" in schema
        assert "RETURN" in schema
        assert "WHERE" in schema

    def test_get_example_queries_returns_list(self):
        """Test that get_example_queries returns a list."""
        queries = get_example_queries()
        assert isinstance(queries, list)
        assert len(queries) > 0

    def test_example_queries_are_cypher(self):
        """Test that example queries are valid Cypher."""
        queries = get_example_queries()
        
        for query in queries:
            assert "MATCH" in query
            assert "RETURN" in query

    def test_schema_contains_csharp_nodes(self):
        """Test that schema documents C# specific nodes."""
        schema = get_schema()
        
        assert "Namespace" in schema
        assert "Interface" in schema
        assert "Property" in schema
