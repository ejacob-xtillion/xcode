# xCode Clean Architecture

This document describes the clean architecture implementation for xCode.

## Overview

xCode follows **Clean Architecture** principles with clear separation of concerns across four layers:

```
┌─────────────────────────────────────────────────────────┐
│                     Presentation Layer                   │
│                    (CLI, Interactive)                    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      Service Layer                       │
│              (Business Logic Orchestration)              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                     Repository Layer                     │
│              (Data Access Abstractions)                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                   │
│               (External System Clients)                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      Domain Layer                        │
│         (Models, Interfaces, Business Rules)             │
└─────────────────────────────────────────────────────────┘
```

## Architecture Layers

### 1. Domain Layer (`xcode/domain/`)

**Purpose:** Pure business logic, models, and interfaces. No external dependencies.

**Contents:**
- `models.py`: Domain models (re-exported from `xcode/models/`)
  - `Task`, `AgentResult`, `VerificationResult`
  - `TaskType`, `TaskClassification`
  - `FileInfo`, `FileTreeCache`
  - `XCodeConfig`

- `interfaces.py`: Repository interfaces (ports) for dependency inversion
  - `GraphRepository`: Knowledge graph operations
  - `FileRepository`: File system operations
  - `AgentRepository`: Agent execution
  - `TaskRepository`: Task persistence

**Principles:**
- No external dependencies (only Python standard library)
- Pure data structures and business rules
- Defines contracts that outer layers must implement

### 2. Models Package (`xcode/models/`)

**Purpose:** Concrete domain model implementations.

**Contents:**
- `result.py`: `AgentResult`, `VerificationResult`
- `config.py`: `XCodeConfig` with environment integration
- `classification.py`: `TaskType`, `TaskClassification`
- `file_info.py`: `FileInfo`, `FileTreeCache` with caching logic
- `task.py`: `Task` representation

**Characteristics:**
- Modern Python 3.10+ type hints (`str | None`, `list[str]`)
- No external dependencies
- Rich business logic (validation, caching, statistics)

### 3. Service Layer (`xcode/services/`)

**Purpose:** Business logic orchestration. Coordinates domain models and repositories.

**Services:**

#### `TaskService`
- Task classification and validation
- Task creation and management
- Wraps `TaskClassifier` with service interface

#### `GraphService`
- Knowledge graph operations
- Graph building with progress display
- Query execution wrapper
- Delegates to `GraphRepository`

#### `AgentService`
- Agent execution orchestration
- Task execution with LLM configuration
- Result handling and logging
- Delegates to `AgentRepository`

#### `VerificationService`
- Test and lint verification
- Wraps `VerificationLoop` with service interface

**Principles:**
- Depends on domain interfaces, not concrete implementations
- Orchestrates multiple repositories
- Contains no infrastructure details

### 4. Repository Layer (`xcode/repositories/`)

**Purpose:** Data access abstractions. Implements domain interfaces.

**Repositories:**

#### `Neo4jGraphRepository`
- Implements `GraphRepository` interface
- Knowledge graph operations via xgraph
- Library and CLI fallback support
- Graph building and query execution

#### `LocalFileRepository`
- Implements `FileRepository` interface
- File system operations
- File tree caching integration
- File reading/writing/listing

#### `LaFactoriaAgentRepository`
- Implements `AgentRepository` interface
- Agent execution via la-factoria API
- Streaming support with event handling
- Tool call tracking and display

**Principles:**
- Adapts external systems to domain interfaces
- Implements dependency inversion
- Handles data access concerns

### 5. Infrastructure Layer (`xcode/infrastructure/`)

**Purpose:** External system integrations and low-level clients.

**Clients:**

#### `Neo4jClient`
- Direct Neo4j database operations
- Connection management
- Cypher query execution
- Environment-based configuration

#### `LLMClient`
- LLM API client
- Chat completion support
- Streaming support
- Configurable base URL and model

**Principles:**
- Lowest level of abstraction
- Direct external system integration
- Used by repositories for data access

### 6. Presentation Layer (`xcode/`)

**Purpose:** User interface and application entry points.

**Components:**
- `cli.py`: Command-line interface
- `interactive.py`: Interactive REPL session
- `banner.py`: Visual presentation
- `orchestrator.py`: Legacy orchestrator (deprecated)
- `orchestrator_new.py`: New orchestrator using service layer

**Principles:**
- Depends on services, not repositories or infrastructure
- Handles user interaction and display
- Minimal business logic

## Dependency Flow

```
CLI/Interactive
    ↓
Services (TaskService, GraphService, AgentService)
    ↓
Repositories (Neo4jGraphRepository, LocalFileRepository, LaFactoriaAgentRepository)
    ↓
Infrastructure (Neo4jClient, LLMClient)
    ↓
Domain (Models, Interfaces)
```

**Key Rules:**
1. Inner layers never depend on outer layers
2. All dependencies point inward toward domain
3. Outer layers depend on domain interfaces, not concrete implementations
4. Domain layer has zero external dependencies

## Benefits

### 1. Testability
- Services can be tested with mock repositories
- Repositories can be tested with mock infrastructure
- Domain models are pure and easy to test

### 2. Flexibility
- Easy to swap implementations (e.g., different graph databases)
- Can add new repositories without changing services
- Infrastructure changes don't affect business logic

### 3. Maintainability
- Clear separation of concerns
- Each layer has a single responsibility
- Changes are localized to specific layers

### 4. Scalability
- Easy to add new services
- Can parallelize repository operations
- Infrastructure can be optimized independently

## Migration Path

### Backward Compatibility

To maintain backward compatibility during migration:

1. **Alias Classes:**
   - `xcode/result.py`: `XCodeResult = AgentResult`
   - `xcode/config.py`: Keep full `XCodeConfig` class

2. **Dual Orchestrators:**
   - `orchestrator.py`: Legacy orchestrator (deprecated)
   - `orchestrator_new.py`: New orchestrator using services

3. **Gradual Migration:**
   - Phase 1: Create new architecture layers ✅
   - Phase 2: Update imports to use domain models ✅
   - Phase 3: Migrate to new orchestrator (in progress)
   - Phase 4: Remove legacy code

## File Structure

```
xcode/
├── domain/                    # Domain Layer
│   ├── __init__.py
│   ├── models.py             # Model re-exports
│   └── interfaces.py         # Repository interfaces
│
├── models/                    # Domain Models
│   ├── __init__.py
│   ├── classification.py     # TaskType, TaskClassification
│   ├── config.py             # XCodeConfig
│   ├── file_info.py          # FileInfo, FileTreeCache
│   ├── result.py             # AgentResult, VerificationResult
│   └── task.py               # Task
│
├── services/                  # Service Layer
│   ├── __init__.py
│   ├── task_service.py       # Task operations
│   ├── graph_service.py      # Graph operations
│   ├── agent_service.py      # Agent operations
│   └── verification_service.py # Verification operations
│
├── repositories/              # Repository Layer
│   ├── __init__.py
│   ├── graph_repository.py   # Neo4j graph adapter
│   ├── file_repository.py    # File system adapter
│   └── agent_repository.py   # La-factoria agent adapter
│
├── infrastructure/            # Infrastructure Layer
│   ├── __init__.py
│   ├── neo4j_client.py       # Neo4j client
│   └── llm_client.py         # LLM API client
│
├── cli.py                     # CLI entry point
├── interactive.py             # Interactive mode
├── banner.py                  # Visual presentation
├── orchestrator.py            # Legacy orchestrator (deprecated)
├── orchestrator_new.py        # New orchestrator
│
└── [Legacy modules for backward compatibility]
    ├── config.py              # Alias to domain.models.XCodeConfig
    ├── result.py              # Alias to domain.models.AgentResult
    ├── task_classifier.py     # Wraps domain models
    ├── file_cache.py          # Cache manager only
    ├── verification.py        # Verification loop
    ├── graph_builder.py       # Graph builder
    ├── agent_runner.py        # Agent runner
    ├── execution_tracker.py   # Execution tracking
    └── schema.py              # Neo4j schema
```

## Design Patterns

### 1. Dependency Inversion Principle (DIP)
- Services depend on `GraphRepository` interface, not `Neo4jGraphRepository`
- Enables easy mocking and testing
- Allows swapping implementations

### 2. Repository Pattern
- Abstracts data access behind interfaces
- Separates business logic from data access
- Enables caching and optimization

### 3. Service Layer Pattern
- Encapsulates business logic
- Orchestrates multiple repositories
- Provides clean API for presentation layer

### 4. Adapter Pattern
- Repositories adapt external systems to domain interfaces
- Infrastructure clients provide low-level access
- Clean separation between domain and external systems

## Testing Strategy

### Unit Tests
- **Domain Models:** Test validation and business rules
- **Services:** Test with mock repositories
- **Repositories:** Test with mock infrastructure
- **Infrastructure:** Test with mock external systems

### Integration Tests
- Test service + repository + infrastructure together
- Use test doubles for external systems (Neo4j, LLM API)
- Verify end-to-end flows

### Current Test Coverage
- 121 tests passing
- 46% code coverage
- All domain models: 100% coverage
- All services: Covered via integration tests

## Future Enhancements

### 1. Complete Migration
- Replace `orchestrator.py` with `orchestrator_new.py`
- Remove legacy modules after migration
- Update all imports to use new architecture

### 2. Enhanced Repository Layer
- Add caching decorators
- Implement connection pooling
- Add retry logic for external calls

### 3. Service Improvements
- Add transaction support
- Implement saga pattern for complex operations
- Add event sourcing for audit trail

### 4. Testing
- Increase coverage to 80%+
- Add integration tests for full workflows
- Add performance benchmarks

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
