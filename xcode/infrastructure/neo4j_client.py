"""
Neo4j client for knowledge graph operations.
"""

import os


class Neo4jClient:
    """Client for Neo4j database operations."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        except ImportError:
            raise RuntimeError(
                "neo4j package not installed. Install with: pip install neo4j"
            )

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """
        Execute a Cypher query.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        if not self.driver:
            self.connect()

        with self.driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def close(self) -> None:
        """Close connection to Neo4j."""
        if self.driver:
            self.driver.close()
            self.driver = None
