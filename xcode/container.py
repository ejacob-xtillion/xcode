"""
Dependency injection container for xCode.

Composition root that wires all dependencies together.
"""
from dataclasses import dataclass

from rich.console import Console

from xcode.models import XCodeConfig
from xcode.repositories import (
    AgentRepository,
    LaFactoriaRepository,
    GraphRepository,
    XGraphRepository,
    CacheRepository,
    InMemoryCacheRepository,
)
from xcode.services import (
    AgentService,
    GraphService,
    ClassificationService,
    VerificationService,
)
from xcode.shared import get_schema


@dataclass
class DIContainer:
    """
    Dependency injection container.
    
    Holds all configured services and repositories.
    """
    
    # Repositories
    agent_repo: AgentRepository
    graph_repo: GraphRepository
    cache_repo: CacheRepository
    
    # Services
    agent_service: AgentService
    graph_service: GraphService
    classification_service: ClassificationService
    verification_service: VerificationService
    
    # Utilities
    console: Console


def create_container(config: XCodeConfig, console: Console = None) -> DIContainer:
    """
    Create and wire the dependency injection container.
    
    Args:
        config: xCode configuration
        console: Rich console for output
        
    Returns:
        Configured DIContainer
    """
    if console is None:
        console = Console()
    
    # Get Neo4j schema
    schema_text = get_schema()
    
    # Create repositories
    agent_repo = LaFactoriaRepository(
        base_url="http://localhost:8000",
        console=console,
        verbose=config.verbose,
    )
    
    graph_repo = XGraphRepository(
        console=console,
        verbose=config.verbose,
    )
    
    cache_repo = InMemoryCacheRepository()
    
    # Create services
    classification_service = ClassificationService()
    
    agent_service = AgentService(
        agent_repo=agent_repo,
        cache_repo=cache_repo,
        classification_service=classification_service,
        console=console,
        neo4j_uri=config.neo4j_uri,
        schema_text=schema_text,
    )
    
    graph_service = GraphService(
        graph_repo=graph_repo,
        console=console,
    )
    
    verification_service = VerificationService(
        repo_path=config.repo_path,
        language=config.language,
        console=console,
    )
    
    # Return container with all dependencies
    return DIContainer(
        agent_repo=agent_repo,
        graph_repo=graph_repo,
        cache_repo=cache_repo,
        agent_service=agent_service,
        graph_service=graph_service,
        classification_service=classification_service,
        verification_service=verification_service,
        console=console,
    )
