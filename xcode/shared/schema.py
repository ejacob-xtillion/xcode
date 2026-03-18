"""
Neo4j schema for agents - node labels, relationships, and example queries
"""

NEO4J_SCHEMA = """
# Neo4j Knowledge Graph Schema for Agents

## Node Labels

### Core Nodes
- **Project**: Root project container
  - Properties: `id` (project:{name}), `name`, `type`, `path`

- **Folder**: Directory structure
  - Properties: `id`, `name`, `path`

- **File**: Source code files
  - Properties: `id` (file:{path}), `name`, `path`, `line_count`, `description`

- **Class**: Class definitions
  - Properties: `id`, `name`, `path`, `line_number`, `docstring`, `description`

- **Callable**: Functions and methods
  - Properties: `id`, `name`, `path`, `line_number`, `docstring`, `is_async`,
    `decorators`, `description`

- **Test**: Test functions and methods
  - Properties: `id`, `name`, `path`, `line_number`, `test_framework`, `description`

- **Module**: Imported modules
  - Properties: `id`, `name`

- **Variable**: Variable declarations
  - Properties: `id`, `name`, `path`, `line_number`, `scope`

### C#-Specific Nodes
- **Namespace**: C# namespace containers
- **Interface**: C# interface definitions
- **Constructor**: C# class/struct constructors
- **Property**: C# property members
- **Struct**: C# struct definitions
- **Record**: C# record definitions
- **Enum**: C# enum definitions

## Relationship Types

- **DECLARED_IN**: Element declared in File/Class
  - `(Callable)-[:DECLARED_IN]->(File)`
  - `(Class)-[:DECLARED_IN]->(File)`
  - `(Callable)-[:DECLARED_IN]->(Class)`

- **IMPORTS**: File imports Module
  - `(File)-[:IMPORTS]->(Module)`

- **INHERITS_FROM**: Class inheritance
  - `(Class)-[:INHERITS_FROM]->(Class)`

- **USES**: Code element uses another
  - `(Callable)-[:USES]->(Callable)`
  - `(Callable)-[:USES]->(Class)`
  - `(Callable)-[:USES]->(Variable)`

- **TESTS**: Test covers code element
  - `(Test)-[:TESTS]->(Callable)`

- **INCLUDED_IN**: Containment hierarchy
  - `(File)-[:INCLUDED_IN]->(Folder)`
  - `(File)-[:INCLUDED_IN]->(Project)`
  - `(Folder)-[:INCLUDED_IN]->(Project)`

## Project Scoping

When multiple projects share one Neo4j database, scope queries by project:

```cypher
MATCH (p:Project {name: $projectName})
MATCH (p)<-[:INCLUDED_IN*]-(element)
RETURN element
```

Project node ID format: `project:{project_name}`
File node ID format: `file:{relative_path}`

## Example Cypher Queries

### Find callables that use a specific class or function
```cypher
MATCH (c:Callable)-[:USES]->(target)
WHERE target.name CONTAINS $searchTerm
RETURN c.name AS callable, c.path AS file, c.line_number AS line
ORDER BY c.path, c.line_number
```

### Find tests that cover a specific callable
```cypher
MATCH (t:Test)-[:TESTS]->(c:Callable {name: $callableName})
RETURN t.name AS test, t.path AS file, t.line_number AS line
```

### Get all callables in a file
```cypher
MATCH (f:File {path: $filePath})<-[:DECLARED_IN]-(c:Callable)
RETURN c.name, c.line_number, c.description
ORDER BY c.line_number
```

### Find class methods and inheritance
```cypher
MATCH (class:Class {name: $className})
OPTIONAL MATCH (class)-[:INHERITS_FROM]->(parent:Class)
OPTIONAL MATCH (class)<-[:DECLARED_IN]-(method:Callable)
RETURN class, parent, COLLECT(method) AS methods
```

### Find untested callables in a project
```cypher
MATCH (p:Project {name: $projectName})
MATCH (p)<-[:INCLUDED_IN*]-(f:File)<-[:DECLARED_IN]-(c:Callable)
WHERE NOT (c:Test) AND NOT EXISTS((c)<-[:TESTS]-())
RETURN c.name, c.path, c.line_number
```

### Find files that import a specific module
```cypher
MATCH (f:File)-[:IMPORTS]->(m:Module {name: $moduleName})
RETURN f.path
```

### Get complete call graph for a callable
```cypher
MATCH (c:Callable {name: $callableName})
MATCH (c)-[:USES*1..3]->(used:Callable)
RETURN c.name AS source, COLLECT(DISTINCT used.name) AS dependencies
```
"""


def get_schema() -> str:
    """Get the Neo4j schema documentation for agents."""
    return NEO4J_SCHEMA


def get_example_queries() -> list[str]:
    """Get list of example Cypher queries."""
    return [
        # Find callables using a target
        """
        MATCH (c:Callable)-[:USES]->(target)
        WHERE target.name CONTAINS $searchTerm
        RETURN c.name, c.path, c.line_number
        """,
        # Find tests for callable
        """
        MATCH (t:Test)-[:TESTS]->(c:Callable {name: $callableName})
        RETURN t.name, t.path, t.line_number
        """,
        # Get file callables
        """
        MATCH (f:File {path: $filePath})<-[:DECLARED_IN]-(c:Callable)
        RETURN c.name, c.line_number
        ORDER BY c.line_number
        """,
        # Find untested code
        """
        MATCH (p:Project {name: $projectName})
        MATCH (p)<-[:INCLUDED_IN*]-(f:File)<-[:DECLARED_IN]-(c:Callable)
        WHERE NOT (c:Test) AND NOT EXISTS((c)<-[:TESTS]-())
        RETURN c.name, c.path
        """,
    ]
